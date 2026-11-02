"""Tests fuer die Tagesberechnung und die Hilfsfunktionen in worktime.py.

calculate_period ist in tests/test_worktime_calculation.py abgedeckt. Hier
geht es um die Einzelberechnung je Tag: Zustandsuebergaenge der Buchungen,
die automatische Pausenberechnung und die Sollstunden.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_TYPE", "sqlite")

from app.models import Base, Employee, Holiday, Role, Setting, TimeEntry  # noqa: E402
from app.services.worktime import (  # noqa: E402
    _as_bool,
    _as_float,
    _month_bounds,
    _seconds_between,
    _setting_value,
    calculate_day,
    get_break_settings,
    holiday_adjusted_target_hours,
    target_hours_for_date,
)

MONDAY = date(2026, 10, 5)
TUESDAY = date(2026, 10, 6)


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'worktime_day.db'}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    session.add(Role(id=1, name="Administrator"))
    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def employee(db):
    emp = Employee(
        id=1, employee_number="E001", first_name="Max", last_name="Mustermann",
        role_id=1, active=True,
        monday_hours=8.0, tuesday_hours=8.0, wednesday_hours=8.0,
        thursday_hours=8.0, friday_hours=8.0, saturday_hours=0, sunday_hours=0,
        auto_break_enabled=True,
    )
    db.add(emp)
    db.commit()
    return emp


def _entry(entry_type, day=MONDAY, hour=8, minute=0, deleted=False):
    return TimeEntry(
        employee_id=1,
        timestamp=datetime(day.year, day.month, day.day, hour, minute),
        entry_type=entry_type,
        method="web",
        deleted=deleted,
    )


def _no_break_settings():
    """Pausenregelung aus, damit nur die manuelle Pause zaehlt."""
    return {
        "enabled": False,
        "threshold_1_hours": 6.0,
        "deduct_1_minutes": 30.0,
        "threshold_2_hours": 9.0,
        "deduct_2_minutes": 45.0,
        "only_missing_break": True,
    }


# --- Hilfsfunktionen -------------------------------------------------------

@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "ja", "on", "aktiv", "enabled", "  Ja  "])
def test_as_bool_reads_truthy_values(value):
    assert _as_bool(value) is True


@pytest.mark.parametrize("value", ["0", "false", "no", "nein", "off", "inaktiv", "disabled", ""])
def test_as_bool_reads_falsy_values(value):
    assert _as_bool(value) is False


def test_as_bool_uses_default_for_missing_value():
    assert _as_bool(None, True) is True
    assert _as_bool("", True) is True
    assert _as_bool(None, False) is False


def test_as_bool_accepts_boolean_input():
    assert _as_bool(True) is True
    assert _as_bool(False) is False


@pytest.mark.parametrize("value,expected", [("8", 8.0), ("8.5", 8.5), ("8,5", 8.5), (" 7.25 ", 7.25)])
def test_as_float_parses_numbers(value, expected):
    assert _as_float(value, 0.0) == expected


@pytest.mark.parametrize("value", ["", "keine Zahl", "abc", None])
def test_as_float_uses_default_for_unparsable_values(value):
    assert _as_float(value, 42.0) == 42.0


def test_setting_value_distinguishes_missing_and_empty():
    settings = {"a": "", "b": None}
    assert _setting_value(settings, "a", "default") == ""
    assert _setting_value(settings, "b", "default") == "default"
    assert _setting_value(settings, "c", "default") == "default"


def test_setting_value_keeps_stored_value():
    assert _setting_value({"a": "0"}, "a", "fallback") == "0"


def test_seconds_between_measures_the_gap():
    start = datetime(2026, 10, 5, 8, 0)
    end = datetime(2026, 10, 5, 16, 30)
    assert _seconds_between(start, end) == 8.5 * 3600


@pytest.mark.parametrize("start,end", [
    (None, datetime(2026, 10, 5, 16, 0)),
    (datetime(2026, 10, 5, 8, 0), None),
    (None, None),
])
def test_seconds_between_returns_zero_for_missing_endpoints(start, end):
    assert _seconds_between(start, end) == 0.0


def test_seconds_between_returns_zero_for_reversed_interval():
    start = datetime(2026, 10, 5, 16, 0)
    end = datetime(2026, 10, 5, 8, 0)
    assert _seconds_between(start, end) == 0.0


@pytest.mark.parametrize("year,month,expected_start,expected_end", [
    (2026, 1, date(2026, 1, 1), date(2026, 1, 31)),
    (2026, 2, date(2026, 2, 1), date(2026, 2, 28)),
    (2024, 2, date(2024, 2, 1), date(2024, 2, 29)),
    (2026, 4, date(2026, 4, 1), date(2026, 4, 30)),
    (2026, 12, date(2026, 12, 1), date(2026, 12, 31)),
])
def test_month_bounds_covers_the_whole_month(year, month, expected_start, expected_end):
    start, end = _month_bounds(year, month)
    assert start == expected_start
    assert end == expected_end


# --- Sollstunden -----------------------------------------------------------

def test_target_hours_uses_the_weekday(employee):
    assert target_hours_for_date(employee, MONDAY) == 8.0
    assert target_hours_for_date(employee, TUESDAY) == 8.0


def test_target_hours_is_zero_on_a_free_weekend(employee):
    assert target_hours_for_date(employee, date(2026, 10, 10)) == 0.0
    assert target_hours_for_date(employee, date(2026, 10, 11)) == 0.0


def test_target_hours_is_zero_when_no_hours_are_set(employee):
    employee.monday_hours = None
    assert target_hours_for_date(employee, MONDAY) == 0.0


def test_target_hours_is_zero_for_an_employee_with_a_missing_day(employee):
    """Ein Wochentag ohne hinterlegte Stunden ergibt kein Soll."""
    employee.monday_hours = None
    assert target_hours_for_date(employee, MONDAY) == 0.0


# --- Feiertage --------------------------------------------------------------

def test_full_holiday_sets_the_target_to_zero(db, employee):
    db.add(Holiday(id=1, name="Tag der Einheit", date=MONDAY, half_day=False, active=True))
    db.commit()
    assert holiday_adjusted_target_hours(db, employee, MONDAY) == 0.0


def test_half_holiday_halves_the_target(db, employee):
    db.add(Holiday(id=1, name="Halber Tag", date=MONDAY, half_day=True, active=True))
    db.commit()
    assert holiday_adjusted_target_hours(db, employee, MONDAY) == 4.0


def test_inactive_holiday_does_not_change_the_target(db, employee):
    db.add(Holiday(id=1, name="Inaktiv", date=MONDAY, half_day=False, active=False))
    db.commit()
    assert holiday_adjusted_target_hours(db, employee, MONDAY) == 8.0


def test_holiday_can_be_switched_off_in_the_settings(db, employee):
    db.add(Holiday(id=1, name="Tag der Einheit", date=MONDAY, half_day=False, active=True))
    db.add(Setting(id=1, key="caldav_holidays_affect_target_hours", value="false"))
    db.commit()
    assert holiday_adjusted_target_hours(db, employee, MONDAY) == 8.0


def test_half_day_factor_is_configurable(db, employee):
    db.add(Holiday(id=1, name="Halber Tag", date=MONDAY, half_day=True, active=True))
    db.add(Setting(id=1, key="caldav_half_day_factor", value="0.25"))
    db.commit()
    assert holiday_adjusted_target_hours(db, employee, MONDAY) == 2.0


def test_half_day_factor_is_limited_to_the_range_between_zero_and_one(db, employee):
    db.add(Holiday(id=1, name="Halber Tag", date=MONDAY, half_day=True, active=True))
    db.add(Setting(id=1, key="caldav_half_day_factor", value="3"))
    db.commit()
    assert holiday_adjusted_target_hours(db, employee, MONDAY) == 8.0


def test_holiday_does_not_change_the_target_without_work_hours(db, employee):
    employee.monday_hours = 0.0
    db.add(Holiday(id=1, name="Tag der Einheit", date=MONDAY, half_day=False, active=True))
    db.commit()
    assert holiday_adjusted_target_hours(db, employee, MONDAY) == 0.0


# --- calculate_day: Bruttozeit ---------------------------------------------

def test_a_complete_workday_is_counted_in_full(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.gross_hours == 8.0
    assert result.net_hours == 8.0
    assert result.incomplete is False


def test_two_work_periods_are_added_up(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("gehen", hour=12),
        _entry("kommen", hour=13),
        _entry("gehen", hour=17),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.gross_hours == 8.0
    assert result.incomplete is False


def test_entries_are_sorted_by_time_before_evaluating(employee):
    entries = [
        _entry("gehen", hour=16),
        _entry("kommen", hour=8),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.gross_hours == 8.0
    assert result.incomplete is False


def test_a_day_without_entries_has_no_work_time(employee):
    result = calculate_day(employee, [], MONDAY, _no_break_settings())
    assert result.gross_hours == 0.0
    assert result.net_hours == 0.0
    assert result.incomplete is False


def test_a_missing_exit_marks_the_day_incomplete(employee):
    entries = [_entry("kommen", hour=8)]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.incomplete is True
    assert result.gross_hours == 0.0


def test_an_exit_without_an_entry_marks_the_day_incomplete(employee):
    entries = [_entry("gehen", hour=16)]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.incomplete is True


def test_a_second_entry_marks_the_day_incomplete(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("kommen", hour=9),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.incomplete is True
    assert result.gross_hours == 7.0


def test_the_target_is_taken_from_the_weekday(employee):
    result = calculate_day(employee, [], MONDAY, _no_break_settings())
    assert result.target_hours == 8.0
    assert result.overtime_hours == -8.0


def test_overtime_is_calculated_from_the_net_time(employee):
    entries = [_entry("kommen", hour=8), _entry("gehen", hour=17)]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.overtime_hours == 1.0


def test_the_result_carries_the_employee_name(employee):
    result = calculate_day(employee, [], MONDAY, _no_break_settings())
    assert result.employee_name == "Max Mustermann"
    assert result.employee_id == employee.id
    assert result.date == MONDAY


# --- calculate_day: manuelle Pausen ----------------------------------------

def test_a_manual_pause_is_deducted(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("pause_start", hour=12),
        _entry("pause_ende", hour=12, minute=30),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.gross_hours == 8.0
    assert result.manual_break_hours == 0.5
    assert result.break_hours == 0.5
    assert result.net_hours == 7.5


def test_several_manual_pauses_are_added_up(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("pause_start", hour=11),
        _entry("pause_ende", hour=11, minute=30),
        _entry("pause_start", hour=14),
        _entry("pause_ende", hour=14, minute=15),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.manual_break_hours == 0.75
    assert result.net_hours == 7.25


def test_an_open_pause_is_closed_by_the_exit(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("pause_start", hour=12),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.manual_break_hours == 4.0
    assert result.net_hours == 4.0
    assert result.incomplete is False


def test_a_pause_end_without_a_start_marks_the_day_incomplete(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("pause_ende", hour=12),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.incomplete is True


def test_a_pause_start_without_an_entry_is_ignored(employee):
    entries = [
        _entry("pause_start", hour=12),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.gross_hours == 0.0
    assert result.manual_break_hours == 0.0
    assert result.incomplete is True


def test_a_pause_end_without_a_start_does_not_add_break_time(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("pause_ende", hour=12),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.manual_break_hours == 0.0
    assert result.net_hours == 8.0


def test_a_pause_start_after_the_exit_is_ignored(employee):
    """Eine Pause nach dem Gehen gehoert zu keinem laufenden Arbeitszeitraum."""
    entries = [
        _entry("kommen", hour=8),
        _entry("gehen", hour=16),
        _entry("pause_start", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _no_break_settings())
    assert result.gross_hours == 8.0
    assert result.manual_break_hours == 0.0


def test_the_net_time_never_becomes_negative(employee):
    """Die automatische Pause kann die Bruttozeit nicht in Minus druecken."""
    settings = _auto_break_settings(only_missing=True, threshold_1=0.5, deduct_1=120)
    entries = [_entry("kommen", hour=8), _entry("gehen", hour=9)]
    result = calculate_day(employee, entries, MONDAY, settings)
    assert result.gross_hours == 1.0
    assert result.break_hours == 2.0
    assert result.net_hours == 0.0


# --- calculate_day: automatische Pausen ------------------------------------

def _auto_break_settings(enabled=True, threshold_1=6.0, deduct_1=30.0,
                         threshold_2=9.0, deduct_2=45.0, only_missing=True):
    return {
        "enabled": enabled,
        "threshold_1_hours": threshold_1,
        "deduct_1_minutes": deduct_1,
        "threshold_2_hours": threshold_2,
        "deduct_2_minutes": deduct_2,
        "only_missing_break": only_missing,
    }


def test_no_auto_break_below_the_first_threshold(employee):
    entries = [_entry("kommen", hour=8), _entry("gehen", hour=13)]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings())
    assert result.gross_hours == 5.0
    assert result.auto_break_hours == 0.0
    assert result.net_hours == 5.0


def test_auto_break_above_the_first_threshold(employee):
    entries = [_entry("kommen", hour=8), _entry("gehen", hour=15)]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings())
    assert result.gross_hours == 7.0
    assert result.auto_break_hours == 0.5
    assert result.net_hours == 6.5


def test_auto_break_above_the_second_threshold(employee):
    entries = [_entry("kommen", hour=6), _entry("gehen", hour=16)]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings())
    assert result.gross_hours == 10.0
    assert result.auto_break_hours == 0.75
    assert result.net_hours == 9.25


def test_auto_break_is_switched_off(employee):
    entries = [_entry("kommen", hour=6), _entry("gehen", hour=16)]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings(enabled=False))
    assert result.auto_break_hours == 0.0
    assert result.net_hours == 10.0


def test_auto_break_can_be_switched_off_per_employee(employee):
    employee.auto_break_enabled = False
    entries = [_entry("kommen", hour=6), _entry("gehen", hour=16)]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings())
    assert result.auto_break_hours == 0.0


def test_auto_break_counts_a_missing_break_only(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("pause_start", hour=11),
        _entry("pause_ende", hour=11, minute=15),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings(only_missing=True))
    assert result.manual_break_hours == 0.25
    assert result.auto_break_hours == 0.25
    assert result.net_hours == 7.5


def test_auto_break_deducts_the_full_amount_when_a_break_is_present(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("pause_start", hour=11),
        _entry("pause_ende", hour=11, minute=15),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings(only_missing=False))
    assert result.auto_break_hours == 0.5
    assert result.net_hours == 7.25


def test_a_longer_manual_break_replaces_the_auto_break(employee):
    entries = [
        _entry("kommen", hour=8),
        _entry("pause_start", hour=11),
        _entry("pause_ende", hour=12),
        _entry("gehen", hour=16),
    ]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings(only_missing=True))
    assert result.manual_break_hours == 1.0
    assert result.auto_break_hours == 0.0
    assert result.net_hours == 7.0


def test_the_auto_break_uses_the_configured_minutes(employee):
    entries = [_entry("kommen", hour=8), _entry("gehen", hour=15)]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings(deduct_1=45.0))
    assert result.auto_break_hours == 0.75


def test_an_employee_without_the_flag_gets_the_auto_break(employee):
    """Fehlt das Flag, gilt die automatische Pause."""
    employee.auto_break_enabled = None
    entries = [_entry("kommen", hour=8), _entry("gehen", hour=15)]
    result = calculate_day(employee, entries, MONDAY, _auto_break_settings())
    assert result.auto_break_hours == 0.5


# --- Einstellungen ---------------------------------------------------------

def test_get_break_settings_returns_the_defaults(db):
    settings = get_break_settings(db)
    assert settings["enabled"] is False
    assert settings["threshold_1_hours"] == 6.0
    assert settings["deduct_1_minutes"] == 30.0
    assert settings["threshold_2_hours"] == 9.0
    assert settings["deduct_2_minutes"] == 45.0
    assert settings["only_missing_break"] is True


def test_get_break_settings_reads_stored_values(db):
    db.add(Setting(id=1, key="auto_break_enabled", value="1"))
    db.add(Setting(id=2, key="auto_break_threshold_1_hours", value="7"))
    db.add(Setting(id=3, key="auto_break_deduct_1_minutes", value="20"))
    db.commit()
    settings = get_break_settings(db)
    assert settings["enabled"] is True
    assert settings["threshold_1_hours"] == 7.0
    assert settings["deduct_1_minutes"] == 20.0
