"""Update-Modul der Stempeluhr.

Ab Version 5.2.04 liegt die eigentliche Update-Route in
``app.modules.updates.routes``. Das alte Modul ``app.routes.updates`` bleibt
als Kompatibilitäts-Wrapper bestehen, damit bestehende Imports und Includes
weiter funktionieren.
"""
from app.modules.updates.routes import router

__all__ = ["router"]
