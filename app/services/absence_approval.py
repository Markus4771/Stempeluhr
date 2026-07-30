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
from app.services.vacation_management import VACATION_REQUEST_TYPES, calculate_request_days

_REGISTERED = False
_PENDING_KEY = "vacation_533_pending"
_COMMITTED_KEY = "vacation_533_committed"


def _append_pending(session: Session, action: str, request: VacationRequest, result=None) -> None:
    pending = session.info.setdefault(_PENDING_KEY, [])
    marker = (action, id(request))
    if any((item[0], id(item[1])) == marker for item in pending):
        return
    pending.append((action, request, result))


def _apply_absence_rules(session: Session) -> None:
    candidates = [obj for obj in session.new.union(session.dirty) if isinstance(obj, VacationRequest)]
    if not candidates:
        return

    type_cache: dict[str, AbsenceType | None] = {}
    for request in candidates:
        result = None
        if request.start_date and request.end_date:
            result = calculate_request_days(session, request.start_date, request.end_date, bool(request.half_day))
            request.days = float(result.chargeable_days)
            _append_pending(session, "extension", request, result)

        code = (request.request_type or "").strip()
        if code and code not in type_cache:
            with session.no_autoflush:
                type_cache[code] = session.query(AbsenceType).filter(AbsenceType.code == code).first()
        absence_type = type_cache.get(code)

        if absence_type is not None and not absence_type.requires_approval:
            if request.status in (None, "", "beantragt", "offen", "Offen"):
                request.status = "genehmigt"
                request.decided_at = request.decided_at or datetime.now()
                request.decision_comment = request.decision_comment or (
                    "Automatisch genehmigt: Für diese Abwesenheitsart ist keine Genehmigung erforderlich."
                )

        history = inspect(request).attrs.status.history
        old_status = history.deleted[0] if history.deleted else None
        new_status = request.status
        if code in VACATION_REQUEST_TYPES:
            if new_status == "genehmigt" and old_status != "genehmigt":
                _append_pending(session, "approve", request, result)
            elif old_status == "genehmigt" and new_status in {
                "storniert", "abgelehnt", "loeschung_genehmigt", "gelöscht"
            }:
                _append_pending(session, "reverse", request, result)


def _remember_flushed_requests(session: Session) -> None:
    pending = session.info.pop(_PENDING_KEY, [])
    if not pending:
        return
    committed = session.info.setdefault(_COMMITTED_KEY, [])
    actor = str(session.info.get("actor") or "SYSTEM")
    for action, request, result in pending:
        if not request.id:
            continue
        details = None
        if result is not None:
            details = {
                "chargeable_days": float(result.chargeable_days),
                "calendar_days": result.calendar_days,
                "weekend_days": result.weekend_days,
                "holiday_days": float(result.holiday_days),
                "reference_weekdays": 5,
            }
        item = (action, request.id, actor, details)
        if item not in committed:
            committed.append(item)


def _post_commit_entries(session: Session) -> None:
    committed = session.info.pop(_COMMITTED_KEY, [])
    if not committed:
        return

    from app.database import SessionLocal
    from app.models import VacationRequest
    from app.services.vacation_management import book_approved_request, ensure_request_extension, reverse_request

    db = SessionLocal()
    try:
        handled_extensions: set[int] = set()
        for action, request_id, actor, details in committed:
            row = db.query(VacationRequest).filter(VacationRequest.id == request_id).first()
            if not row:
                continue
            if request_id not in handled_extensions:
                ensure_request_extension(db, row)
                extension = ensure_request_extension(db, row)
                if details is not None:
                    import json
                    extension.calculation_details = json.dumps(details, ensure_ascii=False)
                handled_extensions.add(request_id)
            if action == "approve":
                book_approved_request(db, row, actor)
            elif action == "reverse":
                reverse_request(
                    db,
                    row,
                    actor,
                    "vacation_reversed",
                    "Genehmigter Urlaub wurde storniert, abgelehnt oder gelöscht.",
                )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def register_absence_approval_events() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    @event.listens_for(Session, "before_flush")
    def _before_flush(session: Session, flush_context, instances) -> None:
        _apply_absence_rules(session)

    @event.listens_for(Session, "after_flush_postexec")
    def _after_flush_postexec(session: Session, flush_context) -> None:
        _remember_flushed_requests(session)

    @event.listens_for(Session, "after_commit")
    def _after_commit(session: Session) -> None:
        _post_commit_entries(session)

    _REGISTERED = True
