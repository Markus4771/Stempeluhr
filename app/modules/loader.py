"""Sicherer Modul-Lader für die schrittweise Modularisierung.

Der Lader ist absichtlich defensiv aufgebaut: Er kann Modul-Metadaten lesen und
optional Router registrieren, ohne bestehende Legacy-Routen zu entfernen. Damit
bleiben vorhandene URLs während der 5.2.x-Architekturreihe stabil.
"""
from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, asdict
from typing import Any

from fastapi import FastAPI

from app.modules.registry import get_modules

logger = logging.getLogger("stempeluhr.modules")


@dataclass
class ModuleLoadResult:
    key: str
    title: str
    status: str
    module_path: str
    router_path: str | None
    loaded: bool
    router_registered: bool
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_modules() -> list[ModuleLoadResult]:
    """Prüft, ob die in der Registry genannten Module importierbar sind."""
    results: list[ModuleLoadResult] = []
    for module in get_modules():
        loaded = False
        message = ""
        try:
            importlib.import_module(module.module_path)
            loaded = True
            message = "Modul importierbar"
        except Exception as exc:
            message = f"Modul nicht importierbar: {exc}"
        results.append(ModuleLoadResult(
            key=module.key,
            title=module.title,
            status=module.status,
            module_path=module.module_path,
            router_path=module.router_path,
            loaded=loaded,
            router_registered=False,
            message=message,
        ))
    return results


def load_module_routers(app: FastAPI, *, register: bool = False) -> list[ModuleLoadResult]:
    """Lädt Modulrouter optional automatisch.

    register=False ist der sichere Standard für 5.2.07. Damit kann die
    Entwicklerkonsole bereits sehen, welche Router später automatisch geladen
    werden können, ohne doppelte Routen zu erzeugen.
    """
    results: list[ModuleLoadResult] = []
    for module in get_modules():
        loaded = False
        registered = False
        message = ""
        try:
            importlib.import_module(module.module_path)
            loaded = True
            if register and module.router_path:
                router_module = importlib.import_module(module.router_path)
                router = getattr(router_module, "router", None)
                if router is not None:
                    app.include_router(router)
                    registered = True
                    message = "Router registriert"
                else:
                    message = "Router-Modul besitzt kein Attribut router"
            else:
                message = "Modul geladen, Routerregistrierung im Kompatibilitätsmodus deaktiviert"
        except Exception as exc:
            logger.exception("Modul %s konnte nicht geladen werden", module.key)
            message = str(exc)
        results.append(ModuleLoadResult(module.key, module.title, module.status, module.module_path, module.router_path, loaded, registered, message))
    return results
