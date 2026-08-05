from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models import AuditLog, Employee, PlausibilityIssue
from app.routes.common import report_visible_employee_ids, role_name, templates

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
            revoked_by VARCHAR(100),
            revoked_at TIMESTAMP,
            revoke_reason TEXT,
            UNIQUE (employee_id, issue_date, check_type)
        )
    """))
    db.execute(text("ALTER TABLE plausibility_exceptions ADD COLUMN IF NOT EXISTS revoked_by VARCHAR(100)"))
    db.execute(text("ALTER TABLE plausibility_exceptions ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP"))
    db.execute(text("ALTER TABLE plausibility_exceptions ADD COLUMN IF NOT EXISTS revoke_reason TEXT"))
    db.commit()


def _can_approve_exception(user) -> bool:
    if not user:
        return False
    if str(getattr(user, "employee_number", "") or "").strip().lower() == "admin":
        return True
    return role_name(user) in {"Administrator", "Personal", "Teamleiter"}


def _actor(user) -> str:
    return str(getattr(user, "employee_number", "") or "admin")


def _approve_issue(db: Session, issue: PlausibilityIssue, actor: str, reason: str, request: Request) -> None:
    now = datetime.now()
    db.execute(text("""
        INSERT INTO plausibility_exceptions
            (issue_id, employee_id, issue_date, check_type, reason, approved_by, approved_at, active,
             revoked_by, revoked_at, revoke_reason)
        VALUES
            (:issue_id, :employee_id, :issue_date, :check_type, :reason, :approved_by, :approved_at, TRUE,
             NULL, NULL, NULL)
        ON CONFLICT (employee_id, issue_date, check_type)
        DO UPDATE SET
            issue_id = EXCLUDED.issue_id,
            reason = EXCLUDED.reason,
            approved_by = EXCLUDED.approved_by,
            approved_at = EXCLUDED.approved_at,
            active = TRUE,
            revoked_by = NULL,
            revoked_at = NULL,
            revoke_reason = NULL
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


def _revoke_exception(db: Session, exception_id: int, actor: str, reason: str, request: Request) -> bool:
    row = db.execute(text("""
        SELECT id, issue_id, employee_id, issue_date, check_type
        FROM plausibility_exceptions
        WHERE id = :id AND active = TRUE
    """), {"id": exception_id}).mappings().first()
    if not row:
        return False

    now = datetime.now()
    db.execute(text("""
        UPDATE plausibility_exceptions
        SET active = FALSE,
            revoked_by = :revoked_by,
            revoked_at = :revoked_at,
            revoke_reason = :revoke_reason
        WHERE id = :id
    """), {
        "id": exception_id,
        "revoked_by": actor,
        "revoked_at": now,
        "revoke_reason": reason,
    })

    issue = None
    if row["issue_id"]:
        issue = db.query(PlausibilityIssue).filter(PlausibilityIssue.id == row["issue_id"]).first()
    if not issue:
        issue = db.query(PlausibilityIssue).filter(
            PlausibilityIssue.employee_id == row["employee_id"],
            PlausibilityIssue.issue_date == row["issue_date"],
            PlausibilityIssue.check_type == row["check_type"],
        ).order_by(PlausibilityIssue.id.desc()).first()
    if issue:
        issue.status = "offen"
        issue.resolved_at = None
        issue.resolved_by = None
        issue.updated_at = now
        issue.comment = f"Ausnahme widerrufen: {reason}"

    db.add(AuditLog(
        actor=actor,
        action="plausibility_exception_revoked",
        entity="plausibility_exception",
        entity_id=str(exception_id),
        details=(
            f"Ausnahme widerrufen: Mitarbeiter {row['employee_id']}, Datum {row['issue_date']}, "
            f"Prüfart {row['check_type']}; Grund: {reason}"
        ),
        ip_address=request.client.host if request.client else None,
    ))
    return True


