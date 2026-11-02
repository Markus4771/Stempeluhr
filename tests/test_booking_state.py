"""Regressionstests fuer den Buchungs-Zustandsautomaten.

Diese Logik entscheidet, ob eine Buchung zulaessig ist und welchen
Zustand ein Mitarbeiter hat. Ein Fehler hier fuehrt zu falsch berechneten
Arbeitszeiten. Die Tests decken die reine Zustandslogik sowie die
Datenbankabfragen ab.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Muss vor dem Import von app.models gesetzt sein, sonst versucht app.database
# eine PostgreSQL-Verbindung aufzubauen.
os.environ.setdefault("DATABASE_TYPE", "sqlite")

from app.models import Base, Employee, Role, TimeEntry  # noqa: E402
from app.services.booking_state import (  # noqa: E402
    STATE_ABSENT,
    STATE_PAUSE,
    STATE_PRESENT,
    allowed_next_entries,
    day_bounds,
    determine_auto_entry_type,
    entries_for_day,
    explain_next_action,
    get_booking_state,
    is_valid_entry_type,
    is_valid_transition_for_employee,
    latest_entry,
    normalize_entry_type,
    transition_state,
)

DAY = date(2026, 10, 15)


@pytest.fixture()
def db(tmp_path):
    """Eigene SQLite-Datenbank je Test, damit die Tests unabhaengig sind."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'booking.db'}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    queries: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def _count(conn, cursor, statement, params, context, executemany):
        queries.append(statement)

    session.add(Role(id=1, name="Administrator"))
    session.add(
        Employee(
            id=1,
            employee_number="A1",
            first_name="Max",
            last_name="Muster",
            is_admin=False,
        )
    )
    session.add(
        Employee(
            id=2,
            employee_number="A2",
            first_name="Erika",
            last_name="Musterfrau",
            is_admin=False,
        )
    )
    session.commit()

    yield session, queries

    session.close()
    engine.dispose()


def _entry(session, employee_id, entry_type, hour=8, minute=0, deleted=False):
    """Legt eine Buchung an."""
    entry = TimeEntry(
        employee_id=employee_id,
        timestamp=datetime(DAY.year, DAY.month, DAY.day, hour, minute),
        entry_type=entry_type,
        method="test",
        deleted=deleted,
    )
    session.add(entry)
    session.commit()
    return entry


# --- normalize_entry_type / is_valid_entry_type ---


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("kommen", "kommen"),
        ("KOMMEN", "kommen"),
        ("kommend", "kommen"),
        ("  kommen  ", "kommen"),
        ("check-in", "kommen"),
        ("check in", "kommen"),
        ("checkin", "kommen"),
        ("check_in", "kommen"),
        ("gehen", "gehen"),
        ("out", "gehen"),
        ("check_out", "gehen"),
        ("pause", "pause_start"),
        ("Pause-Start", "pause_start"),
        ("pause start", "pause_start"),
        ("pauseende", "pause_ende"),
        ("pause end", "pause_ende"),
        ("unbekannt", "unbekannt"),
        ("", ""),
    ],
)
def test_normalize_entry_type(raw, expected):
    assert normalize_entry_type(raw) == expected


def test_normalize_entry_type_none_is_handled():
    """None wird nicht geworfen, sondern ergibt einen leeren Wert."""
    assert normalize_entry_type(None) == ""


@pytest.mark.parametrize(
    "raw",
    ["kommen", "gehen", "pause_start", "pause_ende", "KOMMEN", "out", "pause"],
)
def test_is_valid_entry_type_accepts_known(raw):
    assert is_valid_entry_type(raw) is True


@pytest.mark.parametrize("raw", ["unbekannt", "", "pause_mitte", "kom"])
def test_is_valid_entry_type_rejects_unknown(raw):
    assert is_valid_entry_type(raw) is False


# --- transition_state ---


