"""Bestätigungspflichtiger Überstunden-Reset per E-Mail."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models import AuditLog, Employee


class OvertimeResetRequest(Base):
    __tablename__ = "overtime_reset_requests"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    previous_balance = Column(Float, nullable=False, default=0.0)
    requested_by = Column(String(100), nullable=False)
    requested_at = Column(DateTime, nullable=False, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    status = Column(String(30), nullable=False, default="pending")
    note = Column(Text, nullable=True)


def ensure_overtime_reset_schema() -> None:
    Base.metadata.create_all(bind=engine, tables=[OvertimeResetRequest.__table__])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_overtime_reset_request(db: Session, employee: Employee, requested_by: str, note: str = "") -> tuple[OvertimeResetRequest, str]:
    now = datetime.now()
    db.query(OvertimeResetRequest).filter(
        OvertimeResetRequest.employee_id == employee.id,
        OvertimeResetRequest.status == "pending",
    ).update({"status": "cancelled", "cancelled_at": now})

    token = secrets.token_urlsafe(32)
    row = OvertimeResetRequest(
        employee_id=employee.id,
        token_hash=_hash_token(token),
        previous_balance=float(employee.overtime_balance or 0.0),
        requested_by=requested_by,
        requested_at=now,
        expires_at=now + timedelta(hours=72),
        status="pending",
        note=(note or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, token


def confirm_overtime_reset(db: Session, token: str) -> tuple[OvertimeResetRequest | None, Employee | None, str]:
    row = db.query(OvertimeResetRequest).filter(OvertimeResetRequest.token_hash == _hash_token(token)).first()
    if not row:
        return None, None, "Ungültiger Bestätigungslink."
    if row.status != "pending" or row.confirmed_at or row.cancelled_at:
        return row, None, "Dieser Bestätigungslink wurde bereits verwendet oder widerrufen."
    if row.expires_at < datetime.now():
        row.status = "expired"
        db.commit()
        return row, None, "Der Bestätigungslink ist abgelaufen."

    employee = db.query(Employee).filter(Employee.id == row.employee_id).first()
    if not employee:
        return row, None, "Mitarbeiter wurde nicht gefunden."

    old_balance = float(employee.overtime_balance or 0.0)
    employee.overtime_balance = 0.0
    row.previous_balance = old_balance
    row.confirmed_at = datetime.now()
    row.status = "confirmed"
    db.add(AuditLog(
        actor=f"Mitarbeiter {employee.employee_number}",
        action="overtime_reset_confirmed",
        entity="employee",
        entity_id=str(employee.id),
        details=f"Überstundenkonto nach E-Mail-Bestätigung von {old_balance:.2f} h auf 0.00 h zurückgesetzt; angefordert von {row.requested_by}.",
    ))
    db.commit()
    return row, employee, "Überstunden wurden erfolgreich auf 0,00 Stunden zurückgesetzt."
