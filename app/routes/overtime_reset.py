from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user, is_admin_user, redirect_to_login
from app.database import get_db
from app.mailer import send_email_from_settings
from app.models import AuditLog, Employee
from app.services.overtime_reset import create_overtime_reset_request, confirm_overtime_reset

router = APIRouter(tags=["overtime-reset"])


@router.post("/admin/employees/{employee_id}/overtime-reset/request")
def request_reset(
    employee_id: int,
    request: Request,
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    if not is_admin_user(user):
        return RedirectResponse("/admin?error=Keine+Berechtigung", status_code=303)

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return RedirectResponse("/admin?error=Mitarbeiter+nicht+gefunden", status_code=303)
    if not (employee.email or "").strip():
        return RedirectResponse("/admin?error=Beim+Mitarbeiter+ist+keine+E-Mail-Adresse+hinterlegt", status_code=303)

    actor = f"{user.first_name} {user.last_name}".strip() or user.employee_number
    row, token = create_overtime_reset_request(db, employee, actor, note)
    confirmation_url = str(request.base_url).rstrip("/") + f"/overtime-reset/confirm/{token}"
    body = (
        f"Hallo {employee.first_name} {employee.last_name},\n\n"
        f"{actor} möchte dein Überstundenkonto von {row.previous_balance:.2f} Stunden auf 0,00 Stunden zurücksetzen.\n\n"
        f"Begründung: {row.note or 'Keine zusätzliche Begründung angegeben.'}\n\n"
        "Der Reset wird erst ausgeführt, wenn du ihn über folgenden Link bestätigst:\n"
        f"{confirmation_url}\n\n"
        "Der Link ist 72 Stunden gültig. Wenn du dem Reset nicht zustimmst, ignoriere diese E-Mail und wende dich an die Verwaltung."
    )
    try:
        send_email_from_settings(db, employee.email, "Überstunden-Reset bestätigen", body)
    except Exception as exc:
        row.status = "mail_failed"
        row.note = ((row.note or "") + f"\nE-Mail-Fehler: {exc}").strip()
        db.commit()
        return RedirectResponse("/admin?error=E-Mail+konnte+nicht+gesendet+werden", status_code=303)

    db.add(AuditLog(
        actor=actor,
        action="overtime_reset_requested",
        entity="employee",
        entity_id=str(employee.id),
        details=f"Bestätigung für Reset von {row.previous_balance:.2f} h angefordert; E-Mail an {employee.email} gesendet.",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return RedirectResponse("/admin?message=Bestätigungs-E-Mail+für+den+Überstunden-Reset+wurde+gesendet", status_code=303)


@router.get("/overtime-reset/confirm/{token}", response_class=HTMLResponse)
def confirm_reset(token: str, db: Session = Depends(get_db)):
    row, employee, message = confirm_overtime_reset(db, token)
    success = bool(row and employee and row.status == "confirmed")
    title = "Überstunden-Reset bestätigt" if success else "Überstunden-Reset nicht ausgeführt"
    return HTMLResponse(
        "<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Überstunden-Reset</title><style>body{font-family:system-ui;background:#f3f6fb;margin:0;padding:2rem}.box{max-width:650px;margin:8vh auto;background:white;padding:2rem;border-radius:14px;box-shadow:0 8px 30px #0001}h1{color:#17365d}.ok{border-left:6px solid #198754}.error{border-left:6px solid #b42318}</style></head>"
        f"<body><main class='box {'ok' if success else 'error'}'><h1>{title}</h1><p>{message}</p>"
        + (f"<p>Mitarbeiter: <strong>{employee.first_name} {employee.last_name}</strong></p>" if employee else "")
        + "<p>Dieses Fenster kann geschlossen werden.</p></main></body></html>"
    )