@pytest.mark.parametrize(
    "state,entry_type,expected",
    [
        (STATE_ABSENT, "kommen", STATE_PRESENT),
        (STATE_ABSENT, "gehen", None),
        (STATE_ABSENT, "pause_start", None),
        (STATE_ABSENT, "pause_ende", None),
        (STATE_PRESENT, "gehen", STATE_ABSENT),
        (STATE_PRESENT, "pause_start", STATE_PAUSE),
        (STATE_PRESENT, "pause_ende", None),
        (STATE_PRESENT, "kommen", None),
        (STATE_PAUSE, "pause_ende", STATE_PRESENT),
        (STATE_PAUSE, "gehen", None),
        (STATE_PAUSE, "kommen", None),
    ],
)
def test_transition_state(state, entry_type, expected):
    assert transition_state(state, entry_type) == expected


def test_transition_state_accepts_aliases():
    """Aliase fuehren zum selben Ergebnis wie der kanonische Typ."""
    assert transition_state(STATE_ABSENT, "checkin") == STATE_PRESENT
    assert transition_state(STATE_PRESENT, "out") == STATE_ABSENT
    assert transition_state(STATE_PRESENT, "pause") == STATE_PAUSE
    assert transition_state(STATE_PAUSE, "pauseende") == STATE_PRESENT


def test_transition_state_unknown_state_returns_none():
    """Ein unbekannter Zustand fuehrt zu keiner Transition."""
    assert transition_state("quatsch", "kommen") is None


# --- allowed_next_entries ---


def test_allowed_next_entries_per_state():
    assert allowed_next_entries(STATE_ABSENT) == {"kommen"}
    assert allowed_next_entries(STATE_PRESENT) == {"gehen", "pause_start"}
    assert allowed_next_entries(STATE_PAUSE) == {"pause_ende"}


def test_allowed_next_entries_unknown_state_falls_back():
    assert allowed_next_entries("quatsch") == {"kommen"}


# --- day_bounds ---


def test_day_bounds_covers_whole_day():
    start, end = day_bounds(DAY)
    assert start == datetime(2026, 10, 15, 0, 0, 0)
    assert end == datetime(2026, 10, 16, 0, 0, 0)
    assert (end - start) == pytest.approx(1.0) or (end - start).total_seconds() == 86400


def test_day_bounds_defaults_to_today():
    start, end = day_bounds(None)
    assert start.date() == date.today()
    assert end.date() == date.today() + __import__("datetime").timedelta(days=1)


# --- entries_for_day ---


def test_entries_for_day_returns_only_that_day(db):
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    _entry(session, 1, "gehen", hour=16)

    yesterday = TimeEntry(
        employee_id=1,
        timestamp=datetime(2026, 10, 14, 8, 0),
        entry_type="kommen",
        method="test",
    )
    session.add(yesterday)
    session.commit()

    entries = entries_for_day(session, 1, DAY)
    assert len(entries) == 2
    assert [e.entry_type for e in entries] == ["kommen", "gehen"]


def test_entries_for_day_orders_by_timestamp_then_id(db):
    """Gleiche Zeitmarke wird nach Id aufgeloest.

    Die Ids werden in Einfuegereihenfolge vergeben. Damit die Regel
    sichtbar wird, wird zuerst eine spaetere Buchung gespeichert: Sie
    muss trotzdem hinten stehen, weil ihre Id groesser ist.
    """
    session, _ = db
    first = TimeEntry(
        employee_id=1,
        timestamp=datetime(2026, 10, 15, 8, 0),
        entry_type="gehen",
        method="test",
    )
    session.add(first)
    session.commit()
    second = TimeEntry(
        employee_id=1,
        timestamp=datetime(2026, 10, 15, 8, 0),
        entry_type="kommen",
        method="test",
    )
    session.add(second)
    session.commit()

    assert first.id < second.id
    entries = entries_for_day(session, 1, DAY)
    assert [e.id for e in entries] == [first.id, second.id]


def test_entries_for_day_uses_id_as_tiebreaker(db):
    """Die echte Abfrage sortiert bei gleicher Zeitmarke nach Id.

    SQLite liefert ueber den Index ohnehin in Id-Reihenfolge. PostgreSQL
    ist sich bei gleichem Zeitstempel dagegen nicht sicher und sortiert
    ohne die zweite Angabe in beliebiger Reihenfolge. Deshalb wird das
    tatsaechlich ausgefuehrte SQL der Produktionsfunktion geprueft.
    """
    session, queries = db
    _entry(session, 1, "kommen", hour=8)
    queries.clear()
    entries_for_day(session, 1, DAY)

    assert queries, "Es wurde keine Abfrage ausgefuehrt"
    sql = " ".join(queries[-1].split()).lower()
    assert "order by" in sql
    assert "timestamp asc" in sql
    assert re.search(r"id\s+asc", sql), f"Id fehlt als zweite Sortierangabe: {sql}"


