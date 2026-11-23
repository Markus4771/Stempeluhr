from __future__ import annotations

from datetime import datetime, time
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import current_user, is_admin_user, redirect_to_login
from app.core.config import TEMPLATE_DIR
from app.database import get_db
from app.models import PlausibilityIssue, TimeEntry

router = APIRouter(prefix="/plausibility/assistant", tags=["plausibility-assistant"])
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _severity_rank(value: str | None) -> int:
    value = str(value or "").strip().lower()
    if value in {"rot", "kritisch", "critical", "danger"}:
        return 0
    if value in {"gelb", "warnung", "warning"}:
        return 1
    return 2


def _suggestion(issue: PlausibilityIssue, entries: list[TimeEntry]) -> dict:
    check = str(issue.check_type or "").lower()
    message = str(issue.message or "").lower()
    combined = f"{check} {message}"
    entry_types = [str(entry.entry_type or "") for entry in entries]

    if "gehen" in combined and ("fehlt" in combined or "missing" in combined):
        return {
            "title": "Fehlendes Arbeitsende ergänzen",
            "text": "Prüfe die tatsächliche Endzeit und trage eine Gehen-Buchung über die Korrektur ein.",
            "requires_edit": True,
        }
    if "kommen" in combined and ("fehlt" in combined or "missing" in combined):
        return {
            "title": "Fehlenden Arbeitsbeginn ergänzen",
            "text": "Prüfe die tatsächliche Startzeit und trage eine Kommen-Buchung über die Korrektur ein.",
            "requires_edit": True,
        }
    if "pause" in combined:
        return {
            "title": "Pausenbuchungen prüfen",
            "text": "Kontrolliere Pausenbeginn und Pausenende. Fehlende Buchungen müssen mit der tatsächlichen Uhrzeit ergänzt werden.",
            "requires_edit": True,
        }
    if "doppel" in combined or "duplicate" in combined:
        return {
            "title": "Doppelbuchung prüfen",
            "text": "Vergleiche die zeitnahen Buchungen und lösche ausschließlich den nachweislich falschen Eintrag über die Korrektur.",
            "requires_edit": True,
        }
    if "10" in combined or "lang" in combined or "arbeitszeit" in combined:
        return {
            "title": "Arbeitsdauer bestätigen",
            "text": "Ist die lange Arbeitszeit sachlich korrekt, kann der Fall bestätigt werden. Andernfalls Buchungen korrigieren.",
            "requires_edit": False,
        }
    if not entries:
        return {
            "title": "Keine Tagesbuchungen gefunden",
            "text": "Prüfe Abwesenheit, Feiertag oder fehlende Buchungen. Eine automatische Zeitänderung wird nicht vorgenommen.",
            "requires_edit": True,
        }
    return {
        "title": "Fall fachlich prüfen",
        "text": "Vergleiche den Hinweis mit den Tagesbuchungen. Bestätige den Fall nur, wenn keine Buchungsänderung erforderlich ist.",
        "requires_edit": False,
    }


def _open_issues(db: Session):
    rows = db.query(PlausibilityIssue).filter(PlausibilityIssue.status == "offen").all()
    return sorted(rows, key=lambda row: (_severity_rank(row.severity), row.issue_date, row.id))


@router.get("")
def assistant(request: Request, issue_id: int = 0, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    if not is_admin_user(user):
        return RedirectResponse("/plausibility?error=Keine+Berechtigung", status_code=303)

    issues = _open_issues(db)
    if not issues:
        return templates.TemplateResponse("plausibility_assistant.html", {
            "request": request,
            "user": user,
            "issues": [],
            "issue": None,
            "entries": [],
            "position": 0,
            "total": 0,
            "suggestion": None,
        })

    issue = next((row for row in issues if row.id == issue_id), issues[0])
    position = issues.index(issue) + 1
    day_start = datetime.combine(issue.issue_date, time.min)
    day_end = datetime.combine(issue.issue_date, time.max)
    entries = (
        db.query(TimeEntry)
        .filter(
            TimeEntry.employee_id == issue.employee_id,
            TimeEntry.timestamp >= day_start,
            TimeEntry.timestamp <= day_end,
        )
        .order_by(TimeEntry.timestamp.asc())
        .all()
    )
    return templates.TemplateResponse("plausibility_assistant.html", {
        "request": request,
        "user": user,
        "issues": issues,
        "issue": issue,
        "entries": entries,
        "position": position,
        "total": len(issues),
        "suggestion": _suggestion(issue, entries),
    })


@router.post("/{issue_id}/decision")
def decision(
    issue_id: int,
    request: Request,
    action: str = Form(...),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    if not is_admin_user(user):
        return RedirectResponse("/plausibility?error=Keine+Berechtigung", status_code=303)

    issue = db.query(PlausibilityIssue).filter(PlausibilityIssue.id == issue_id).first()
    if not issue:
        return RedirectResponse("/plausibility/assistant?error=Fall+nicht+gefunden", status_code=303)

    actor = f"{user.first_name} {user.last_name}".strip()
    if action == "complete":
        issue.status = "erledigt"
        issue.resolved_at = datetime.now()
        issue.resolved_by = actor
        issue.comment = comment.strip() or "Im Plausibilitäts-Assistenten fachlich bestätigt."
        db.commit()
    elif action == "ignore":
        issue.status = "ignoriert"
        issue.resolved_at = datetime.now()
        issue.resolved_by = actor
        issue.comment = comment.strip() or "Im Plausibilitäts-Assistenten ignoriert."
        db.commit()
    elif action == "reviewed":
        issue.status = "geprueft"
        issue.comment = comment.strip() or "Geprüft; weitere Korrektur erforderlich."
        db.commit()
    elif action == "edit":
        issue.status = "geprueft"
        issue.comment = comment.strip() or "Zur manuellen Buchungskorrektur weitergeleitet."
        db.commit()
        params = urlencode({"employee_id": issue.employee_id, "date": issue.issue_date.isoformat(), "plausibility_issue_id": issue.id})
        return RedirectResponse(f"/corrections?{params}", status_code=303)
    # skip verändert den Fall bewusst nicht.

    remaining = _open_issues(db)
    next_issue = next((row for row in remaining if row.id != issue_id), None)
    if next_issue:
        return RedirectResponse(f"/plausibility/assistant?issue_id={next_issue.id}", status_code=303)
    return RedirectResponse("/plausibility/assistant", status_code=303)
