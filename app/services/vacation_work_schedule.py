from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import Employee, Holiday, VacationRequest


WEEKDAY_FIELDS = (
    "monday_hours",
    "tuesday_hours",
    "wednesday_hours",
    "thursday_hours",
    "friday_hours",
    "saturday_hours",
    "sunday_hours",
)


def scheduled_hours_for_weekday(employee: Employee, weekday: int) -> float:
    if weekday < 0 or weekday > 6:
        return 0.0
    try:
        return max(0.0, float(getattr(employee, WEEKDAY_FIELDS[weekday], 0.0) or 0.0))
    except Exception:
        return 0.0


def scheduled_hours_for_date(employee: Employee, day: date) -> float:
    return scheduled_hours_for_weekday(employee, day.weekday())


def regular_workdays_per_week(employee: Employee) -> int:
    return sum(1 for weekday in range(7) if scheduled_hours_for_weekday(employee, weekday) > 0)


def regular_weekly_hours(employee: Employee) -> float:
    return round(sum(scheduled_hours_for_weekday(employee, weekday) for weekday in range(7)), 2)


def _round_half_day(value: Decimal) -> Decimal:
    return (value * Decimal("2")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / Decimal("2")


def entitlement_from_employee_schedule(base_entitlement: float | Decimal, employee: Employee) -> Decimal:
    """Urlaubsanspruch aus einem 5-Tage-Basisanspruch und den echten Arbeitstagen.

    Beispiel: 30 Tage Basisurlaub, 4 regelmäßige Arbeitstage -> 24 Tage.
    Die Stundenlänge der einzelnen Arbeitstage verändert die Anzahl Urlaubstage
    nicht; sie wird separat als Sollzeit des Urlaubstags verwendet.
    """
    workdays = regular_workdays_per_week(employee)
    base = Decimal(str(base_entitlement or 0))
    if workdays <= 0:
        return Decimal("0")
    # Vertragsbasis ist weiterhin die übliche 5-Tage-Woche. Sechs-/Sieben-Tage-
    # Modelle werden proportional unterstützt statt still auf fünf zu begrenzen.
    return _round_half_day(base * Decimal(workdays) / Decimal("5"))


def vacation_days_and_hours(
    db: Session,
    employee: Employee,
    start_date: date,
    end_date: date,
    *,
    half_day: bool = False,
) -> tuple[float, float]:
    """Berechnet Urlaubsverbrauch und Sollzeitgutschrift für den Arbeitsplan.

    Nur Tage mit positiver individueller Sollzeit zählen. Ganze Feiertage
    verbrauchen keinen Urlaub. Halbe Feiertage verbrauchen einen halben Tag und
    schreiben nur die verbleibende Hälfte der individuellen Sollzeit gut.
    """
    if end_date < start_date:
        return 0.0, 0.0

    holidays = {
        row.date: (0.5 if bool(getattr(row, "half_day", False)) else 1.0)
        for row in db.query(Holiday).filter(
            Holiday.active == True,
            Holiday.date >= start_date,
            Holiday.date <= end_date,
        ).all()
    }

    days = Decimal("0")
    hours = Decimal("0")
    current = start_date
    while current <= end_date:
        scheduled = Decimal(str(scheduled_hours_for_date(employee, current)))
        if scheduled > 0:
            holiday_fraction = Decimal(str(holidays.get(current, 0.0)))
            holiday_fraction = min(Decimal("1"), max(Decimal("0"), holiday_fraction))
            charge = Decimal("1") - holiday_fraction
            if charge > 0:
                days += charge
                hours += scheduled * charge
        current += timedelta(days=1)

    if half_day:
        # Halber Urlaub ist nur für einen einzelnen regulären Arbeitstag erlaubt.
        if start_date != end_date:
            return 0.0, 0.0
        scheduled = Decimal(str(scheduled_hours_for_date(employee, start_date)))
        holiday_fraction = Decimal(str(holidays.get(start_date, 0.0)))
        if scheduled <= 0 or holiday_fraction >= Decimal("1"):
            return 0.0, 0.0
        days = Decimal("0.5")
        hours = scheduled * Decimal("0.5")

    return float(_round_half_day(days)), round(float(hours), 2)


def _recalculate_request(session: Session, request_row: VacationRequest) -> None:
    if request_row.request_type not in {"abwesenheit", "urlaub"}:
        return
    employee = request_row.employee
    if employee is None and request_row.employee_id:
        employee = session.query(Employee).filter(Employee.id == request_row.employee_id).first()
    if employee is None or not request_row.start_date or not request_row.end_date:
        return
    days, _hours = vacation_days_and_hours(
        session,
        employee,
        request_row.start_date,
        request_row.end_date,
        half_day=bool(request_row.half_day),
    )
    request_row.days = days


_registered = False


def register_vacation_work_schedule_events() -> None:
    """Aktiviert die arbeitsplanabhängige Urlaubsberechnung zentral."""
    global _registered
    if _registered:
        return

    @event.listens_for(Session, "before_flush")
    def _vacation_schedule_before_flush(session, flush_context, instances):
        candidates = set(session.new).union(session.dirty)
        for obj in candidates:
            if isinstance(obj, VacationRequest):
                _recalculate_request(session, obj)

    _registered = True
