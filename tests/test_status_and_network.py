"""Tests für die gebündelten Statusabfragen.

Deckt die Umstellung von `latest_employee_statuses` auf eine einzige
Datenbankabfrage ab sowie die Weitergabe der Einstellungen an die
Netzwerksicherheitsprüfung.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Muss vor dem Import von app.models gesetzt sein, sonst versucht app.database
# eine PostgreSQL-Verbindung aufzubauen.
os.environ.setdefault("DATABASE_TYPE", "sqlite")

from app.models import Base, Setting, TimeEntry  # noqa: E402
from app.routes.common import latest_employee_statuses  # noqa: E402
from app.services.network_security import access_allowed, https_should_redirect  # noqa: E402


class FakeRequest:
    """Minimaler Request-Ersatz für die Netzwerksicherheitsprüfung."""

    def __init__(self, path: str, scheme: str = "http", headers: dict | None = None):
        from starlette.datastructures import URL

        self.url = URL(f"{scheme}://testserver{path}")
        self.headers = headers or {}
        self.client = type("Client", (), {"host": "192.168.1.50"})()


@pytest.fixture
def db(tmp_path):
    """Eigene SQLite-Datenbank je Test, damit die Tests unabhaengig sind."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'status.db'}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(engine)

    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    queries: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def _count(conn, cursor, statement, params, context, executemany):
        queries.append(statement)

    session.queries = queries
    yield session
    session.close()
    engine.dispose()


def _entry(db, employee_id: int, timestamp: datetime, entry_type: str = "kommen") -> TimeEntry:
    entry = TimeEntry(
        employee_id=employee_id,
        timestamp=timestamp,
        entry_type=entry_type,
        method="web",
        deleted=False,
    )
    db.add(entry)
    return entry


def test_status_needs_one_query_for_many_employees(db):
    """Die Statusabfrage läuft mit einer Abfrage für alle Mitarbeiter."""
    for employee_id in range(1, 21):
        _entry(db, employee_id, datetime(2026, 10, 5, 8, 0))
    db.commit()
    db.queries.clear()

    result = latest_employee_statuses(db, list(range(1, 21)))

    assert len(result) == 20
    assert len(db.queries) == 1


def test_status_reports_the_latest_entry_per_employee(db):
    """Je Mitarbeiter zählt die letzte Buchung."""
    _entry(db, 1, datetime(2026, 10, 5, 8, 0), "kommen")
    _entry(db, 1, datetime(2026, 10, 5, 12, 0), "pause_start")
    _entry(db, 1, datetime(2026, 10, 5, 16, 0), "gehen")
    _entry(db, 2, datetime(2026, 10, 5, 8, 0), "kommen")
    db.commit()

    result = latest_employee_statuses(db, [1, 2])

    assert result[1]["entry_type"] == "gehen"
    assert result[1]["label"] == "Abwesend"
    assert result[1]["present"] is False
    assert result[2]["entry_type"] == "kommen"
    assert result[2]["present"] is True


def test_status_uses_the_newest_timestamp_not_the_highest_id(db):
    """Bei vertauschter Id- und Zeitmarkenfolge zählt die Zeitmarke.

    Die Id-Reihenfolge entspricht nicht der Reihenfolge der Anlage. Die
    Buchung mit der neuesten Zeitmarke muss gewinnen.
    """
    older = _entry(db, 1, datetime(2026, 10, 5, 8, 0), "gehen")
    newer = _entry(db, 1, datetime(2026, 10, 5, 9, 0), "kommen")
    db.flush()
    # Höhere Id, aber ältere Zeitmarke.
    older.id = 200
    newer.id = 100
    db.commit()

    result = latest_employee_statuses(db, [1])

    assert result[1]["entry_type"] == "kommen"


def test_status_breaks_ties_on_equal_timestamps_by_id(db):
    """Bei gleicher Zeitmarke gewinnt die höhere Id."""
    first = _entry(db, 1, datetime(2026, 10, 5, 8, 0), "kommen")
    second = _entry(db, 1, datetime(2026, 10, 5, 8, 0), "gehen")
    db.flush()
    first.id = 10
    second.id = 11
    db.commit()

    result = latest_employee_statuses(db, [1])

    assert result[1]["entry_type"] == "gehen"


def test_status_without_entries(db):
    """Mitarbeiter ohne Buchung bekommen den Status Keine Buchung."""
    db.commit()

    result = latest_employee_statuses(db, [1, 2])

    assert result[1] == {
        "label": "Keine Buchung",
        "entry_type": "",
        "timestamp": None,
        "present": False,
    }
    assert result[2]["label"] == "Keine Buchung"


def test_status_with_empty_employee_list(db):
    """Eine leere Liste liefert ein leeres Ergebnis ohne Abfrage."""
    db.commit()
    db.queries.clear()

    assert latest_employee_statuses(db, []) == {}
    assert db.queries == []


def test_status_keeps_deleted_entries_visible(db):
    """Gelöschte Buchungen werden weiterhin berücksichtigt.

    Die bisherige Abfrage filterte nicht auf gelöschte Buchungen. Das
    Verhalten bleibt erhalten.
    """
    entry = _entry(db, 1, datetime(2026, 10, 5, 8, 0), "kommen")
    entry.deleted = True
    db.commit()

    result = latest_employee_statuses(db, [1])

    assert result[1]["entry_type"] == "kommen"


def test_status_only_contains_requested_employees(db):
    """Es werden nur die angeforderten Mitarbeiter geliefert."""
    _entry(db, 1, datetime(2026, 10, 5, 8, 0))
    _entry(db, 2, datetime(2026, 10, 5, 8, 0))
    db.commit()

    result = latest_employee_statuses(db, [2])

    assert set(result) == {2}


def test_network_checks_use_the_given_settings(db):
    """Die übergebenen Einstellungen werden verwendet."""
    db.add(Setting(key="security_force_https", value="1"))
    db.add(Setting(key="security_network_filter_enabled", value="1"))
    db.add(Setting(key="security_allowed_networks", value="10.0.0.0/8"))
    db.commit()

    settings = {s.key: s.value for s in db.query(Setting).all()}
    request = FakeRequest("/api/v1/entries", headers={"x-forwarded-proto": "https"})

    assert https_should_redirect(request, db, settings) is False
    allowed, reason = access_allowed(request, db, settings)
    assert allowed is False
    assert "192.168.1.50" in reason


def test_network_checks_fall_back_to_the_database(db):
    """Ohne übergebene Einstellungen wird die Datenbank gelesen."""
    db.add(Setting(key="security_force_https", value="1"))
    db.commit()
    request = FakeRequest("/dashboard", headers={"x-forwarded-proto": "http"})

    assert https_should_redirect(request, db) is True


def test_network_checks_read_settings_once(db):
    """Beide Prüfungen zusammen lesen die Einstellungen nur einmal."""
    db.add(Setting(key="security_force_https", value="1"))
    db.add(Setting(key="security_network_filter_enabled", value="1"))
    db.add(Setting(key="security_allowed_networks", value="192.168.1.0/24"))
    db.commit()
    db.queries.clear()

    settings = {s.key: s.value for s in db.query(Setting).all()}
    request = FakeRequest("/api/v1/entries", headers={"x-forwarded-proto": "https"})
    https_should_redirect(request, db, settings)
    access_allowed(request, db, settings)

    assert len(db.queries) == 1
