"""Kompatibilitätsrouten für den vor Stempeluhr 6.0 verwendeten RFID-Lernweg.

Die alten URLs bleiben für Bookmarks und Browser-Caches erreichbar, dürfen aber
keinen zweiten RFID-Zustand mehr erzeugen. RFID/NFC wird ausschließlich über
employee_rfid_media und die zentrale Medienverwaltung gepflegt.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from .common import require_admin_response, log_action

router = APIRouter()


def _redirect_to_media(employee_id: int, request: Request, db: Session):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    log_action(
        db,
        user.employee_number if user else "system",
        "legacy_rfid_route_redirected",
        "employees",
        str(employee_id),
        "Alter RFID-Lernweg auf zentrale Anmeldemedien-Verwaltung umgeleitet.",
    )
    return RedirectResponse(
        f"/admin/employees/{employee_id}/rfid-media",
        status_code=303,
    )


@router.get("/admin/employees/{employee_id}/rfid-learn")
def legacy_rfid_learn_get(employee_id: int, request: Request, db: Session = Depends(get_db)):
    return _redirect_to_media(employee_id, request, db)


@router.post("/admin/employees/{employee_id}/rfid-learn")
def legacy_rfid_learn_post(employee_id: int, request: Request, db: Session = Depends(get_db)):
    return _redirect_to_media(employee_id, request, db)


@router.get("/admin/employees/{employee_id}/rfid-learn/cancel")
def legacy_rfid_learn_cancel(employee_id: int, request: Request, db: Session = Depends(get_db)):
    return _redirect_to_media(employee_id, request, db)
