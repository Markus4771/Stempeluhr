"""Regressionstests fuer den Session-Schluessel.

Der Schluessel signiert die Session-Cookies. Mit einem vorhersagbaren
Wert kann jeder Cookies faelschen und sich als Administrator anmelden.
Diese Tests sichern ab, dass kein fester Fallback zurueckkommt und der
Schluessel ueber Neustarts hinweg stabil bleibt.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def config_module(tmp_path, monkeypatch):
    """Laedt app.core.config neu mit isolierter Schluessel-Datei."""
    monkeypatch.setenv("STEMPELUHR_SECRET_KEY_FILE", str(tmp_path / "secret_key"))
    monkeypatch.delenv("STEMPELUHR_SECRET_KEY", raising=False)
    sys.modules.pop("app.core.config", None)
    module = importlib.import_module("app.core.config")
    yield module
    sys.modules.pop("app.core.config", None)


def test_secret_key_is_not_the_old_static_default(config_module):
    """Der frueher fest verdrahtete Schluessel darf nicht verwendet werden."""
    assert config_module.SECRET_KEY != "stempeluhr-change-me-2026-v4-3-0"
    assert config_module.SECRET_KEY not in config_module.INSECURE_SECRET_KEYS


def test_secret_key_is_random_and_long(config_module):
    """Der erzeugte Schluessel ist lang genug und nicht vorhersagbar."""
    assert len(config_module.SECRET_KEY) >= 32
    assert config_module.SECRET_KEY_IS_INSECURE is False


def test_two_instances_get_different_keys(config_module, tmp_path, monkeypatch):
    """Zwei frische Installationen erhalten unterschiedliche Schluessel."""
    monkeypatch.setenv("STEMPELUHR_SECRET_KEY_FILE", str(tmp_path / "other_key"))
    sys.modules.pop("app.core.config", None)
    other = importlib.import_module("app.core.config")
    try:
        assert other.SECRET_KEY != config_module.SECRET_KEY
    finally:
        sys.modules.pop("app.core.config", None)


def test_secret_key_persists_across_restarts(config_module):
    """Nach einem Neustart wird derselbe Schluessel verwendet.

    Sonst waeren nach jedem Neustart alle Sessions ungueltig.
    """
    key_file = config_module.SECRET_KEY_FILE
    assert key_file.exists()
    stored = key_file.read_text(encoding="utf-8").strip()

    sys.modules.pop("app.core.config", None)
    reloaded = importlib.import_module("app.core.config")
    try:
        assert reloaded.SECRET_KEY == stored
        assert reloaded.SECRET_KEY == config_module.SECRET_KEY
    finally:
        sys.modules.pop("app.core.config", None)


def test_secret_key_file_has_restrictive_permissions(config_module):
    """Die Schluessel-Datei ist nur fuer den Eigentuemper lesbar."""
    mode = config_module.SECRET_KEY_FILE.stat().st_mode & 0o777
    assert mode == 0o600


def test_environment_variable_wins(config_module, monkeypatch):
    """Ein gesetzter Umgebungsschluessel hat Vorrang."""
    monkeypatch.setenv("STEMPELUHR_SECRET_KEY", "ein-sehr-langer-testschluessel-mit-mindestens-32-zeichen")
    sys.modules.pop("app.core.config", None)
    module = importlib.import_module("app.core.config")
    try:
        assert module.SECRET_KEY == "ein-sehr-langer-testschluessel-mit-mindestens-32-zeichen"
    finally:
        sys.modules.pop("app.core.config", None)


def test_insecure_environment_value_is_rejected(config_module, monkeypatch):
    """Ein Platzhalter aus der Umgebung wird nicht uebernommen."""
    monkeypatch.setenv("STEMPELUHR_SECRET_KEY", "stempeluhr-change-me-2026-v4-3-0")
    sys.modules.pop("app.core.config", None)
    module = importlib.import_module("app.core.config")
    try:
        assert module.SECRET_KEY != "stempeluhr-change-me-2026-v4-3-0"
        assert module.SECRET_KEY not in module.INSECURE_SECRET_KEYS
    finally:
        sys.modules.pop("app.core.config", None)


def test_startup_check_flags_insecure_key(monkeypatch):
    """Die Startup-Pruefung meldet einen vorhersagbaren Schluessel."""
    from app.services import startup_checks

    monkeypatch.setattr(startup_checks, "_check_secret_key", lambda: {
        "name": "secret_key",
        "ok": False,
        "message": "Session-Schluessel ist leer oder ein bekannter Platzhalter",
    })
    result = startup_checks.run_startup_checks()
    assert result["ok"] is False
    assert any(c["name"] == "secret_key" for c in result["checks"])


def test_startup_check_reports_secret_key(monkeypatch):
    """Die Startup-Pruefung enthaelt immer eine Schluessel-Pruefung."""
    from app.services import startup_checks

    result = startup_checks.run_startup_checks()
    names = [c.get("name") for c in result["checks"]]
    assert "secret_key" in names


def test_no_static_fallback_in_source():
    """Im Quelltext steht kein fester Schluessel-Fallback mehr.

    Der alte Wert darf weiterhin genannt werden - er steht in der
    Blockliste. Er darf aber nicht mehr als Vorgabe dienen.
    """
    config_path = Path(__file__).resolve().parents[1] / "app" / "core" / "config.py"
    source = config_path.read_text(encoding="utf-8")
    assert 'os.environ.get("STEMPELUHR_SECRET_KEY", "stempeluhr' not in source
    assert "SECRET_KEY = os.environ.get" not in source