def test_entries_for_day_excludes_deleted(db):
    """Geloeschte Buchungen werden nicht beruecksichtigt."""
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    _entry(session, 1, "gehen", hour=16, deleted=True)

    entries = entries_for_day(session, 1, DAY)
    assert len(entries) == 1
    assert entries[0].entry_type == "kommen"


def test_entries_for_day_is_scoped_to_employee(db):
    """Buchungen eines anderen Mitarbeiters werden nicht geliefert."""
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    _entry(session, 2, "kommen", hour=9)

    entries = entries_for_day(session, 1, DAY)
    assert len(entries) == 1
    assert entries[0].employee_id == 1


# --- latest_entry ---


def test_latest_entry_returns_newest(db):
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    _entry(session, 1, "gehen", hour=16)

    latest = latest_entry(session, 1)
    assert latest is not None
    assert latest.entry_type == "gehen"


def test_latest_entry_without_entries_is_none(db):
    session, _ = db
    assert latest_entry(session, 1) is None


def test_latest_entry_ignores_deleted(db):
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    _entry(session, 1, "gehen", hour=16, deleted=True)

    latest = latest_entry(session, 1)
    assert latest is not None
    assert latest.entry_type == "kommen"


# --- get_booking_state ---


def test_booking_state_without_entries_is_absent(db):
    session, _ = db
    state = get_booking_state(session, 1, DAY)
    assert state.state == STATE_ABSENT
    assert state.last_entry is None
    assert state.last_valid_entry is None
    assert state.invalid_entries == 0
    assert state.next_auto_entry_type == "kommen"


def test_booking_state_after_coming_is_present(db):
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    state = get_booking_state(session, 1, DAY)
    assert state.state == STATE_PRESENT
    assert state.next_auto_entry_type == "gehen"


def test_booking_state_after_pause_is_pause(db):
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    _entry(session, 1, "pause_start", hour=12)
    state = get_booking_state(session, 1, DAY)
    assert state.state == STATE_PAUSE
    assert state.next_auto_entry_type == "pause_ende"


def test_booking_state_full_day_cycle(db):
    """kommen -> pause -> coming back -> gehen ergibt abwesend."""
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    _entry(session, 1, "pause_start", hour=12)
    _entry(session, 1, "pause_ende", hour=13)
    _entry(session, 1, "gehen", hour=16)
    state = get_booking_state(session, 1, DAY)
    assert state.state == STATE_ABSENT
    assert state.invalid_entries == 0


def test_booking_state_counts_invalid_entries(db):
    """Unzulaessige Buchungen werden gezaehlt und ignorieren den Zustand."""
    session, _ = db
    _entry(session, 1, "gehen", hour=8)
    _entry(session, 1, "kommen", hour=9)
    state = get_booking_state(session, 1, DAY)
    assert state.state == STATE_PRESENT
    assert state.invalid_entries == 1
    # Die letzte gueltige Buchung ist "kommen", nicht das ungueltige "gehen".
    assert state.last_valid_entry is not None
    assert state.last_valid_entry.entry_type == "kommen"


def test_booking_state_last_entry_is_last_raw_entry(db):
    """last_entry zeigt die letzte Buchung, auch wenn sie ungueltig war."""
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    _entry(session, 1, "gehen", hour=16)
    _entry(session, 1, "kommen", hour=17)
    state = get_booking_state(session, 1, DAY)
    assert state.last_entry is not None
    assert state.last_entry.entry_type == "kommen"


def test_booking_state_ignores_deleted_entries(db):
    """Geloeschte Buchungen veraendern den Zustand nicht."""
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    _entry(session, 1, "gehen", hour=16, deleted=True)
    state = get_booking_state(session, 1, DAY)
    assert state.state == STATE_PRESENT


def test_booking_state_ignores_other_days(db):
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    other_day = TimeEntry(
        employee_id=1,
        timestamp=datetime(2026, 10, 16, 8, 0),
        entry_type="gehen",
        method="test",
    )
    session.add(other_day)
    session.commit()
    state = get_booking_state(session, 1, DAY)
    assert state.state == STATE_PRESENT


