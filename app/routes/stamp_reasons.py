from __future__ import annotations

import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.models import Department, Employee, VacationRequest
from .common import *
from .common import _save_pending_rfid_from_terminal
from .vacation import _check_absence_calendar_access, absence_reason_for_request, absence_type_label_map

router = APIRouter()


class StampReason(Base):
    __tablename__ = "stamp_reasons"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    entry_type = Column(String(30), nullable=False, default="kommen")
    active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


ALLOWED_ENTRY_TYPES = {"kommen", "gehen", "pause_start", "pause_ende"}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-") or "stempelgrund"


def active_stamp_reasons(db: Session):
    return db.query(StampReason).filter(StampReason.active == True).order_by(StampReason.sort_order, StampReason.name).all()


def _visible_departments(db: Session, user):
    if not user:
        return []
    if is_hr_or_admin(user):
        return db.query(Department).filter(Department.active == True).order_by(Department.name).all()
    if role_name(user) == "Teamleiter":
        return db.query(Department).filter(Department.active == True, Department.manager_employee_id == user.id).order_by(Department.name).all()
    if user.department_id:
        return db.query(Department).filter(Department.id == user.department_id, Department.active == True).all()
    return []


@router.get("/api/stamp-reasons")
def stamp_reasons_api(db: Session = Depends(get_db)):
    return {"reasons": [{"id": row.id, "name": row.name, "entry_type": row.entry_type} for row in active_stamp_reasons(db)]}


@router.get("/system/settings/stamp-reasons", response_class=HTMLResponse)
def stamp_reasons_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    rows = db.query(StampReason).order_by(StampReason.sort_order, StampReason.name).all()
    return templates.TemplateResponse("system_stamp_reasons.html", {"request": request, "user": user, "rows": rows, "saved": request.query_params.get("saved") == "1"})


