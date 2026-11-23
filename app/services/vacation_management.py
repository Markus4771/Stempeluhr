from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Employee, Holiday, VacationRequest
from app.models_vacation import (
    VacationAccount,
    VacationLedgerEntry,
    VacationProfile,
    VacationRequestExtension,
    VacationSchedulePeriod,
)
from app.services.vacation_calculation import (
    VacationModel,
    VacationPeriod,
    count_chargeable_vacation_days,
    entitlement_for_model,
    entitlement_for_periods,
    prorated_entitlement,
)


VACATION_REQUEST_TYPES = {"abwesenheit", "urlaub"}


def holiday_map(db: Session, start_date: date, end_date: date) -> dict[date, Decimal]:
    rows = (
        db.query(Holiday)
        .filter(Holiday.active == True, Holiday.date >= start_date, Holiday.date <= end_date)
        .all()
    )
    return {row.date: Decimal("0.5") if row.half_day else Decimal("1") for row in rows}


def calculate_request_days(db: Session, start_date: date, end_date: date, half_day: bool = False):
    return count_chargeable_vacation_days(
        start_date,
        end_date,
        holidays=holiday_map(db, start_date, end_date),
        half_day=half_day,
    )


def get_or_create_profile(db: Session, employee: Employee) -> VacationProfile:
    # New Employee objects do not have a primary key until SQLAlchemy has
    # flushed the INSERT.  VacationProfile.employee_id is NOT NULL, so make
    # sure the employee exists in the database before creating its profile.
    if employee.id is None:
        db.flush()
    if employee.id is None:
        raise ValueError("Mitarbeiter konnte vor Anlage des Urlaubsprofils nicht gespeichert werden.")

    profile = db.query(VacationProfile).filter(VacationProfile.employee_id == employee.id).first()
    if profile:
        return profile
    profile = VacationProfile(
        employee_id=employee.id,
        calculation_model="five_day",
        base_entitlement=float(employee.vacation_days_total or 30.0),
        weekly_workdays=5.0,
        annual_workdays=260.0,
        automatic_proration=True,
        valid_from=employee.entry_date or employee.hired_at,
        valid_to=employee.exit_date or employee.left_at,
    )
    db.add(profile)
    db.flush()
    return profile


def full_employment_months(employee: Employee, year: int) -> int:
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    start = max(employee.entry_date or employee.hired_at or year_start, year_start)
    end = min(employee.exit_date or employee.left_at or year_end, year_end)
    if end < start:
        return 0

    months = 0
    for month in range(1, 13):
        month_start = date(year, month, 1)
        if month == 12:
            month_end = year_end
        else:
            month_end = date(year, month + 1, 1)
            month_end = date.fromordinal(month_end.toordinal() - 1)
        if start <= month_start and end >= month_end:
            months += 1
    return months


def annual_entitlement(db: Session, employee: Employee, year: int) -> Decimal:
    profile = get_or_create_profile(db, employee)
    periods = (
        db.query(VacationSchedulePeriod)
        .filter(
            VacationSchedulePeriod.employee_id == employee.id,
            VacationSchedulePeriod.end_date >= date(year, 1, 1),
            VacationSchedulePeriod.start_date <= date(year, 12, 31),
        )
        .order_by(VacationSchedulePeriod.start_date)
        .all()
    )

    if periods:
        value = entitlement_for_periods(
            profile.base_entitlement,
            [
                VacationPeriod(
                    p.start_date,
                    p.end_date,
                    weekly_workdays=Decimal(str(p.weekly_workdays)) if p.weekly_workdays is not None else None,
                    annual_workdays=Decimal(str(p.annual_workdays)) if p.annual_workdays is not None else None,
                )
                for p in periods
            ],
            year,
        )
    else:
        value = entitlement_for_model(
            profile.base_entitlement,
            VacationModel(profile.calculation_model or "five_day"),
            weekly_workdays=profile.weekly_workdays,
            annual_workdays=profile.annual_workdays,
            manual_entitlement=profile.manual_entitlement,
        )

    if profile.automatic_proration:
        months = full_employment_months(employee, year)
        if months < 12:
            value = prorated_entitlement(value, months)
    return value


