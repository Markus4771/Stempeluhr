"""Allgemeines Datenmodell für Anmeldemedien in Stempeluhr 6.x."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models import Employee
from app.services.rfid_media import normalize_rfid_uid


class EmployeeAuthCredential(Base):
    __tablename__ = "employee_auth_credentials"
    __table_args__ = (
        UniqueConstraint("provider", "identifier_hash", name="ux_auth_credential_provider_identifier"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(100), nullable=False, index=True)
    credential_type = Column(String(100), nullable=False, index=True)
    identifier_hash = Column(String(64), nullable=False, index=True)
    identifier_hint = Column(String(255), nullable=True)
    display_name = Column(String(150), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(Text, nullable=True)


def credential_identifier_hash(provider: str, identifier: str) -> str:
    normalized_provider = str(provider or "").strip().lower()
    normalized_identifier = str(identifier or "").strip()
    if normalized_provider == "rfid":
        normalized_identifier = normalize_rfid_uid(normalized_identifier)
    return hashlib.sha256(f"{normalized_provider}\0{normalized_identifier}".encode("utf-8")).hexdigest()


def credential_identifier_hint(provider: str, identifier: str) -> str:
    """Nur eine ungefährliche Anzeigehilfe speichern, niemals PINs oder Tokens im Klartext."""
    provider = str(provider or "").strip().lower()
    identifier = str(identifier or "").strip()
    if provider in {"pin", "mobile_app", "smartwatch", "fido2", "bluetooth"}:
        return "••••••••"
    if provider == "fingerprint":
        return "Biometrische Vorlage"
    if len(identifier) > 16:
        return f"{identifier[:6]}…{identifier[-4:]}"
    return identifier


def ensure_auth_credential_schema() -> None:
    """Legt nur die generische Credential-Tabelle an.

    RFID-/NFC-UIDs werden ab Stempeluhr 6.0 ausschließlich über
    ``employee_rfid_media`` verwaltet. Frühere Versionen spiegelten diese
    Datensätze zusätzlich als provider='rfid' nach
    ``employee_auth_credentials``. Diese Spiegelung war redundant und konnte
    nach Änderungen oder Neu-Zuordnungen zu widersprüchlichen Besitzern führen.
    Bestehende Alt-Datensätze werden hier bewusst nicht neu erzeugt.
    """
    Base.metadata.create_all(bind=engine, tables=[EmployeeAuthCredential.__table__])


def list_employee_credentials(db: Session, employee_id: int) -> list[EmployeeAuthCredential]:
    return (
        db.query(EmployeeAuthCredential)
        .filter(EmployeeAuthCredential.employee_id == employee_id)
        .order_by(EmployeeAuthCredential.provider, EmployeeAuthCredential.display_name)
        .all()
    )


def add_auth_credential(
    db: Session,
    *,
    employee_id: int,
    provider: str,
    credential_type: str,
    identifier: str,
    display_name: str,
    metadata: dict[str, Any] | None = None,
) -> EmployeeAuthCredential:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise ValueError("Mitarbeiter nicht gefunden")
    provider = str(provider or "").strip().lower()
    credential_type = str(credential_type or provider).strip().lower()
    identifier = str(identifier or "").strip()
    if not provider or not identifier:
        raise ValueError("Provider und Kennung sind erforderlich")
    identifier_hash = credential_identifier_hash(provider, identifier)
    hint = credential_identifier_hint(provider, identifier)
    existing = db.query(EmployeeAuthCredential).filter(
        EmployeeAuthCredential.provider == provider,
        EmployeeAuthCredential.identifier_hash == identifier_hash,
    ).first()
    if existing:
        if existing.employee_id != employee_id:
            raise ValueError("Dieses Anmeldemedium gehört bereits zu einem anderen Mitarbeiter")
        existing.active = True
        existing.revoked_at = None
        existing.revoked_reason = None
        existing.display_name = display_name.strip() or existing.display_name
        existing.credential_type = credential_type
        existing.identifier_hint = hint
        existing.metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        existing.updated_at = datetime.now()
        return existing
    row = EmployeeAuthCredential(
        employee_id=employee_id,
        provider=provider,
        credential_type=credential_type,
        identifier_hash=identifier_hash,
        identifier_hint=hint,
        display_name=display_name.strip() or f"{provider}-Medium",
        active=True,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.add(row)
    return row


def revoke_auth_credential(db: Session, credential_id: int, reason: str = "Manuell gesperrt") -> EmployeeAuthCredential:
    row = db.query(EmployeeAuthCredential).filter(EmployeeAuthCredential.id == credential_id).first()
    if not row:
        raise ValueError("Anmeldemedium nicht gefunden")
    row.active = False
    row.revoked_at = datetime.now()
    row.revoked_reason = reason.strip() or "Manuell gesperrt"
    row.updated_at = datetime.now()
    return row


def activate_auth_credential(db: Session, credential_id: int) -> EmployeeAuthCredential:
    row = db.query(EmployeeAuthCredential).filter(EmployeeAuthCredential.id == credential_id).first()
    if not row:
        raise ValueError("Anmeldemedium nicht gefunden")
    row.active = True
    row.revoked_at = None
    row.revoked_reason = None
    row.updated_at = datetime.now()
    return row
