"""Einmalige Bereinigung alter RFID-Lernaufträge.

Seit 6.0 ist employee_rfid_media die maßgebliche RFID/NFC-Zuordnung.
Der frühere RFID-Lernmodus wurde aus den Routen entfernt. Dieses Modul
entfernt nur noch eventuell vorhandene alte Pending-Settings aus bestehenden
Installationen.
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
    """Entfernt verbliebene Settings des früheren RFID-Lernmodus."""
    rows = db.query(Setting).filter(Setting.key.in_(LEGACY_PENDING_KEYS)).all()
    for row in rows:
        db.delete(row)
    if rows:
        db.commit()
    return len(rows)
