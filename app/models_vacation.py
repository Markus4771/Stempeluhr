from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class VacationProfile(Base):
    """Berechnungsprofil eines Mitarbeiters.

    Die betriebliche Referenz bleibt unabhängig vom Modell immer eine
    Fünf-Tage-Woche.
    """

    __tablename__ = "vacation_profiles"
    __table_args__ = (UniqueConstraint("employee_id", name="uq_vacation_profile_employee"),)

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    calculation_model = Column(String(30), default="five_day", nullable=False)
    base_entitlement = Column(Float, default=30.0, nullable=False)
    weekly_workdays = Column(Float, default=5.0, nullable=False)
    annual_workdays = Column(Float, default=260.0, nullable=False)
    manual_entitlement = Column(Float, nullable=True)
    federal_state = Column(String(50), nullable=True)
    automatic_proration = Column(Boolean, default=True)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

    employee = relationship("Employee", foreign_keys=[employee_id])


class VacationSchedulePeriod(Base):
    """Zeitabschnitt für Änderungen des Arbeitszeitmodells im laufenden Jahr."""

    __tablename__ = "vacation_schedule_periods"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    weekly_workdays = Column(Float, nullable=True)
    annual_workdays = Column(Float, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class VacationAccount(Base):
    """Getrennte Urlaubskonten je Mitarbeiter und Jahr."""

    __tablename__ = "vacation_accounts"
    __table_args__ = (UniqueConstraint("employee_id", "year", "account_type", name="uq_vacation_account"),)

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    account_type = Column(String(40), nullable=False, default="annual")
    entitlement = Column(Float, default=0.0)
    used = Column(Float, default=0.0)
    carried_over = Column(Float, default=0.0)
    expires_on = Column(Date, nullable=True)
    note = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now)


class VacationLedgerEntry(Base):
    """Revisionssicheres Buchungsjournal für alle Kontobewegungen."""

    __tablename__ = "vacation_ledger_entries"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    vacation_request_id = Column(Integer, ForeignKey("vacation_requests.id"), nullable=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    account_type = Column(String(40), nullable=False, default="annual")
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=True)
    action = Column(String(60), nullable=False)
    reason = Column(Text, nullable=True)
    actor = Column(String(100), nullable=False, default="SYSTEM")
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class VacationRequestExtension(Base):
    """Erweiterte Angaben, ohne alte vacation_requests zu verändern."""

    __tablename__ = "vacation_request_extensions"
    __table_args__ = (UniqueConstraint("vacation_request_id", name="uq_vacation_request_extension"),)

    id = Column(Integer, primary_key=True)
    vacation_request_id = Column(Integer, ForeignKey("vacation_requests.id"), nullable=False, index=True)
    representative_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    account_type = Column(String(40), default="annual", nullable=False)
    approval_stage = Column(Integer, default=1)
    hr_confirmation_required = Column(Boolean, default=False)
    hr_confirmed_at = Column(DateTime, nullable=True)
    hr_confirmed_by = Column(String(100), nullable=True)
    illness_converted_at = Column(DateTime, nullable=True)
    illness_converted_by = Column(String(100), nullable=True)
    calculation_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)


class CompanyClosure(Base):
    """Betriebsferien für Firma oder einzelne Abteilungen."""

    __tablename__ = "company_closures"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    deduct_vacation = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
