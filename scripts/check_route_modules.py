#!/usr/bin/env python3
"""Prüft, ob die modularisierten Routen importierbar sind.

Aufruf auf dem Server:
    cd /opt/stempeluhr
    PYTHONPATH=/opt/stempeluhr .venv/bin/python scripts/check_route_modules.py
"""
import importlib
import sys

MODULES = [
    "app.routes.web",
    "app.routes.dashboard",
    "app.routes.employees",
    "app.routes.reports",
    "app.routes.corrections",
    "app.routes.privacy_audit",
    "app.routes.backup",
    "app.routes.vacation",
    "app.routes.plausibility",
    "app.routes.email_settings",
    "app.routes.departments",
    "app.routes.api_settings",
    "app.routes.terminals",
    "app.routes.time_settings",
    "app.routes.https_settings",
    "app.routes.security_general",
    "app.routes.offboarding",
    "app.routes.dsgvo",
]

failed = []
for name in MODULES:
    try:
        module = importlib.import_module(name)
        router = getattr(module, "router", None)
        count = len(getattr(router, "routes", [])) if router else 0
        print(f"OK  {name} ({count} routes)")
    except Exception as exc:
        failed.append((name, exc))
        print(f"ERR {name}: {exc}")

if failed:
    print("\nFehlerhafte Routenmodule:")
    for name, exc in failed:
        print(f"- {name}: {exc}")
    sys.exit(1)

print("\nAlle Routenmodule importierbar.")