@router.post("/system/settings/stamp-reasons/add")
def stamp_reason_add(request: Request, name: str = Form(...), code: str = Form(""), entry_type: str = Form(...), sort_order: int = Form(100), active: str = Form("off"), db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    clean_name = name.strip()
    clean_code = _slug(code or clean_name)
    if not clean_name or entry_type not in ALLOWED_ENTRY_TYPES:
        return RedirectResponse("/system/settings/stamp-reasons", status_code=303)
    if db.query(StampReason).filter(StampReason.code == clean_code).first():
        clean_code = f"{clean_code}-{int(datetime.now().timestamp())}"
    row = StampReason(name=clean_name, code=clean_code, entry_type=entry_type, sort_order=int(sort_order or 100), active=active == "on")
    db.add(row)
    db.commit()
    log_action(db, user.employee_number, "stamp_reason_created", "stamp_reasons", str(row.id), f"{row.name}: {row.entry_type}")
    return RedirectResponse("/system/settings/stamp-reasons?saved=1", status_code=303)


@router.post("/system/settings/stamp-reasons/{reason_id}/save")
def stamp_reason_save(reason_id: int, request: Request, name: str = Form(...), entry_type: str = Form(...), sort_order: int = Form(100), active: str = Form("off"), db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    row = db.query(StampReason).filter(StampReason.id == reason_id).first()
    if row and name.strip() and entry_type in ALLOWED_ENTRY_TYPES:
        row.name = name.strip()
        row.entry_type = entry_type
        row.sort_order = int(sort_order or 100)
        row.active = active == "on"
        row.updated_at = datetime.now()
        db.commit()
        log_action(db, user.employee_number, "stamp_reason_updated", "stamp_reasons", str(row.id), f"{row.name}: {row.entry_type}")
    return RedirectResponse("/system/settings/stamp-reasons?saved=1", status_code=303)


@router.post("/raspberry/reason-scan", response_class=HTMLResponse)
def raspberry_reason_scan(request: Request, rfid_code: str = Form(""), reason_id: int = Form(0), db: Session = Depends(get_db)):
    rfid_code = (rfid_code or "").strip().replace("\r", "").replace("\n", "")
    if not rfid_code:
        return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": "Kein RFID-Code erkannt.", "return_to": "/raspberry"})
    learn_response = _save_pending_rfid_from_terminal(request, db, rfid_code)
    if learn_response:
        return learn_response
    employee = db.query(Employee).filter(Employee.rfid_code == rfid_code, Employee.active == True).first()
    if not employee or is_fixed_admin_employee(employee):
        return templates.TemplateResponse("rfid_unknown.html", {"request": request, "rfid_code": rfid_code, "message": "RFID unbekannt! Bitte Administrator informieren.", "return_to": "/raspberry"})
    reason = db.query(StampReason).filter(StampReason.id == reason_id, StampReason.active == True).first() if reason_id else None
    entry_type = reason.entry_type if reason else determine_auto_entry_type(db, employee.id)
    note = f"Stempelgrund: {reason.name} ({reason.code})" if reason else "Automatische Kommen-/Gehen-Buchung ohne ausgewählten Stempelgrund"
    method = "rfid_reason" if reason else "rfid_auto"
    entry, duplicate_last = create_time_entry(db, employee, entry_type, method, "raspberry", note, duplicate_seconds=8)
    if duplicate_last:
        return templates.TemplateResponse("duplicate_booking.html", {"request": request, "employee": employee, "last": duplicate_last, "seconds": 8, "return_to": "/raspberry"})
    label = reason.name if reason else entry_type
    return templates.TemplateResponse("message.html", {"request": request, "title": reason.name if reason else "Automatisch gebucht", "message": f"{label} für {employee.first_name} {employee.last_name} gebucht.", "return_to": "/raspberry", "status_display_seconds": status_display_seconds(db)})


@router.get("/vacation/department-calendars", response_class=HTMLResponse)
def department_calendars(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    settings = service_settings_dict(db)
    return templates.TemplateResponse("vacation_department_calendars.html", {"request": request, "user": user, "departments": _visible_departments(db, user), "token": settings.get("caldav_vacation_feed_token", "")})


def _ics_escape(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@router.get("/calendar/department/{department_id}.ics")
def department_calendar_ics(department_id: int, request: Request, token: str = "", db: Session = Depends(get_db)):
    settings = service_settings_dict(db)
    denied = _check_absence_calendar_access(request, settings, token)
    if denied:
        return denied
    department = db.query(Department).filter(Department.id == department_id, Department.active == True).first()
    if not department:
        return PlainTextResponse("Kalender nicht gefunden", status_code=404)
    rows = db.query(VacationRequest).join(Employee, VacationRequest.employee_id == Employee.id).filter(VacationRequest.status == "genehmigt", Employee.department_id == department.id).order_by(VacationRequest.start_date).all()
    labels = absence_type_label_map(db)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Stempeluhr//Abteilungskalender//DE", f"X-WR-CALNAME:{_ics_escape('Abwesenheit ' + department.name)}"]
    for row in rows:
        employee_name = f"{row.employee.first_name} {row.employee.last_name}".strip()
        reason = absence_reason_for_request(row, labels)
        lines.extend(["BEGIN:VEVENT", f"UID:absence-{row.id}-department-{department.id}@stempeluhr", f"DTSTART;VALUE=DATE:{row.start_date.strftime('%Y%m%d')}", f"DTEND;VALUE=DATE:{(row.end_date + timedelta(days=1)).strftime('%Y%m%d')}", f"SUMMARY:{_ics_escape(employee_name + ' – ' + reason)}", f"DESCRIPTION:{_ics_escape(reason + ' | ' + employee_name)}", "STATUS:CONFIRMED", "END:VEVENT"])
    lines.append("END:VCALENDAR")
    return PlainTextResponse("\r\n".join(lines) + "\r\n", media_type="text/calendar; charset=utf-8")
