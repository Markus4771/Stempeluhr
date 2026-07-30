from datetime import date
from decimal import Decimal

import pytest

from app.services.vacation_calculation import (
    VacationModel,
    VacationPeriod,
    count_chargeable_vacation_days,
    entitlement_for_model,
    entitlement_for_periods,
    prorated_entitlement,
)


def test_weekend_is_not_charged():
    result = count_chargeable_vacation_days(date(2026, 8, 3), date(2026, 8, 9))
    assert result.chargeable_days == Decimal("5")
    assert result.weekend_days == 2


def test_full_holiday_is_not_charged():
    result = count_chargeable_vacation_days(
        date(2026, 12, 21),
        date(2026, 12, 25),
        holidays={date(2026, 12, 25): 1},
    )
    assert result.chargeable_days == Decimal("4")
    assert result.holiday_days == Decimal("1")


def test_half_holiday_reduces_charge():
    result = count_chargeable_vacation_days(
        date(2026, 12, 24),
        date(2026, 12, 24),
        holidays={date(2026, 12, 24): Decimal("0.5")},
    )
    assert result.chargeable_days == Decimal("0.5")


def test_half_day_requires_single_chargeable_workday():
    result = count_chargeable_vacation_days(
        date(2026, 8, 3),
        date(2026, 8, 3),
        half_day=True,
    )
    assert result.chargeable_days == Decimal("0.5")

    with pytest.raises(ValueError):
        count_chargeable_vacation_days(
            date(2026, 8, 8),
            date(2026, 8, 8),
            half_day=True,
        )


def test_fixed_part_time_uses_five_day_reference():
    assert entitlement_for_model(30, VacationModel.FIXED_PART_TIME, weekly_workdays=3) == Decimal("18")


def test_irregular_year_uses_260_day_reference():
    assert entitlement_for_model(30, VacationModel.IRREGULAR_YEAR, annual_workdays=130) == Decimal("15")


def test_manual_entitlement():
    assert entitlement_for_model(30, VacationModel.MANUAL, manual_entitlement=27.5) == Decimal("27.5")


def test_prorated_entitlement():
    assert prorated_entitlement(30, 6) == Decimal("15")


def test_schedule_change_is_calculated_by_period():
    result = entitlement_for_periods(
        30,
        [
            VacationPeriod(date(2026, 1, 1), date(2026, 6, 30), weekly_workdays=5),
            VacationPeriod(date(2026, 7, 1), date(2026, 12, 31), weekly_workdays=3),
        ],
        2026,
    )
    assert result == Decimal("24")
