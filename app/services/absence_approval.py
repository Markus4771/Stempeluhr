"""Statusautomatik für genehmigungsfreie Abwesenheitsarten.

Abwesenheitsarten mit ``requires_approval=False`` werden beim Anlegen oder
Bearbeiten unmittelbar als genehmigt gespeichert. Dadurch erscheinen etwa
Krankmeldungen nicht in der Genehmigungsliste.
"""

from datetime import datetime

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import AbsenceType, VacationRequest

_REGISTERED = False


def _apply_absence_approval_status(session: Session) -> None:
    candidates = [
        obj
        for obj in session.new.union(session.dirty)
        if isinstance(obj, VacationRequest)
    ]
    if not candidates:
        return

    type_cache: dict[str, AbsenceType | None] = {}
    for request in candidates:
        code = (request.request_type or "").strip()
        if not code:
            continue
        if code not in type_cache:
            type_cache[code] = (
                session.query(AbsenceType)
                .filter(AbsenceType.code == code)
                .first()
            )
        absence_type = type_cache[code]
        if absence_type is None or absence_type.requires_approval:
            continue

        # Genehmigungsfreie Arten, zum Beispiel „Krank“, werden direkt wirksam.
        # Stornierungen und Löschvorgänge dürfen dabei nicht überschrieben werden.
        if request.status in (None, "", "beantragt", "offen", "Offen"):
            request.status = "genehmigt"
            request.decided_at = request.decided_at or datetime.now()
            request.decision_comment = request.decision_comment or "Automatisch genehmigt: Für diese Abwesenheitsart ist keine Genehmigung erforderlich."


def register_absence_approval_events() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    @event.listens_for(Session, "before_flush")
    def _before_flush(session: Session, flush_context, instances) -> None:
        _apply_absence_approval_status(session)

    _REGISTERED = True
