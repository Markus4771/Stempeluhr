"""Kompatibilitäts-Wrapper für das Update-Modul.

Die produktive Implementierung liegt ab Version 5.2.04 unter:

    app.modules.updates.routes

Dieses Modul bleibt bewusst erhalten, damit ``app.main`` und bestehende
Erweiterungen weiterhin ``from app.routes import updates`` verwenden können.
"""
from app.modules.updates.routes import *  # noqa: F401,F403