def test_booking_state_next_auto_entry_type_matches_state(db):
    session, _ = db
    assert get_booking_state(session, 1, DAY).next_auto_entry_type == "kommen"
    _entry(session, 1, "kommen", hour=8)
    assert get_booking_state(session, 1, DAY).next_auto_entry_type == "gehen"
    _entry(session, 1, "pause_start", hour=12)
    assert get_booking_state(session, 1, DAY).next_auto_entry_type == "pause_ende"


# --- determine_auto_entry_type ---


def test_determine_auto_entry_type(db):
    session, _ = db
    assert determine_auto_entry_type(session, 1, DAY) == "kommen"
    _entry(session, 1, "kommen", hour=8)
    assert determine_auto_entry_type(session, 1, DAY) == "gehen"


# --- is_valid_transition_for_employee ---


def test_is_valid_transition_for_employee(db):
    session, _ = db
    assert is_valid_transition_for_employee(session, 1, "kommen", DAY) is True
    assert is_valid_transition_for_employee(session, 1, "gehen", DAY) is False

    _entry(session, 1, "kommen", hour=8)
    assert is_valid_transition_for_employee(session, 1, "gehen", DAY) is True
    assert is_valid_transition_for_employee(session, 1, "pause_start", DAY) is True
    assert is_valid_transition_for_employee(session, 1, "kommen", DAY) is False


def test_is_valid_transition_accepts_aliases(db):
    session, _ = db
    assert is_valid_transition_for_employee(session, 1, "checkin", DAY) is True
    _entry(session, 1, "kommen", hour=8)
    assert is_valid_transition_for_employee(session, 1, "out", DAY) is True


def test_is_valid_transition_is_per_employee(db):
    """Der Zustand eines Mitarbeiters gilt nicht fuer einen anderen."""
    session, _ = db
    _entry(session, 1, "kommen", hour=8)
    assert is_valid_transition_for_employee(session, 2, "kommen", DAY) is True
    assert is_valid_transition_for_employee(session, 2, "gehen", DAY) is False


# --- explain_next_action ---


def test_explain_next_action_without_entries(db):
    session, _ = db
    result = explain_next_action(session, 1, DAY)
    assert result["state"] == STATE_ABSENT
    assert result["next_entry_type"] == "kommen"
    assert result["last_entry_type"] is None
    assert result["last_entry_time"] is None
    assert result["invalid_entries"] == 0


def test_explain_next_action_with_entries(db):
    session, _ = db
    _entry(session, 1, "kommen", hour=8, minute=5)
    result = explain_next_action(session, 1, DAY)
    assert result["state"] == STATE_PRESENT
    assert result["next_entry_type"] == "gehen"
    assert result["last_entry_type"] == "kommen"
    assert result["last_entry_time"] == "2026-10-15T08:05:00"
    assert result["invalid_entries"] == 0


def test_explain_next_action_reports_invalid_entries(db):
    session, _ = db
    _entry(session, 1, "gehen", hour=8)
    result = explain_next_action(session, 1, DAY)
    assert result["invalid_entries"] == 1
    assert result["last_entry_type"] == "gehen"


def test_explain_next_action_normalizes_last_entry_type(db):
    """Ein Alias in der Datenbank wird auf den kanonischen Wert gebracht."""
    session, _ = db
    _entry(session, 1, "checkin", hour=8)
    result = explain_next_action(session, 1, DAY)
    assert result["last_entry_type"] == "kommen"


# --- Datenbankzugriffe ---


def test_get_booking_state_uses_few_queries(db):
    """Die Zustandsermittlung braucht wenige Abfragen, keine je Buchung."""
    session, queries = db
    for hour in (8, 12, 13, 16):
        _entry(session, 1, "kommen", hour=hour)

    queries.clear()
    get_booking_state(session, 1, DAY)

    assert len(queries) <= 2, f"Unerwartet viele Abfragen: {len(queries)}"


def test_entries_for_day_uses_one_query(db):
    session, queries = db
    _entry(session, 1, "kommen", hour=8)
    queries.clear()
    entries_for_day(session, 1, DAY)
    assert len(queries) == 1