def get_or_create_account(db: Session, employee: Employee, year: int, account_type: str = "annual") -> VacationAccount:
    account = (
        db.query(VacationAccount)
        .filter(
            VacationAccount.employee_id == employee.id,
            VacationAccount.year == year,
            VacationAccount.account_type == account_type,
        )
        .first()
    )
    if account:
        return account

    entitlement = float(annual_entitlement(db, employee, year)) if account_type == "annual" else 0.0
    account = VacationAccount(
        employee_id=employee.id,
        year=year,
        account_type=account_type,
        entitlement=entitlement,
        used=0.0,
        carried_over=0.0,
    )
    db.add(account)
    db.flush()
    return account


def account_balance(account: VacationAccount) -> float:
    return round(float(account.entitlement or 0) + float(account.carried_over or 0) - float(account.used or 0), 2)


def post_ledger(
    db: Session,
    employee: Employee,
    year: int,
    amount: float,
    action: str,
    actor: str,
    *,
    account_type: str = "annual",
    vacation_request_id: int | None = None,
    reason: str | None = None,
) -> VacationLedgerEntry:
    account = get_or_create_account(db, employee, year, account_type)
    account.used = round(float(account.used or 0) + amount, 2)
    account.updated_at = datetime.now()
    entry = VacationLedgerEntry(
        employee_id=employee.id,
        vacation_request_id=vacation_request_id,
        year=year,
        account_type=account_type,
        amount=amount,
        balance_after=account_balance(account),
        action=action,
        reason=reason,
        actor=actor,
    )
    db.add(entry)
    return entry


def ensure_request_extension(
    db: Session,
    request_row: VacationRequest,
    *,
    account_type: str = "annual",
    representative_employee_id: int | None = None,
    calculation_result=None,
) -> VacationRequestExtension:
    extension = (
        db.query(VacationRequestExtension)
        .filter(VacationRequestExtension.vacation_request_id == request_row.id)
        .first()
    )
    if not extension:
        extension = VacationRequestExtension(vacation_request_id=request_row.id)
        db.add(extension)
    extension.account_type = account_type or "annual"
    extension.representative_employee_id = representative_employee_id
    extension.updated_at = datetime.now()
    if calculation_result is not None:
        extension.calculation_details = json.dumps(
            {
                "chargeable_days": float(calculation_result.chargeable_days),
                "calendar_days": calculation_result.calendar_days,
                "weekend_days": calculation_result.weekend_days,
                "holiday_days": float(calculation_result.holiday_days),
                "reference_weekdays": 5,
            },
            ensure_ascii=False,
        )
    db.flush()
    return extension


def book_approved_request(db: Session, request_row: VacationRequest, actor: str) -> None:
    if request_row.request_type not in VACATION_REQUEST_TYPES:
        return
    extension = ensure_request_extension(db, request_row)
    existing = (
        db.query(VacationLedgerEntry)
        .filter(
            VacationLedgerEntry.vacation_request_id == request_row.id,
            VacationLedgerEntry.action == "vacation_approved",
        )
        .first()
    )
    if existing:
        return
    post_ledger(
        db,
        request_row.employee,
        request_row.start_date.year,
        float(request_row.days or 0),
        "vacation_approved",
        actor,
        account_type=extension.account_type,
        vacation_request_id=request_row.id,
        reason="Genehmigter Urlaubsantrag",
    )


def reverse_request(db: Session, request_row: VacationRequest, actor: str, action: str, reason: str) -> None:
    if request_row.request_type not in VACATION_REQUEST_TYPES:
        return
    extension = ensure_request_extension(db, request_row)
    already = (
        db.query(VacationLedgerEntry)
        .filter(VacationLedgerEntry.vacation_request_id == request_row.id, VacationLedgerEntry.action == action)
        .first()
    )
    if already:
        return
    post_ledger(
        db,
        request_row.employee,
        request_row.start_date.year,
        -float(request_row.days or 0),
        action,
        actor,
        account_type=extension.account_type,
        vacation_request_id=request_row.id,
        reason=reason,
    )
