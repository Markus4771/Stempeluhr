#!/usr/bin/env python3
"""Modulstruktur-Selbsttest für die Stempeluhr.

Der Test verändert nichts. Er prüft nur, ob die vorbereitete Modulstruktur,
das Plugin-Framework und die wichtigsten Kompatibilitäts-Wrapper vorhanden und
importierbar sind.
"""
from pathlib import Path
import importlib
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REQUIRED = [
    ROOT / "app" / "modules" / "registry.py",
    ROOT / "app" / "modules" / "spec.py",
    ROOT / "app" / "modules" / "loader.py",
    ROOT / "app" / "modules" / "updates" / "routes.py",
    ROOT / "app" / "routes" / "updates.py",
    ROOT / "app" / "modules" / "system" / "routes.py",
    ROOT / "app" / "modules" / "developer" / "routes.py",
    ROOT / "app" / "core" / "permissions.py",
    ROOT / "app" / "plugins.py",
    ROOT / "plugins" / "README.md",
    ROOT / "build_deb.sh",
    ROOT / "buildsystem" / "build_deb.sh",
    ROOT / "version.json",
]

missing = [p for p in REQUIRED if not p.exists()]
if missing:
    print("Modularisierung: FEHLER")
    for path in missing:
        print(f" - fehlt: {path}")
    sys.exit(1)

IMPORTS = [
    "app.modules.registry",
    "app.modules.spec",
    "app.modules.loader",
    "app.core.permissions",
    "app.plugins",
]

errors = []
for module_name in IMPORTS:
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        errors.append((module_name, exc))

if errors:
    print("Modularisierung: FEHLER")
    for name, exc in errors:
        print(f" - Import fehlgeschlagen: {name}: {exc}")
    sys.exit(1)

from app.modules.registry import get_modules, get_navigation_as_dicts

modules = get_modules()
if not modules:
    print("Modularisierung: FEHLER - keine Module registriert")
    sys.exit(1)

print("Modularisierung: OK")
print(f"Projekt: {ROOT}")
print(f"Registrierte Module: {len(modules)}")
print(f"Navigationsvorschau: {len(get_navigation_as_dicts())} Einträge")
