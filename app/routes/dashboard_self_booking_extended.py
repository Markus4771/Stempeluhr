from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from .common import create_time_entry, is_fixed_admin_employee, log_action
from .dashboard_self_booking import employee_self_booking_enabled

router = APIRouter()
ALLOWED_DIRECT_TYPES = {"kommen", "gehen", "pause_start", "pause_ende"}


@router.post("/dashboard/self-book")
def dashboard_self_book_extended(
    request: Request,
    entry_type: str = Form(""),
    reason_id: int = Form(0),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not employee_self_booking_enabled(db, user.id):
        return RedirectResponse("/dashboard?error=" + quote("Die eigene Buchung ohne erneute Passworteingabe ist für deinen Benutzer nicht freigegeben."), status_code=303)
    if is_fixed_admin_employee(user):
        return RedirectResponse("/dashboard?error=" + quote("Der Systemadministrator darf keine Arbeitszeit buchen."), status_code=303)

    reason = None
    if reason_id:
        from .stamp_reasons import StampReason, _set_employee_status, stamp_reasons_enabled

        if stamp_reasons_enabled(db):
            reason = db.query(StampReason).filter(StampReason.id == reason_id, StampReason.active == True).first()
        if not reason:
            return RedirectResponse("/dashboard?error=" + quote("Der ausgewählte Stempelgrund ist nicht verfügbar."), status_code=303)

        if reason.entry_type in {"status", "status_clear"}:
            if reason.entry_type == "status_clear":
                _set_employee_status(db, user, None)
                message = "Dein Personenstatus wurde zurückgesetzt."
                action = "employee_status_cleared"
            else:
                _set_employee_status(db, user, reason)
                message = f"Dein Personenstatus wurde auf „{reason.name}“ gesetzt."
                action = "employee_status_set"
            log_action(db, user.employee_number, action, "employee", str(user.id), reason.name)
            return RedirectResponse("/dashboard?message=" + quote(message), status_code=303)

        entry_type = reason.entry_type
        note = f"Stempelgrund: {reason.name} ({reason.code})"
        method = "dashboard_reason"
        label = reason.name
    else:
        if entry_type not in ALLOWED_DIRECT_TYPES:
            return RedirectResponse("/dashboard?error=" + quote("Bitte Kommen, Gehen, Pause Start oder Pause Ende auswählen."), status_code=303)
        labels = {"kommen": "Kommen", "gehen": "Gehen", "pause_start": "Pause Start", "pause_ende": "Pause Ende"}
        label = labels[entry_type]
        note = "Selbstbuchung durch angemeldeten Benutzer ohne erneute Passworteingabe"
        method = "dashboard_session"

    entry, conflicting = create_time_entry(db, user, entry_type, method, "dashboard", note, duplicate_seconds=8)
    if not entry:
        detail = "Die Buchung wurde wegen einer doppelten oder unzulässigen Buchungsfolge nicht gespeichert."
        if conflicting and getattr(conflicting, "entry_type", None):
            detail += f" Letzte Buchung: {conflicting.entry_type}."
        return RedirectResponse("/dashboard?error=" + quote(detail), status_code=303)

    log_action(db, user.employee_number, "dashboard_self_booking", "time_entries", str(entry.id), f"{entry_type}; reason_id={reason_id or 0}")
    return RedirectResponse("/dashboard?message=" + quote(f"{label} wurde für dich gebucht."), status_code=303)
