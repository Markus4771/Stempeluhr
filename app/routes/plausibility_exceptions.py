from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models import AuditLog, PlausibilityIssue
from app.routes.common import report_visible_employee_ids, role_name

router = APIRouter(tags=["plausibility-exceptions"])


def ensure_plausibility_exception_schema(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS plausibility_exceptions (
            id SERIAL PRIMARY KEY,
            issue_id INTEGER,
            employee_id INTEGER NOT NULL,
            issue_date DATE NOT NULL,
            check_type VARCHAR(100) NOT NULL,
            reason TEXT NOT NULL,
            approved_by VARCHAR(100) NOT NULL,
            approved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            UNIQUE (employee_id, issue_date, check_type)
        )
    """))
    db.commit()


def _can_approve_exception(user) -> bool:
    if not user:
        return False
    if str(getattr(user, "employee_number", "") or "").strip().lower() == "admin":
        return True
    return role_name(user) in {"Administrator", "Personal", "Teamleiter"}


def _approve_issue(db: Session, issue: PlausibilityIssue, actor: str, reason: str, request: Request) -> None:
    now = datetime.now()
    db.execute(text("""
        INSERT INTO plausibility_exceptions
            (issue_id, employee_id, issue_date, check_type, reason, approved_by, approved_at, active)
        VALUES
            (:issue_id, :employee_id, :issue_date, :check_type, :reason, :approved_by, :approved_at, TRUE)
        ON CONFLICT (employee_id, issue_date, check_type)
        DO UPDATE SET
            issue_id = EXCLUDED.issue_id,
            reason = EXCLUDED.reason,
            approved_by = EXCLUDED.approved_by,
            approved_at = EXCLUDED.approved_at,
            active = TRUE
    """), {
        "issue_id": issue.id,
        "employee_id": issue.employee_id,
        "issue_date": issue.issue_date,
        "check_type": issue.check_type,
        "reason": reason,
        "approved_by": actor,
        "approved_at": now,
    })

    issue.status = "geprueft"
    issue.comment = f"Genehmigte Ausnahme: {reason}"
    issue.resolved_at = now
    issue.resolved_by = actor
    issue.updated_at = now

    db.add(AuditLog(
        actor=actor,
        action="plausibility_exception_approved",
        entity="plausibility",
        entity_id=str(issue.id),
        details=(
            f"Ausnahme genehmigt: Mitarbeiter {issue.employee_id}, "
            f"Datum {issue.issue_date.isoformat()}, Prüfart {issue.check_type}; Grund: {reason}"
        ),
        ip_address=request.client.host if request.client else None,
    ))


@router.post("/plausibility/{issue_id}/approve-exception")
def approve_plausibility_exception(
    issue_id: int,
    request: Request,
    reason: str = Form(...),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not _can_approve_exception(user):
        return RedirectResponse("/plausibility?status=offen&error=Keine+Berechtigung", status_code=303)

    issue = db.query(PlausibilityIssue).filter(PlausibilityIssue.id == issue_id).first()
    if not issue or issue.employee_id not in report_visible_employee_ids(db, user):
        return RedirectResponse("/plausibility?status=offen&error=Keine+Berechtigung", status_code=303)

    reason = (reason or "").strip()
    if len(reason) < 3:
        return RedirectResponse("/plausibility?status=offen&error=Bitte+eine+Begründung+angeben", status_code=303)
    if issue.check_type != "missing_workday" or issue.status != "offen":
        return RedirectResponse("/plausibility?status=offen&error=Dieser+Fall+kann+nicht+als+Arbeitstagsausnahme+genehmigt+werden", status_code=303)

    ensure_plausibility_exception_schema(db)
    actor = str(getattr(user, "employee_number", "") or "admin")
    _approve_issue(db, issue, actor, reason, request)
    db.commit()

    return RedirectResponse(
        "/plausibility?status=offen&message=Ausnahme+wurde+genehmigt",
        status_code=303,
    )


@router.post("/plausibility/approve-exceptions-bulk")
def approve_plausibility_exceptions_bulk(
    request: Request,
    issue_ids: list[int] = Form(default=[]),
    reason: str = Form(...),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not _can_approve_exception(user):
        return RedirectResponse("/plausibility?status=offen&error=Keine+Berechtigung", status_code=303)

    reason = (reason or "").strip()
    if len(reason) < 3:
        return RedirectResponse("/plausibility?status=offen&error=Bitte+eine+Begründung+angeben", status_code=303)
    if not issue_ids:
        return RedirectResponse("/plausibility?status=offen&error=Keine+Fälle+ausgewählt", status_code=303)

    visible_ids = set(report_visible_employee_ids(db, user))
    issues = db.query(PlausibilityIssue).filter(
        PlausibilityIssue.id.in_(issue_ids),
        PlausibilityIssue.employee_id.in_(visible_ids),
        PlausibilityIssue.check_type == "missing_workday",
        PlausibilityIssue.status == "offen",
    ).order_by(PlausibilityIssue.issue_date.asc(), PlausibilityIssue.id.asc()).all()

    if not issues:
        return RedirectResponse("/plausibility?status=offen&error=Keine+geeigneten+offenen+Fälle+gefunden", status_code=303)

    ensure_plausibility_exception_schema(db)
    actor = str(getattr(user, "employee_number", "") or "admin")
    for issue in issues:
        _approve_issue(db, issue, actor, reason, request)

    db.add(AuditLog(
        actor=actor,
        action="plausibility_exceptions_bulk_approved",
        entity="plausibility",
        entity_id="bulk",
        details=f"{len(issues)} Arbeitstagsausnahmen gemeinsam genehmigt; Grund: {reason}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    return RedirectResponse(
        f"/plausibility?status=offen&message={len(issues)}+Ausnahmen+wurden+genehmigt",
        status_code=303,
    )
