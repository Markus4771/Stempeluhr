"""Tests fuer die Performance-Indizes der Stempeluhr.

Geprueft wird nicht nur, dass die Indizes im Modell definiert sind, sondern
dass der Datenbank-Planer sie tatsaechlich verwendet. Ohne den Index
erklaert SQLite den Zugriff als "SCAN time_entries" (vollstaendiger
Tabellenscan), mit Index als "SEARCH ... USING INDEX".
"""
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# app.database legt beim Import die Engine an. Ohne diese Variable waere
# psycopg2 noetig, obwohl der Test ausschliesslich SQLite verwendet.
import os  # noqa: E402

os.environ.setdefault("DATABASE_TYPE", "sqlite")

from app.models import Base, TimeEntry  # noqa: E402

# Erwartete Indizes aus Migration 013 "performance_indexes".
EXPECTED_INDEXES = {
    "time_entries": "ix_time_entries_employee_id_timestamp",
    "audit_logs": "ix_audit_logs_created_at",
}


@pytest.fixture()
def db_engine(tmp_path):
    """Frische SQLite-Datenbank mit dem aktuellen Schema.

    NullPool sorgt dafuer, dass jede Verbindung neu aufgebaut wird. SQLite
    cached den Ausfuehrungsplan pro Verbindung - ohne NullPool wuerde der
    Plan eines vorherigen Testlaufs weiterverwendet.
    """
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def seeded_engine(db_engine):
    """Datenbank mit Mitarbeitern und Buchungen über mehrere Tage."""
    with db_engine.begin() as conn:
        conn.execute(text("INSERT INTO roles (id, name) VALUES (1, 'Administrator')"))
        for i in range(1, 4):
            conn.execute(
                text(
                    "INSERT INTO employees (id, employee_number, first_name, last_name, role_id, active) "
                    "VALUES (:id, :num, 'Max', 'Muster', 1, 1)"
                ),
                {"id": i, "num": f"E{i:03d}"},
            )
        for i in range(1, 4):
            for day in range(1, 21):
                for hour in (8, 12, 13, 16):
                    conn.execute(
                        text(
                            "INSERT INTO time_entries (employee_id, timestamp, entry_type, method, deleted) "
                            "VALUES (:emp, :ts, 'kommen', 'web', 0)"
                        ),
                        {"emp": i, "ts": f"2026-10-{day:02d} {hour:02d}:00:00"},
                    )
    return db_engine


def _index_names(engine, table: str) -> set[str]:
    inspector = inspect(engine)
    return {idx["name"] for idx in inspector.get_indexes(table)}


@pytest.mark.parametrize("table,index_name", sorted(EXPECTED_INDEXES.items()))
def test_performance_index_is_created(db_engine, table, index_name):
    """Der Index muss im Schema vorhanden sein (frische Installation)."""
    assert index_name in _index_names(db_engine, table)


def test_time_entry_model_declares_composite_index():
    """Das Modell muss den zusammengesetzten Index deklarieren."""
    indexes = {index.name: tuple(column.name for column in index.columns)
               for index in TimeEntry.__table__.indexes}
    assert "ix_time_entries_employee_id_timestamp" in indexes
    assert indexes["ix_time_entries_employee_id_timestamp"] == ("employee_id", "timestamp")


def test_query_plan_uses_index_instead_of_full_scan(seeded_engine):
    """Der Planer muss den Index nutzen statt der Tabelle zu scannen."""
    sql = (
        "SELECT * FROM time_entries "
        "WHERE employee_id = 1 AND timestamp >= '2026-10-01' AND timestamp < '2026-11-01'"
    )
    with seeded_engine.connect() as conn:
        plan = " ".join(str(row[-1]) for row in conn.execute(text(f"EXPLAIN QUERY PLAN {sql}")))
    assert "SCAN time_entries" not in plan, f"Tabellenscan trotz Index: {plan}"
    assert "ix_time_entries_employee_id_timestamp" in plan, f"Index nicht verwendet: {plan}"


def test_query_plan_changes_from_scan_to_index_search(seeded_engine):
    """Gegenprobe: ohne Index scannt der Planer, mit Index sucht er.

    SQLite cached den Ausfuehrungsplan pro Verbindung. Deshalb werden fuer
    die Gegenprobe zwei getrennte Verbindungen verwendet.
    """
    sql = (
        "SELECT * FROM time_entries "
        "WHERE employee_id = 1 AND timestamp >= '2026-10-01' AND timestamp < '2026-11-01'"
    )

    def plan_for(connection) -> str:
        return " ".join(str(row[-1]) for row in connection.execute(text(f"EXPLAIN QUERY PLAN {sql}")))

    with seeded_engine.connect() as conn:
        with_index = plan_for(conn)

    with seeded_engine.connect() as conn:
        conn.execute(text("DROP INDEX ix_time_entries_employee_id_timestamp"))
        conn.commit()
        without_index = plan_for(conn)

    assert "SCAN time_entries" in without_index, f"Erwarteter Tabellenscan fehlt: {without_index}"
    assert "ix_time_entries_employee_id_timestamp" in with_index, f"Index nicht verwendet: {with_index}"


def test_migration_013_is_registered():
    """Die Migration muss in der Migrationsliste stehen."""
    from app.db_migrations import MIGRATIONS

    versions = {migration.version for migration in MIGRATIONS}
    assert "013" in versions

    migration = next(m for m in MIGRATIONS if m.version == "013")
    assert migration.name == "performance_indexes"


def test_migration_013_creates_indexes_on_existing_schema(db_engine):
    """Die Migration muss Indizes auch in bestehenden Installationen anlegen."""
    from app.db_migrations import _m013_performance_indexes

    with db_engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS ix_time_entries_employee_id_timestamp"))
        conn.execute(text("DROP INDEX IF EXISTS ix_audit_logs_created_at"))
        _m013_performance_indexes(conn, "sqlite")

    inspector = inspect(db_engine)
    assert "ix_time_entries_employee_id_timestamp" in {i["name"] for i in inspector.get_indexes("time_entries")}
    assert "ix_audit_logs_created_at" in {i["name"] for i in inspector.get_indexes("audit_logs")}


def test_migration_013_is_idempotent(db_engine):
    """Mehrfaches Ausfuehren der Migration darf nicht fehlschlagen."""
    from app.db_migrations import _m013_performance_indexes

    with db_engine.begin() as conn:
        _m013_performance_indexes(conn, "sqlite")
        _m013_performance_indexes(conn, "sqlite")
