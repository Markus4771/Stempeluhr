from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from typing import Iterable, Mapping, Sequence


FIVE_DAY_WEEK = Decimal("5")
STANDARD_WORKDAYS_PER_YEAR = Decimal("260")


class VacationModel(StrEnum):
    """Supported entitlement calculation models.

    All models use a five-day workweek as the company-wide reference basis.
    """

    FIVE_DAY = "five_day"
    FIXED_PART_TIME = "fixed_part_time"
    IRREGULAR_YEAR = "irregular_year"
    MANUAL = "manual"


@dataclass(frozen=True)
class VacationPeriod:
    start_date: date
    end_date: date
    weekly_workdays: Decimal | None = None
    annual_workdays: Decimal | None = None


@dataclass(frozen=True)
class VacationDayResult:
    chargeable_days: Decimal
    weekend_days: int
    holiday_days: Decimal
    calendar_days: int


def _decimal(value: Decimal | float | int | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def round_half_day(value: Decimal | float | int | str) -> Decimal:
    """Round vacation values to half days using commercial rounding."""

    number = _decimal(value)
    return (number * Decimal("2")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / Decimal("2")


def entitlement_for_model(
    base_entitlement: Decimal | float | int | str,
    model: VacationModel | str,
    *,
    weekly_workdays: Decimal | float | int | str | None = None,
    annual_workdays: Decimal | float | int | str | None = None,
    manual_entitlement: Decimal | float | int | str | None = None,
) -> Decimal:
    """Calculate the personal annual entitlement.

    ``base_entitlement`` is always the contractual entitlement for a five-day
    week. Part-time and irregular schedules are converted from that basis.
    """

    base = _decimal(base_entitlement)
    selected_model = VacationModel(model)

    if base < 0:
        raise ValueError("base_entitlement must not be negative")

    if selected_model is VacationModel.FIVE_DAY:
        return round_half_day(base)

    if selected_model is VacationModel.FIXED_PART_TIME:
        if weekly_workdays is None:
            raise ValueError("weekly_workdays is required")
        days = _decimal(weekly_workdays)
        if days < 0 or days > FIVE_DAY_WEEK:
            raise ValueError("weekly_workdays must be between 0 and 5")
        return round_half_day(base * days / FIVE_DAY_WEEK)

    if selected_model is VacationModel.IRREGULAR_YEAR:
        if annual_workdays is None:
            raise ValueError("annual_workdays is required")
        days = _decimal(annual_workdays)
        if days < 0:
            raise ValueError("annual_workdays must not be negative")
        return round_half_day(base * days / STANDARD_WORKDAYS_PER_YEAR)

    if manual_entitlement is None:
        raise ValueError("manual_entitlement is required")
    manual = _decimal(manual_entitlement)
    if manual < 0:
        raise ValueError("manual_entitlement must not be negative")
    return round_half_day(manual)


def prorated_entitlement(
    annual_entitlement: Decimal | float | int | str,
    full_months: int,
) -> Decimal:
    """Calculate one twelfth per full employment month."""

    if full_months < 0 or full_months > 12:
        raise ValueError("full_months must be between 0 and 12")
    return round_half_day(_decimal(annual_entitlement) * Decimal(full_months) / Decimal("12"))


def entitlement_for_periods(
    base_entitlement: Decimal | float | int | str,
    periods: Sequence[VacationPeriod],
    year: int,
) -> Decimal:
    """Calculate a year entitlement for changing work schedules.

    Each calendar day belongs to at most one period. The result is weighted by
    the number of calendar days in the period, then rounded once to half days.
    """

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    total_year_days = Decimal((year_end - year_start).days + 1)
    total = Decimal("0")
    occupied: set[date] = set()

    for period in periods:
        start = max(period.start_date, year_start)
        end = min(period.end_date, year_end)
        if end < start:
            continue

        current = start
        period_days = 0
        while current <= end:
            if current in occupied:
                raise ValueError("vacation periods must not overlap")
            occupied.add(current)
            period_days += 1
            current += timedelta(days=1)

        if period.weekly_workdays is not None:
            period_entitlement = entitlement_for_model(
                base_entitlement,
                VacationModel.FIXED_PART_TIME,
                weekly_workdays=period.weekly_workdays,
            )
        elif period.annual_workdays is not None:
            period_entitlement = entitlement_for_model(
                base_entitlement,
                VacationModel.IRREGULAR_YEAR,
                annual_workdays=period.annual_workdays,
            )
        else:
            period_entitlement = entitlement_for_model(base_entitlement, VacationModel.FIVE_DAY)

        total += period_entitlement * Decimal(period_days) / total_year_days

    return round_half_day(total)


def count_chargeable_vacation_days(
    start_date: date,
    end_date: date,
    *,
    holidays: Mapping[date, Decimal | float | int | str] | Iterable[date] = (),
    half_day: bool = False,
) -> VacationDayResult:
    """Count vacation days from Monday to Friday only.

    Weekends are never charged. Holidays are skipped; a holiday value of 0.5
    reduces the charge by half a day. A half-day request is valid only when the
    selected date is a chargeable workday.
    """

    if end_date < start_date:
        raise ValueError("end_date must not be before start_date")

    if isinstance(holidays, Mapping):
        holiday_values = {day: _decimal(value) for day, value in holidays.items()}
    else:
        holiday_values = {day: Decimal("1") for day in holidays}

    current = start_date
    chargeable = Decimal("0")
    weekend_days = 0
    holiday_days = Decimal("0")
    calendar_days = 0

    while current <= end_date:
        calendar_days += 1
        if current.weekday() >= 5:
            weekend_days += 1
            current += timedelta(days=1)
            continue

        holiday_fraction = min(Decimal("1"), max(Decimal("0"), holiday_values.get(current, Decimal("0"))))
        if holiday_fraction:
            holiday_days += holiday_fraction
        chargeable += Decimal("1") - holiday_fraction
        current += timedelta(days=1)

    if half_day:
        if start_date != end_date:
            raise ValueError("half-day vacation requires a single date")
        if chargeable <= 0:
            raise ValueError("half-day vacation requires a chargeable workday")
        chargeable = Decimal("0.5")

    return VacationDayResult(
        chargeable_days=round_half_day(chargeable),
        weekend_days=weekend_days,
        holiday_days=holiday_days,
        calendar_days=calendar_days,
    )