@router.get("/plausibility/exceptions", response_class=HTMLResponse)
def plausibility_exceptions_view(
    request: Request,
    employee_id: int = 0,
    check_type: str = "",
    state: str = "active",
    date_from: str = "",
    date_to: str = "",
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not _can_approve_exception(user):
        return RedirectResponse("/plausibility?error=Keine+Berechtigung", status_code=303)

    ensure_plausibility_exception_schema(db)
    visible_ids = report_visible_employee_ids(db, user)
    if not visible_ids:
        visible_ids = [-1]

    conditions = ["pe.employee_id = ANY(:visible_ids)"]
    params: dict = {"visible_ids": visible_ids}
    if employee_id:
        conditions.append("pe.employee_id = :employee_id")
        params["employee_id"] = employee_id
    if check_type:
        conditions.append("pe.check_type = :check_type")
        params["check_type"] = check_type
    if state == "active":
        conditions.append("pe.active = TRUE")
    elif state == "revoked":
        conditions.append("pe.active = FALSE")
    try:
        if date_from:
            params["date_from"] = datetime.strptime(date_from, "%Y-%m-%d").date()
            conditions.append("pe.issue_date >= :date_from")
        if date_to:
            params["date_to"] = datetime.strptime(date_to, "%Y-%m-%d").date()
            conditions.append("pe.issue_date <= :date_to")
    except ValueError:
        date_from = ""
        date_to = ""

    rows = db.execute(text(f"""
        SELECT pe.id, pe.issue_id, pe.employee_id, pe.issue_date, pe.check_type,
               pe.reason, pe.approved_by, pe.approved_at, pe.active,
               pe.revoked_by, pe.revoked_at, pe.revoke_reason,
               e.employee_number, e.first_name, e.last_name
        FROM plausibility_exceptions pe
        JOIN employees e ON e.id = pe.employee_id
        WHERE {' AND '.join(conditions)}
        ORDER BY pe.issue_date DESC, e.last_name, e.first_name, pe.id DESC
    """), params).mappings().all()

    employees = db.query(Employee).filter(Employee.id.in_(visible_ids)).order_by(
        Employee.last_name, Employee.first_name
    ).all()
    check_types = [r[0] for r in db.execute(text("""
        SELECT DISTINCT check_type
        FROM plausibility_exceptions
        ORDER BY check_type
    """)).all()]

    return templates.TemplateResponse("plausibility_exceptions.html", {
        "request": request,
        "user": user,
        "rows": rows,
        "employees": employees,
        "check_types": check_types,
        "filters": {
            "employee_id": employee_id,
            "check_type": check_type,
            "state": state,
            "date_from": date_from,
            "date_to": date_to,
        },
    })


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
    _approve_issue(db, issue, _actor(user), reason, request)
    db.commit()
    return RedirectResponse("/plausibility?status=offen&message=Ausnahme+wurde+genehmigt", status_code=303)


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
    actor = _actor(user)
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


@router.post("/plausibility/exceptions/{exception_id}/revoke")
def revoke_plausibility_exception(
    exception_id: int,
    request: Request,
    reason: str = Form(...),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not _can_approve_exception(user):
        return RedirectResponse("/plausibility/exceptions?error=Keine+Berechtigung", status_code=303)
    reason = (reason or "").strip()
    if len(reason) < 3:
        return RedirectResponse("/plausibility/exceptions?error=Bitte+eine+Widerrufsbegründung+angeben", status_code=303)

    ensure_plausibility_exception_schema(db)
    row = db.execute(text("SELECT employee_id FROM plausibility_exceptions WHERE id=:id"), {"id": exception_id}).first()
    if not row or row[0] not in report_visible_employee_ids(db, user):
        return RedirectResponse("/plausibility/exceptions?error=Ausnahme+nicht+gefunden", status_code=303)
    changed = _revoke_exception(db, exception_id, _actor(user), reason, request)
    db.commit()
    message = "Ausnahme+wurde+widerrufen" if changed else "Ausnahme+war+bereits+widerrufen"
    return RedirectResponse(f"/plausibility/exceptions?message={message}", status_code=303)


@router.post("/plausibility/exceptions/revoke-bulk")
def revoke_plausibility_exceptions_bulk(
    request: Request,
    exception_ids: list[int] = Form(default=[]),
    reason: str = Form(...),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not _can_approve_exception(user):
        return RedirectResponse("/plausibility/exceptions?error=Keine+Berechtigung", status_code=303)
    reason = (reason or "").strip()
    if len(reason) < 3:
        return RedirectResponse("/plausibility/exceptions?error=Bitte+eine+Widerrufsbegründung+angeben", status_code=303)
    if not exception_ids:
        return RedirectResponse("/plausibility/exceptions?error=Keine+Ausnahmen+ausgewählt", status_code=303)

    ensure_plausibility_exception_schema(db)
    visible_ids = set(report_visible_employee_ids(db, user))
    allowed_ids = [r[0] for r in db.execute(text("""
        SELECT id FROM plausibility_exceptions
        WHERE id = ANY(:ids) AND employee_id = ANY(:visible_ids) AND active = TRUE
    """), {"ids": exception_ids, "visible_ids": list(visible_ids)}).all()]
    actor = _actor(user)
    changed = 0
    for exception_id in allowed_ids:
        if _revoke_exception(db, exception_id, actor, reason, request):
            changed += 1
    db.add(AuditLog(
        actor=actor,
        action="plausibility_exceptions_bulk_revoked",
        entity="plausibility_exception",
        entity_id="bulk",
        details=f"{changed} Ausnahmen gemeinsam widerrufen; Grund: {reason}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return RedirectResponse(
        f"/plausibility/exceptions?message={changed}+Ausnahmen+wurden+widerrufen",
        status_code=303,
    )
