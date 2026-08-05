from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, inspect, text
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models import Employee


class EmployeeRfidMedia(Base):
    """Beliebig viele RFID-/NFC-Medien je Mitarbeiter."""

    __tablename__ = "employee_rfid_media"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    uid = Column(String(128), nullable=False, unique=True, index=True)
    uid_raw = Column(String(255), nullable=True)
    name = Column(String(150), nullable=False, default="RFID/NFC-Medium")
    media_type = Column(String(50), nullable=False, default="rfid")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    last_used_at = Column(DateTime, nullable=True)


def normalize_rfid_uid(value: str | None) -> str:
    """Normalisiert Leser-Ausgaben für einen stabilen Vergleich.

    Entfernt Steuerzeichen, Leerzeichen und übliche Trennzeichen. Hex-Zeichen
    werden vereinheitlicht. Andere Reader-IDs bleiben als Großbuchstaben erhalten.
    """
    if not value:
        return ""
    cleaned = str(value).replace("\\r", "").replace("\\n", "").strip().upper()
    cleaned = re.sub(r"[\s:\-_.]", "", cleaned)
    return cleaned


def ensure_rfid_media_schema() -> None:
    """Legt die Medientabelle an und übernimmt vorhandene Mitarbeiter-RFIDs."""
    Base.metadata.create_all(bind=engine, tables=[EmployeeRfidMedia.__table__])

    with engine.begin() as conn:
        dialect = conn.dialect.name
        if inspect(conn).has_table("employee_rfid_media"):
            if dialect == "postgresql":
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_employee_rfid_media_employee_id ON employee_rfid_media (employee_id)"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_employee_rfid_media_uid ON employee_rfid_media (uid)"))

        if not inspect(conn).has_table("employees"):
            return

        rows = conn.execute(text("SELECT id, rfid_code FROM employees WHERE rfid_code IS NOT NULL AND TRIM(rfid_code) <> ''")).fetchall()
        for employee_id, raw_uid in rows:
            uid = normalize_rfid_uid(raw_uid)
            if not uid:
                continue
            exists = conn.execute(text("SELECT 1 FROM employee_rfid_media WHERE uid = :uid"), {"uid": uid}).first()
            if exists:
                continue
            conn.execute(
                text(
                    "INSERT INTO employee_rfid_media "
                    "(employee_id, uid, uid_raw, name, media_type, active, created_at) "
                    "VALUES (:employee_id, :uid, :uid_raw, :name, :media_type, :active, :created_at)"
                ),
                {
                    "employee_id": employee_id,
                    "uid": uid,
                    "uid_raw": str(raw_uid),
                    "name": "Bestehende RFID-Karte",
                    "media_type": "rfid",
                    "active": True,
                    "created_at": datetime.now(),
                },
            )


def resolve_employee_by_rfid(db: Session, raw_uid: str | None) -> tuple[Employee | None, EmployeeRfidMedia | None]:
    uid = normalize_rfid_uid(raw_uid)
    if not uid:
        return None, None

    medium = (
        db.query(EmployeeRfidMedia)
        .filter(EmployeeRfidMedia.uid == uid, EmployeeRfidMedia.active.is_(True))
        .first()
    )
    if medium:
        employee = db.query(Employee).filter(Employee.id == medium.employee_id, Employee.active.is_(True)).first()
        if employee:
            medium.last_used_at = datetime.now()
            return employee, medium

    # Abwärtskompatibilität, falls die Startmigration noch nicht gelaufen ist.
    for employee in db.query(Employee).filter(Employee.rfid_code.isnot(None), Employee.active.is_(True)).all():
        if normalize_rfid_uid(employee.rfid_code) == uid:
            return employee, None
    return None, None


def add_rfid_medium(
    db: Session,
    employee_id: int,
    raw_uid: str,
    name: str = "RFID/NFC-Medium",
    media_type: str = "rfid",
) -> EmployeeRfidMedia:
    uid = normalize_rfid_uid(raw_uid)
    if not uid:
        raise ValueError("Leere RFID-/NFC-ID")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise ValueError("Mitarbeiter nicht gefunden")

    existing = db.query(EmployeeRfidMedia).filter(EmployeeRfidMedia.uid == uid).first()
    if existing:
        if existing.employee_id != employee_id:
            raise ValueError("Dieses Medium ist bereits einem anderen Mitarbeiter zugeordnet")
        existing.uid_raw = raw_uid
        existing.name = name.strip() or existing.name
        existing.media_type = media_type.strip().lower() or existing.media_type
        existing.active = True
        return existing

    medium = EmployeeRfidMedia(
        employee_id=employee_id,
        uid=uid,
        uid_raw=raw_uid,
        name=name.strip() or "RFID/NFC-Medium",
        media_type=media_type.strip().lower() or "rfid",
        active=True,
    )
    db.add(medium)
    return medium
