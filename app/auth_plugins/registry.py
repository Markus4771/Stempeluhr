"""Registry, Zustände und Zugriffsfunktionen für Anmelde-Plugins."""
from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

from app.database import Base, engine
from .base import AuthenticationPlugin

logger = logging.getLogger("stempeluhr.auth_plugins")


class AuthPluginState(Base):
    __tablename__ = "auth_plugin_states"

    id = Column(Integer, primary_key=True)
    plugin_key = Column(String(100), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=False)
    installed_version = Column(String(50), nullable=True)
    settings_json = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


@dataclass(frozen=True)
class PluginDefinition:
    key: str
    module_path: str
    default_enabled: bool = False


PLUGIN_DEFINITIONS = (
    PluginDefinition("rfid", "app.auth_plugins.rfid", True),
)

PLANNED_PLUGINS = (
    {"key": "qr", "name": "QR-Code", "description": "Dynamische und statische QR-Anmeldung.", "required_capabilities": ["camera"]},
    {"key": "pin", "name": "PIN", "description": "Anmeldung über Terminal-Tastatur oder Touchdisplay.", "required_capabilities": ["pin"]},
    {"key": "fingerprint", "name": "Fingerabdruck", "description": "Biometrische Anmeldung über Fingerprint-Sensor.", "required_capabilities": ["fingerprint"]},
    {"key": "mobile_app", "name": "Handy-App", "description": "Sichere Geräteanmeldung über App und Zertifikat.", "required_capabilities": ["bluetooth"]},
    {"key": "smartwatch", "name": "Smartwatch", "description": "Wearable-Anmeldung über App oder Bluetooth.", "required_capabilities": ["bluetooth"]},
    {"key": "fido2", "name": "FIDO2 / Passkey", "description": "Anmeldung mit Sicherheitsschlüssel oder Passkey.", "required_capabilities": []},
)

_loaded_plugins: dict[str, AuthenticationPlugin] = {}


def ensure_auth_plugin_schema() -> None:
    Base.metadata.create_all(bind=engine, tables=[AuthPluginState.__table__])


def _load_definition(definition: PluginDefinition) -> AuthenticationPlugin:
    module = importlib.import_module(definition.module_path)
    plugin = getattr(module, "plugin", None)
    if not isinstance(plugin, AuthenticationPlugin):
        raise TypeError(f"{definition.module_path} exportiert kein gültiges AuthenticationPlugin")
    if plugin.metadata.key != definition.key:
        raise ValueError(f"Plugin-Key stimmt nicht überein: {plugin.metadata.key} != {definition.key}")
    return plugin


def initialize_auth_plugins(db: Session) -> dict[str, AuthenticationPlugin]:
    """Lädt installierte Plugins und synchronisiert deren Datenbankzustand."""
    _loaded_plugins.clear()
    for definition in PLUGIN_DEFINITIONS:
        state = db.query(AuthPluginState).filter(AuthPluginState.plugin_key == definition.key).first()
        if state is None:
            state = AuthPluginState(plugin_key=definition.key, enabled=definition.default_enabled)
            db.add(state)
            db.flush()
        try:
            plugin = _load_definition(definition)
            state.installed_version = plugin.metadata.version
            state.last_error = None
            if state.enabled:
                plugin.initialize()
                _loaded_plugins[definition.key] = plugin
        except Exception as exc:
            state.last_error = str(exc)
            logger.exception("Anmelde-Plugin %s konnte nicht geladen werden", definition.key)
        state.updated_at = datetime.now()
    db.commit()
    return dict(_loaded_plugins)


def installed_plugin(key: str) -> AuthenticationPlugin | None:
    definition = next((item for item in PLUGIN_DEFINITIONS if item.key == key), None)
    if not definition:
        return None
    try:
        return _load_definition(definition)
    except Exception:
        return None


def enabled_plugin(key: str) -> AuthenticationPlugin | None:
    return _loaded_plugins.get(key)


def list_plugins(db: Session) -> list[dict[str, Any]]:
    definitions = {item.key: item for item in PLUGIN_DEFINITIONS}
    states = {row.plugin_key: row for row in db.query(AuthPluginState).all()}
    result: list[dict[str, Any]] = []
    for key, definition in definitions.items():
        plugin = installed_plugin(key)
        state = states.get(key)
        result.append({
            "key": key,
            "installed": plugin is not None,
            "enabled": bool(state.enabled) if state else definition.default_enabled,
            "version": plugin.metadata.version if plugin else None,
            "name": plugin.metadata.name if plugin else key,
            "description": plugin.metadata.description if plugin else "Plugin konnte nicht geladen werden.",
            "credential_types": list(plugin.metadata.credential_types) if plugin else [],
            "required_capabilities": list(plugin.metadata.required_capabilities) if plugin else [],
            "supports_enrollment": bool(plugin.metadata.supports_enrollment) if plugin else False,
            "supports_diagnostics": bool(plugin.metadata.supports_diagnostics) if plugin else False,
            "last_error": state.last_error if state else None,
        })
    for item in PLANNED_PLUGINS:
        result.append({
            **item,
            "installed": False,
            "enabled": False,
            "version": None,
            "credential_types": [],
            "supports_enrollment": False,
            "supports_diagnostics": False,
            "last_error": None,
            "planned": True,
        })
    return result


def set_plugin_enabled(db: Session, key: str, enabled: bool) -> AuthPluginState:
    if key not in {item.key for item in PLUGIN_DEFINITIONS}:
        raise ValueError("Plugin ist nicht installiert")
    state = db.query(AuthPluginState).filter(AuthPluginState.plugin_key == key).first()
    if state is None:
        state = AuthPluginState(plugin_key=key)
        db.add(state)
    state.enabled = bool(enabled)
    state.updated_at = datetime.now()
    db.commit()
    initialize_auth_plugins(db)
    return state


def plugin_settings(db: Session, key: str) -> dict[str, Any]:
    state = db.query(AuthPluginState).filter(AuthPluginState.plugin_key == key).first()
    if not state or not state.settings_json:
        return {}
    try:
        return json.loads(state.settings_json)
    except Exception:
        return {}
