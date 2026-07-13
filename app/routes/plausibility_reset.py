from .common import *
from urllib.parse import urlencode

router = APIRouter()


def _return_url(employee_id: int, status: str, date_from: str, date_to: str) -> str:
    return "/plausibility?" + urlencode({
        "employee_id": int(employee_id or 0),
        "status": status or "offen",
        "date_from": date_from or "",
        "date_to": date_to or "",
    })


def _can_reset(user) -> bool:
    return is_hr_or_admin(user) or role_name(user) == "Teamleiter"


@router.post("/plausibility/{issue_id}/reset")
def reset_plausibility_issue(
    issue_id: int,
    request: Request,
    filter_employee_id: int = Form(0),
    filter_status: str = Form("offen"),
    filter_date_from: str = Form(""),
    filter_date_to: str = Form(""),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    return_to = _return_url(filter_employee_id, filter_status, filter_date_from, filter_date_to)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not _can_reset(user):
        return templates.TemplateResponse("message.html", {
            "request": request, "user": user, "title": "Keine Berechtigung",
            "message": "Nur Teamleiter, Personal und Administratoren dürfen Plausibilitätsmeldungen zurücksetzen.",
            "return_to": return_to,
        })

    issue = db.query(PlausibilityIssue).filter(PlausibilityIssue.id == issue_id).first()
    if not issue or issue.employee_id not in report_visible_employee_ids(db, user):
        return templates.TemplateResponse("message.html", {
            "request": request, "user": user, "title": "Keine Berechtigung",
            "message": "Diese Plausibilitätsmeldung ist nicht sichtbar oder nicht vorhanden.",
            "return_to": return_to,
        })

    issue.status = "offen"
    issue.comment = None
    issue.resolved_at = None
    issue.resolved_by = None
    issue.updated_at = datetime.now()
    db.commit()
    log_action(db, user.employee_number, "plausibility_reset", "plausibility", str(issue.id), "Meldung auf offen zurückgesetzt")
    return RedirectResponse(return_to, status_code=303)
