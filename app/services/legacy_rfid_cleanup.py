"""Abschaltung der alten RFID-Lern- und Speicherpfade.

Seit 6.0 ist employee_rfid_media die einzige maßgebliche RFID/NFC-Zuordnung.
Dieses Modul entfernt beim Start verbliebene alte Lernaufträge und deaktiviert
den früheren Raspberry-Lernhook, damit kein Code mehr employees.rfid_code
beschreiben kann.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Setting

LEGACY_PENDING_KEYS = (
    "rfid_learn_pending_employee_id",
    "rfid_learn_pending_started_by",
    "rfid_learn_pending_started_at",
)


def disable_legacy_rfid_paths(db: Session) -> int:
    """Entfernt alte, eventuell noch offene RFID-Lernaufträge.

    Die eigentliche Medienverwaltung erfolgt ausschließlich über
    app.services.rfid_media und die zentralen Enrollment-Endpunkte.
    """
    rows = db.query(Setting).filter(Setting.key.in_(LEGACY_PENDING_KEYS)).all()
    for row in rows:
        db.delete(row)
    if rows:
        db.commit()

    # dashboard.py hat den alten Hook beim Modulimport lokal gebunden. Beide
    # Referenzen werden daher explizit neutralisiert. Bestehende Scan-Routen
    # buchen anschließend normal über resolve_employee_by_rfid().
    from app.routes import common, dashboard

    def _legacy_learning_disabled(request, session, rfid_code):
        return None

    common._save_pending_rfid_from_terminal = _legacy_learning_disabled
    dashboard._save_pending_rfid_from_terminal = _legacy_learning_disabled
    return len(rows)
