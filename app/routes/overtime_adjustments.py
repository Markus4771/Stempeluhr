from __future__ import annotations

import hashlib
import secrets
import threading
import time
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .common import *
from app.database import Base, SessionLocal
from app.mailer import send_email_from_settings

router = APIRouter()


class OvertimeAdjustment(Base):
    __tablename__ = "overtime_adjustments"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    requested_by = Column(String(100), nullable=False)
    old_balance = Column(Float, nullable=False, default=0.0)
    target_balance = Column(Float, nullable=False, default=0.0)
    effective_at = Column(DateTime, nullable=False, default=datetime.now)
    reason = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    approval_token_hash = Column(String(64), nullable=False, unique=True)
    approved_at = Column(DateTime)
    applied_at = Column(DateTime)
    rejected_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    employee = relationship("Employee")


def _allowed_manager(user) -> bool:
    return is_hr_or_admin(user) or role_name(user) == "Teamleiter"


def _apply_due(db: Session) -> int:
    now = datetime.now()
    rows = db.query(OvertimeAdjustment).filter(
        OvertimeAdjustment.status == "approved",
        OvertimeAdjustment.applied_at.is_(None),
        OvertimeAdjustment.effective_at <= now,
    ).all()
    applied = 0
    for row in rows:
        employee = db.query(Employee).filter(Employee.id == row.employee_id).first()
        if not employee:
            row.status = "failed"
            continue
        employee.overtime_balance = float(row.target_balance or 0.0)
        employee.updated_at = now
        row.applied_at = now
        row.status = "applied"
        applied += 1
    if rows:
        db.commit()
    return applied


def _scheduler() -> None:
    while True:
        db = SessionLocal()
        try:
            _apply_due(db)
        except Exception:
            db.rollback()
        finally:
            db.close()
        time.sleep(60)


@router.on_event("startup")
def start_overtime_scheduler() -> None:
    threading.Thread(target=_scheduler, daemon=True, name="overtime-adjustments").start()


@router.get("/overtime-adjustments", response_class=HTMLResponse)
def overtime_adjustments_page(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not _allowed_manager(user):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Nur Teamleiter, Personal und Administratoren dürfen Überstundenänderungen beantragen.", "return_to": "/reports"})
    _apply_due(db)
    visible_ids = report_visible_employee_ids(db, user)
    employees = db.query(Employee).filter(Employee.id.in_(visible_ids), Employee.active == True).order_by(Employee.last_name, Employee.first_name).all() if visible_ids else []
    rows = db.query(OvertimeAdjustment).filter(OvertimeAdjustment.employee_id.in_(visible_ids)).order_by(OvertimeAdjustment.created_at.desc()).limit(200).all() if visible_ids else []
    return templates.TemplateResponse("overtime_adjustments.html", {"request": request, "user": user, "employees": employees, "rows": rows, "message": request.query_params.get("message", "")})


@router.post("/overtime-adjustments/request")
def request_overtime_adjustment(
    request: Request,
    employee_id: int = Form(...),
    target_balance: float = Form(...),
    effective_at: str = Form(""),
    reason: str = Form(...),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not _allowed_manager(user) or employee_id not in report_visible_employee_ids(db, user):
        return RedirectResponse("/overtime-adjustments?message=Keine+Berechtigung", status_code=303)
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.active == True).first()
    if not employee or not (employee.email or "").strip():
        return RedirectResponse("/overtime-adjustments?message=Mitarbeiter+ohne+E-Mail-Adresse", status_code=303)
    try:
        effective = datetime.strptime(effective_at, "%Y-%m-%dT%H:%M") if effective_at else datetime.now()
    except Exception:
        effective = datetime.now()
    raw_token = secrets.token_urlsafe(32)
    row = OvertimeAdjustment(
        employee_id=employee.id,
        requested_by=user.employee_number,
        old_balance=float(employee.overtime_balance or 0.0),
        target_balance=float(target_balance),
        effective_at=effective,
        reason=reason.strip(),
        status="pending",
        approval_token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
    )
    db.add(row)
    db.commit()
    approval_url = str(request.url_for("approve_overtime_adjustment", token=raw_token))
    reject_url = str(request.url_for("reject_overtime_adjustment", token=raw_token))
    body = (
        f"Hallo {employee.first_name} {employee.last_name},\n\n"
        f"{user.first_name} {user.last_name} beantragt eine Änderung deines Überstundenstands.\n"
        f"Bisher: {row.old_balance:.2f} Stunden\nNeuer Stand: {row.target_balance:.2f} Stunden\n"
        f"Wirksam ab: {row.effective_at.strftime('%d.%m.%Y %H:%M')}\nGrund: {row.reason}\n\n"
        f"Genehmigen: {approval_url}\nAblehnen: {reject_url}\n"
    )
    try:
        send_email_from_settings(db, employee.email.strip(), "Überstundenänderung genehmigen", body)
        log_action(db, user.employee_number, "overtime_adjustment_requested", "employee", str(employee.id), f"{row.old_balance:.2f} -> {row.target_balance:.2f}")
        return RedirectResponse("/overtime-adjustments?message=Genehmigungs-E-Mail+versendet", status_code=303)
    except Exception as exc:
        row.status = "mail_failed"
        db.commit()
        return RedirectResponse("/overtime-adjustments?message=E-Mail-Versand+fehlgeschlagen", status_code=303)


@router.get("/overtime-adjustments/approve/{token}", response_class=HTMLResponse, name="approve_overtime_adjustment")
def approve_overtime_adjustment(token: str, request: Request, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    row = db.query(OvertimeAdjustment).filter(OvertimeAdjustment.approval_token_hash == token_hash, OvertimeAdjustment.status == "pending").first()
    if not row:
        return HTMLResponse("<h1>Link ungültig oder bereits verwendet</h1>", status_code=400)
    row.status = "approved"
    row.approved_at = datetime.now()
    db.commit()
    _apply_due(db)
    return HTMLResponse("<h1>Überstundenänderung genehmigt</h1><p>Die Änderung wird zum angegebenen Zeitpunkt wirksam.</p>")


@router.get("/overtime-adjustments/reject/{token}", response_class=HTMLResponse, name="reject_overtime_adjustment")
def reject_overtime_adjustment(token: str, request: Request, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    row = db.query(OvertimeAdjustment).filter(OvertimeAdjustment.approval_token_hash == token_hash, OvertimeAdjustment.status == "pending").first()
    if not row:
        return HTMLResponse("<h1>Link ungültig oder bereits verwendet</h1>", status_code=400)
    row.status = "rejected"
    row.rejected_at = datetime.now()
    db.commit()
    return HTMLResponse("<h1>Überstundenänderung abgelehnt</h1>")
