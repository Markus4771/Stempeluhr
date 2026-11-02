"""Prüft, dass keine Route doppelt registriert ist.

FastAPI registriert bei doppelten Routen nur den ersten Handler und warnt
mit "Duplicate Operation ID". Der spätere Handler ist toter Code. Dieser
Test macht die Duplikate sichtbar, damit sie beim Bauen auffallen.

Der Test schlägt fehl, wenn neue Duplikate hinzukommen. Bereits bekannte
Duplikate sind in KNOWN_DUPLICATES aufgeführt und werden nur gemeldet.
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Muss vor dem Import der Anwendung gesetzt sein, sonst versucht
# app.database eine PostgreSQL-Verbindung aufzubauen.
os.environ.setdefault("DATABASE_TYPE", "sqlite")


# Bereits bekannte Duplikate. Siehe docs/OPTIMIERUNG.md, Abschnitt 2.1.
#
# Welche Variante gewollt ist, muss fachlich entschieden werden:
#   - delete_role: roles.py nutzt require_system_admin_response und leitet
#     mit Meldung um, roles_rights.py wirft HTTPException.
#   - absence_calendar_feed_write_disabled: dreifach in vacation.py.
KNOWN_DUPLICATES = {
    "absence_calendar_feed_write_disabled_calendar__calendar_slug__ics_post",
    "absence_calendar_feed_write_disabled_calendar__calendar_slug__ics_put",
    "absence_calendar_feed_write_disabled_calendar__calendar_slug__ics_patch",
    "absence_calendar_feed_write_disabled_calendar__calendar_slug__ics_delete",
    "delete_role_system_settings_roles__role_id__delete_post",
}

# Alle Pfad+Methoden-Kombinationen, für die mehrere Handler registriert sind.
# FastAPI nimmt nur den ersten Handler; der zweite ist toter Code.
# Der jeweils zuerst genannte Handler ist der erreichbare.
KNOWN_ROUTE_CONFLICTS = {
    # dashboard_privacy.py:privacy_dashboard_home vs dashboard.py:index
    ("/", "GET"),
    # dashboard_privacy.py:privacy_dashboard_alias vs dashboard.py:dashboard
    ("/dashboard", "GET"),
    # dashboard_metrics_corrected.py:corrected_dashboard_metrics
    #   vs dashboard_metrics.py:dashboard_metrics
    ("/api/dashboard/metrics", "GET"),
    # dashboard_self_booking_extended.py:dashboard_self_book_extended
    #   vs dashboard_self_booking.py:dashboard_self_book
    ("/dashboard/self-book", "POST"),
    # security_login.py:secure_login_form vs dashboard.py:login_form
    ("/login", "GET"),
    # security_login.py:secure_login_submit vs dashboard.py:login_submit
    ("/login", "POST"),
    # security_login.py:secure_onboarding_submit
    #   vs onboarding.py:onboarding_accept_submit
    ("/onboarding/{token}", "POST"),
    # security_login.py:secure_password_reset_form
    #   vs dashboard.py:password_reset_form
    ("/password-reset/{token}", "GET"),
    # security_login.py:secure_password_reset_submit
    #   vs dashboard.py:password_reset_submit
    ("/password-reset/{token}", "POST"),
    # vacation.py:system_caldav_settings vs caldav_accounts.py:caldav_accounts_page
    ("/system/settings/caldav", "GET"),
    # roles.py:roles_settings vs roles_rights.py:roles_rights_page
    ("/system/settings/roles", "GET"),
    # roles.py:delete_role vs roles_rights.py:delete_role
    ("/system/settings/roles/{role_id}/delete", "POST"),
}


@pytest.fixture(scope="module")
def duplicate_operation_ids():
    """Sammelt die doppelt vergebenen Operation-IDs der Anwendung."""
    import tempfile

    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    import app.database as database

    tmp_dir = tempfile.mkdtemp()
    engine = create_engine(
        f"sqlite:///{Path(tmp_dir) / 'routes.db'}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    original_engine = database.engine
    database.engine.dispose()
    database.engine = engine
    database.SessionLocal.configure(bind=engine)

    try:
        import app.db_migrations as migrations

        migrations.engine = engine
        from app.main import app

        # Das OpenAPI-Schema cachen, sonst entstehen keine Warnungen.
        app.openapi_schema = None
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            app.openapi()

        found: set[str] = set()
        for warning in caught:
            message = str(warning.message)
            if "Duplicate Operation ID" not in message:
                continue
            operation_id = message.split("Duplicate Operation ID ")[1]
            operation_id = operation_id.split(" for function")[0].strip()
            found.add(operation_id)
        return found
    finally:
        database.engine.dispose()
        database.engine = original_engine


def _iter_routes(routes):
    """Liefert alle Routen rekursiv.

    Neuere FastAPI-Versionen legen eingebundene Router als ``_IncludedRouter``
    ab. Ohne das Aufklappen werden die eigentlichen Routen nicht gefunden.
    """
    for route in routes:
        original = getattr(route, "original_router", None)
        if original is not None:
            yield from _iter_routes(original.routes)
        else:
            yield route


@pytest.fixture(scope="module")
def duplicate_route_conflicts():
    """Findet alle Routen, für die mehrere Handler registriert sind.

    FastAPI warnt nur, wenn auch der Funktionsname übereinstimmt. Zwei
    verschiedene Funktionen auf demselben Pfad erzeugen keine Warnung,
    der zweite Handler ist aber trotzdem toter Code. Diese Prüfung deckt
    beide Fälle ab.
    """
    import tempfile

    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    import app.database as database

    tmp_dir = tempfile.mkdtemp()
    engine = create_engine(
        f"sqlite:///{Path(tmp_dir) / 'routes.db'}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    original_engine = database.engine
    database.engine.dispose()
    database.engine = engine
    database.SessionLocal.configure(bind=engine)

    try:
        import app.db_migrations as migrations

        migrations.engine = engine
        from app.main import app

        registered: dict[tuple[str, str], list[str]] = {}
        for route in _iter_routes(app.routes):
            methods = getattr(route, "methods", None)
            endpoint = getattr(route, "endpoint", None)
            if not methods or endpoint is None:
                continue
            source = endpoint.__code__.co_filename.split("/app/")[-1]
            label = f"{source}:{endpoint.__name__}"
            for method in methods:
                if method in ("HEAD", "OPTIONS"):
                    continue
                registered.setdefault((route.path, method), []).append(label)

        return {
            key: handlers
            for key, handlers in registered.items()
            if len(handlers) > 1
        }
    finally:
        database.engine.dispose()
        database.engine = original_engine


def test_no_new_duplicate_routes(duplicate_operation_ids):
    """Keine neuen doppelten Routen gegenüber dem bekannten Stand."""
    new_duplicates = set(duplicate_operation_ids) - KNOWN_DUPLICATES
    assert not new_duplicates, (
        "Neue doppelt registrierte Routen gefunden: "
        + ", ".join(sorted(new_duplicates))
        + ". FastAPI nutzt nur den ersten Handler."
    )


def test_known_duplicates_are_still_detected(duplicate_operation_ids):
    """Der Test erkennt die bekannten Duplikate überhaupt.

    Ohne diese Prüfung könnte der Test unauffällig grün bleiben, wenn
    FastAPI seine Warnung nicht mehr ausgibt.
    """
    assert KNOWN_DUPLICATES & set(duplicate_operation_ids), (
        "Keine der bekannten doppelten Routen wurde erkannt. "
        "Der Test prüft womöglich nichts mehr."
    )


def test_no_new_route_conflicts(duplicate_route_conflicts):
    """Keine neuen Pfade, für die mehrere Handler registriert sind.

    Diese Prüfung ist strenger als der OpenAPI-Test: Sie erkennt auch
    Duplikate, bei denen sich die Funktionsnamen unterscheiden und FastAPI
    deshalb nicht warnt.
    """
    new_conflicts = set(duplicate_route_conflicts) - KNOWN_ROUTE_CONFLICTS
    assert not new_conflicts, (
        "Neue mehrfach registrierte Routen gefunden: "
        + ", ".join(f"{method} {path}" for path, method in sorted(new_conflicts))
        + ". FastAPI nutzt nur den ersten Handler."
    )


def test_known_route_conflicts_are_still_detected(duplicate_route_conflicts):
    """Die bekannten Konflikte werden erkannt.

    Ohne diese Prüfung wäre der Test wirkungslos, falls die Erkennung
    kaputtgeht.
    """
    detected = set(duplicate_route_conflicts)
    assert KNOWN_ROUTE_CONFLICTS <= detected, (
        "Bekannte Konflikte fehlen in der Erkennung: "
        + ", ".join(
            f"{method} {path}"
            for path, method in sorted(KNOWN_ROUTE_CONFLICTS - detected)
        )
    )
