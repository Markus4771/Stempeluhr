"""Zentrale Status- und Berechnungsautomatik für Abwesenheiten.

Seit 5.6.33 wird die Anzahl der Urlaubstage bei jedem Speichern serverseitig
neu berechnet. Grundlage sind Montag bis Freitag. Samstage, Sonntage und aktive
Feiertage werden nicht als volle Urlaubstage abgezogen; halbe Feiertage zählen
mit 0,5 Tagen.
"""

from datetime import datetime

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models import AbsenceType, VacationRequest
from app.services.vacation_management import (
    VACATION_REQUEST_TYPES,
    book_approved_request,
    calculate_request_days,
    ensure_request_extension,
    reverse_request,
)

_REGISTERED = False
_PENDING_KEY = "vacation_533_status_changes"


def _apply_absence_rules(session: Session) -> None:
    candidates = [
        obj
        for obj in session.new.union(session.dirty)
        if isinstance(obj, VacationRequest)
    ]
    if not candidates:
        return

    type_cache: dict[str, AbsenceType | None] = {}
    pending = session.info.setdefault(_PENDING_KEY, [])

    for request in candidates:
        # Die gespeicherte Tageszahl wird niemals mehr aus Kalendertagen
        # übernommen. Damit ist eine Woche verbindlich fünf Urlaubstage lang.
        if request.start_date and request.end_date:
            result = calculate_request_days(
                session,
                request.start_date,
                request.end_date,
                bool(request.half_day),
            )
            request.days = float(result.chargeable_days)
            ensure_request_extension(session, request, calculation_result=result)

        code = (request.request_type or "").strip()
        if code and code not in type_cache:
            with session.no_autoflush:
                type_cache[code] = (
                    session.query(AbsenceType)
                    .filter(AbsenceType.code == code)
                    .first()
                )
        absence_type = type_cache.get(code)

        # Genehmigungsfreie Arten, beispielsweise Krank, werden direkt wirksam.
        if absence_type is not None and not absence_type.requires_approval:
            if request.status in (None, "", "beantragt", "offen", "Offen"):
                request.status = "genehmigt"
                request.decided_at = request.decided_at or datetime.now()
                request.decision_comment = request.decision_comment or (
                    "Automatisch genehmigt: Für diese Abwesenheitsart ist keine Genehmigung erforderlich."
                )

        state = inspect(request)
        history = state.attrs.status.history
        old_status = history.deleted[0] if history.deleted else None
        new_status = request.status

        # Neue, direkt genehmigte Anträge besitzen vor dem Flush noch keine ID.
        # Die Kontobuchung wird deshalb nach dem Flush durchgeführt.
        if code in VACATION_REQUEST_TYPES:
            if new_status == "genehmigt" and old_status != "genehmigt":
                pending.append(("approve", request))
            elif old_status == "genehmigt" and new_status in {
                "storniert", "abgelehnt", "loeschung_genehmigt", "gelöscht"
            }:
                pending.append(("reverse", request))


def _apply_pending_account_entries(session: Session) -> None:
    pending = session.info.pop(_PENDING_KEY, [])
    if not pending:
        return

    actor = str(session.info.get("actor") or "SYSTEM")
    for action, request in pending:
        if action == "approve":
            book_approved_request(session, request, actor)
        else:
            reverse_request(
                session,
                request,
                actor,
                "vacation_reversed",
                "Genehmigter Urlaub wurde storniert, abgelehnt oder gelöscht.",
            )


def register_absence_approval_events() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    @event.listens_for(Session, "before_flush")
    def _before_flush(session: Session, flush_context, instances) -> None:
        _apply_absence_rules(session)

    @event.listens_for(Session, "after_flush_postexec")
    def _after_flush_postexec(session: Session, flush_context) -> None:
        _apply_pending_account_entries(session)

    _REGISTERED = True
