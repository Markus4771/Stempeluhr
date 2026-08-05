from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth import current_user, is_admin_user
from app.database import get_db
from app.models import PlausibilityIssue
from app.services.plausibility_patterns import employee_booking_pattern

router = APIRouter(prefix="/api/plausibility-patterns", tags=["plausibility-patterns"])


@router.get("/{issue_id}")
def pattern_for_issue(issue_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return JSONResponse({"status": "error", "message": "Nicht angemeldet"}, status_code=401)
    if not is_admin_user(user):
        return JSONResponse({"status": "error", "message": "Keine Berechtigung"}, status_code=403)

    issue = db.query(PlausibilityIssue).filter(PlausibilityIssue.id == issue_id).first()
    if not issue:
        return JSONResponse({"status": "error", "message": "Fall nicht gefunden"}, status_code=404)

    result = employee_booking_pattern(db, issue.employee_id, issue.issue_date)
    return {
        "status": "ok",
        "issue_id": issue.id,
        "employee_id": issue.employee_id,
        "issue_date": issue.issue_date.isoformat(),
        **result,
    }
