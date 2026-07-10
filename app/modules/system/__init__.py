"""System-Modul der Stempeluhr.

Version 5.2.04 führt eine Registry für System-Routen ein. Die eigentlichen
Routen bleiben aus Stabilitätsgründen zunächst an ihrem bisherigen Ort.
"""
from app.modules.system.routes import get_routers

__all__ = ["get_routers"]
