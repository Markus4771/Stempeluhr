from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user, is_admin_user, redirect_to_login
from app.database import get_db
from app.services.plausibility_reconcile import reconcile_open_plausibility_issues

router = APIRouter(tags=["plausibility-reconcile"])


@router.post("/plausibility/reconcile")
def reconcile(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    if not is_admin_user(user):
        return RedirectResponse("/plausibility", status_code=303)

    reconcile_open_plausibility_issues(db)
    return RedirectResponse("/plausibility", status_code=303)
