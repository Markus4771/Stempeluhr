"""Kompatibilitätsfix für den Ausschluss des festen Systemadmins.

Der bisherige Filter verkettete mehrere ``!= 'admin'``-Bedingungen. In SQL
werden Datensätze mit NULL in einem dieser Felder dadurch ebenfalls verworfen.
Das führte dazu, dass reguläre Mitarbeiter u. a. in Korrektur und Auswertung
nicht sichtbar waren.

Der feste Admin besitzt systemweit die eindeutige Mitarbeiternummer ``admin``.
Nur dieser Datensatz wird deshalb aus fachlichen Mitarbeiterlisten entfernt.
"""

from sqlalchemy import func, or_

from . import common


def _exclude_fixed_admin_null_safe(query, Employee):
    """Schließt ausschließlich den festen Systemadmin NULL-sicher aus."""
    if not hasattr(Employee, "employee_number"):
        return query

    employee_number = Employee.employee_number
    return query.filter(
        or_(
            employee_number.is_(None),
            func.lower(func.trim(employee_number)) != "admin",
        )
    )


# Früh beim Laden der Web-Routen installieren. Alle anschließend modular
# importierten Routen übernehmen damit den korrigierten gemeinsamen Filter.
common._exclude_fixed_admin = _exclude_fixed_admin_null_safe
