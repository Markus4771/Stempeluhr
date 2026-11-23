from __future__ import annotations

from datetime import datetime, time
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import current_user, redirect_to_login
from app.core.config import TEMPLATE_DIR
from app.database import get_db
from app.models import PlausibilityIssue, TimeEntry

router = APIRouter(tags=["employee-plausibility"])
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

VISIBLE_STATUSES = ("offen", "geprueft")


def _employee_issues(db: Session, employee_id: int):
    return (
        db.query(PlausibilityIssue)
        .filter(
            PlausibilityIssue.employee_id == employee_id,
            PlausibilityIssue.status.in_(VISIBLE_STATUSES),
        )
        .order_by(PlausibilityIssue.issue_date.desc(), PlausibilityIssue.id.desc())
        .all()
    )


def _day_entries(db: Session, issue: PlausibilityIssue):
    day_start = datetime.combine(issue.issue_date, time.min)
    day_end = datetime.combine(issue.issue_date, time.max)
    return (
        db.query(TimeEntry)
        .filter(
            TimeEntry.employee_id == issue.employee_id,
            TimeEntry.timestamp >= day_start,
            TimeEntry.timestamp <= day_end,
            or_(TimeEntry.deleted.is_(False), TimeEntry.deleted.is_(None)),
        )
        .order_by(TimeEntry.timestamp.asc())
        .all()
    )


@router.get("/api/me/plausibility-summary")
def employee_plausibility_summary(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return JSONResponse({"authenticated": False, "open": 0}, status_code=401)
    issues = _employee_issues(db, user.id)
    return {
        "authenticated": True,
        "open": len(issues),
        "critical": sum(1 for row in issues if str(row.severity or "").lower() in {"rot", "kritisch", "critical", "danger"}),
        "url": "/me/plausibility",
        "latest_date": issues[0].issue_date.isoformat() if issues else None,
    }


@router.get("/me/plausibility")
def employee_plausibility(request: Request, issue_id: int = 0, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    issues = _employee_issues(db, user.id)
    issue = next((row for row in issues if row.id == issue_id), issues[0] if issues else None)
    entries = _day_entries(db, issue) if issue else []
    return templates.TemplateResponse("employee_plausibility.html", {
        "request": request,
        "user": user,
        "issues": issues,
        "issue": issue,
        "entries": entries,
    })


@router.post("/me/plausibility/{issue_id}/respond")
def employee_plausibility_respond(
    issue_id: int,
    request: Request,
    action: str = Form(...),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    issue = db.query(PlausibilityIssue).filter(
        PlausibilityIssue.id == issue_id,
        PlausibilityIssue.employee_id == user.id,
        PlausibilityIssue.status.in_(VISIBLE_STATUSES),
    ).first()
    if not issue:
        return RedirectResponse("/me/plausibility?error=Fall+nicht+gefunden", status_code=303)

    response_text = comment.strip()
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    employee_name = f"{user.first_name} {user.last_name}".strip()

    if action == "confirm":
        issue.status = "geprueft"
        note = response_text or "Buchungen wurden vom Mitarbeiter als sachlich korrekt bestätigt."
        issue.comment = f"Mitarbeiterbestätigung {timestamp} durch {employee_name}: {note}"
        issue.notified_employee_at = issue.notified_employee_at or datetime.now()
        db.commit()
        return RedirectResponse("/me/plausibility?message=Bestätigung+gespeichert", status_code=303)

    if action == "comment":
        if not response_text:
            return RedirectResponse(f"/me/plausibility?issue_id={issue.id}&error=Bitte+Kommentar+eingeben", status_code=303)
        issue.comment = f"Mitarbeiterhinweis {timestamp} durch {employee_name}: {response_text}"
        issue.notified_employee_at = issue.notified_employee_at or datetime.now()
        db.commit()
        return RedirectResponse("/me/plausibility?message=Hinweis+gespeichert", status_code=303)

    if action == "correction":
        note = response_text or "Mitarbeiter bittet um Prüfung und Korrektur der Buchungen."
        issue.status = "geprueft"
        issue.comment = f"Korrekturwunsch {timestamp} durch {employee_name}: {note}"
        issue.notified_employee_at = issue.notified_employee_at or datetime.now()
        db.commit()
        params = urlencode({
            "employee_id": user.id,
            "date": issue.issue_date.isoformat(),
            "plausibility_issue_id": issue.id,
            "message": "Plausibilitätsfall zur Korrektur vorgemerkt",
        })
        return RedirectResponse(f"/corrections?{params}", status_code=303)

    return RedirectResponse(f"/me/plausibility?issue_id={issue.id}&error=Ungültige+Aktion", status_code=303)
