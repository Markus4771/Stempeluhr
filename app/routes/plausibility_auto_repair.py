from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import current_user, is_admin_user, redirect_to_login
from app.core.config import TEMPLATE_DIR
from app.database import get_db
from app.services.plausibility_auto_repair import apply_proposal, list_safe_proposals

router = APIRouter(prefix="/plausibility/auto-repair", tags=["plausibility-auto-repair"])
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _actor(user) -> str:
    return f"{user.first_name} {user.last_name}".strip() or str(user.employee_number)


@router.get("")
def preview(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    if not is_admin_user(user):
        return RedirectResponse("/plausibility?error=Keine+Berechtigung", status_code=303)
    proposals = list_safe_proposals(db)
    return templates.TemplateResponse("plausibility_auto_repair.html", {
        "request": request,
        "user": user,
        "proposals": proposals,
        "message": request.query_params.get("message", ""),
        "error": request.query_params.get("error", ""),
    })


@router.post("/{issue_id}/apply")
def apply_one(issue_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    if not is_admin_user(user):
        return RedirectResponse("/plausibility?error=Keine+Berechtigung", status_code=303)
    proposal = next((item for item in list_safe_proposals(db) if item.issue_id == issue_id), None)
    if not proposal:
        return RedirectResponse("/plausibility/auto-repair?error=Vorschlag+nicht+mehr+verfügbar", status_code=303)
    try:
        apply_proposal(db, proposal, _actor(user))
    except ValueError as exc:
        return RedirectResponse(f"/plausibility/auto-repair?error={str(exc).replace(' ', '+')}", status_code=303)
    return RedirectResponse("/plausibility/auto-repair?message=Reparatur+erfolgreich", status_code=303)


@router.post("/apply-selected")
def apply_selected(
    request: Request,
    issue_ids: list[int] = Form(default=[]),
    confirmation: str = Form(""),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    if not is_admin_user(user):
        return RedirectResponse("/plausibility?error=Keine+Berechtigung", status_code=303)
    if confirmation != "REPARIEREN":
        return RedirectResponse("/plausibility/auto-repair?error=Bestätigung+fehlt", status_code=303)

    proposals = {item.issue_id: item for item in list_safe_proposals(db)}
    completed = 0
    failed = 0
    for issue_id in issue_ids:
        proposal = proposals.get(issue_id)
        if not proposal:
            failed += 1
            continue
        try:
            apply_proposal(db, proposal, _actor(user))
            completed += 1
        except ValueError:
            db.rollback()
            failed += 1
    return RedirectResponse(
        f"/plausibility/auto-repair?message={completed}+Reparaturen+ausgeführt,+{failed}+übersprungen",
        status_code=303,
    )
