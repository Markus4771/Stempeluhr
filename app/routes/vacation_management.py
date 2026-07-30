from datetime import datetime
from html import escape

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, VacationRequest
from app.models_vacation import (
    CompanyClosure,
    VacationAccount,
    VacationLedgerEntry,
    VacationProfile,
    VacationSchedulePeriod,
)
from app.routes.common import current_user, log_action
from app.routes.vacation import is_vacation_admin
from app.services.vacation_management import (
    account_balance,
    annual_entitlement,
    get_or_create_account,
    get_or_create_profile,
    reverse_request,
)

router = APIRouter()


def _admin(request: Request, db: Session):
    user = current_user(request, db)
    if not user:
        return None, RedirectResponse("/login", status_code=303)
    if not is_vacation_admin(user):
        return user, RedirectResponse("/vacation", status_code=303)
    return user, None


def _layout(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html lang='de'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title>"
        "<style>body{font-family:Arial,sans-serif;max-width:1200px;margin:24px auto;padding:0 16px;}"
        "table{border-collapse:collapse;width:100%;margin:16px 0;}th,td{border:1px solid #ccc;padding:8px;text-align:left;}"
        "form{border:1px solid #ddd;padding:14px;margin:16px 0;border-radius:8px;}label{display:block;margin:8px 0;}"
        "input,select,textarea{padding:7px;min-width:220px;}button{padding:8px 14px;} .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;}"
        ".hint{background:#f3f5f7;padding:12px;border-radius:8px}.ok{color:#176b2c}.warn{color:#8a4b00}</style></head><body>"
        f"<p><a href='/vacation'>← Urlaub</a> · <a href='/'>Dashboard</a></p><h1>{escape(title)}</h1>{body}</body></html>"
    )


@router.get("/vacation/management", response_class=HTMLResponse)
def vacation_management(request: Request, year: int | None = None, db: Session = Depends(get_db)):
    user, denied = _admin(request, db)
    if denied:
        return denied
    selected_year = year or datetime.now().year
    employees = db.query(Employee).filter(Employee.active == True).order_by(Employee.last_name, Employee.first_name).all()
    profiles = {p.employee_id: p for p in db.query(VacationProfile).all()}
    accounts = {
        (a.employee_id, a.account_type): a
        for a in db.query(VacationAccount).filter(VacationAccount.year == selected_year).all()
    }
    closures = db.query(CompanyClosure).order_by(CompanyClosure.start_date.desc()).limit(20).all()

    rows = []
    options = []
    for emp in employees:
        profile = profiles.get(emp.id)
        annual = accounts.get((emp.id, "annual"))
        entitlement = annual.entitlement if annual else float(annual_entitlement(db, emp, selected_year))
        used = annual.used if annual else 0.0
        balance = account_balance(annual) if annual else entitlement
        name = f"{emp.first_name} {emp.last_name}".strip()
        rows.append(
            f"<tr><td>{escape(name)}</td><td>{escape((profile.calculation_model if profile else 'five_day'))}</td>"
            f"<td>{entitlement:.1f}</td><td>{used:.1f}</td><td>{balance:.1f}</td></tr>"
        )
        options.append(f"<option value='{emp.id}'>{escape(name)} ({escape(emp.employee_number)})</option>")

    employee_options = "".join(options)
    closure_rows = "".join(
        f"<tr><td>{escape(c.name)}</td><td>{c.start_date}</td><td>{c.end_date}</td><td>{'Ja' if c.deduct_vacation else 'Nein'}</td></tr>"
        for c in closures
    ) or "<tr><td colspan='4'>Keine Betriebsferien hinterlegt.</td></tr>"

    body = f"""
    <div class='hint'><strong>Verbindliche Grundlage:</strong> Alle Ansprüche werden auf eine 5-Tage-Woche bezogen. Bei Anträgen zählen ausschließlich Montag bis Freitag; Wochenenden und volle Feiertage werden nicht abgezogen.</div>
    <h2>Kontenübersicht {selected_year}</h2>
    <table><thead><tr><th>Mitarbeiter</th><th>Modell</th><th>Anspruch</th><th>Verbraucht</th><th>Verfügbar</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    <div class='grid'>
      <form method='post' action='/vacation/management/profile'>
        <h2>Berechnungsprofil</h2>
        <label>Mitarbeiter<select name='employee_id'>{employee_options}</select></label>
        <label>Modell<select name='calculation_model'><option value='five_day'>Feste 5-Tage-Woche</option><option value='fixed_part_time'>Teilzeit mit festen Arbeitstagen</option><option value='irregular_year'>Unregelmäßige Arbeitstage/Jahresmodell</option><option value='manual'>Manueller Anspruch</option></select></label>
        <label>Basisanspruch bei 5 Tagen<input type='number' step='0.5' name='base_entitlement' value='30'></label>
        <label>Arbeitstage pro Woche<input type='number' step='0.5' min='0' max='5' name='weekly_workdays' value='5'></label>
        <label>Arbeitstage pro Jahr<input type='number' step='1' min='0' name='annual_workdays' value='260'></label>
        <label>Manueller Anspruch<input type='number' step='0.5' name='manual_entitlement'></label>
        <label><input type='checkbox' name='automatic_proration' checked> Eintritt/Austritt automatisch anteilig berechnen</label>
        <button>Profil speichern</button>
      </form>
      <form method='post' action='/vacation/management/period'>
        <h2>Arbeitszeitwechsel</h2>
        <label>Mitarbeiter<select name='employee_id'>{employee_options}</select></label>
        <label>Von<input type='date' name='start_date' required></label><label>Bis<input type='date' name='end_date' required></label>
        <label>Arbeitstage/Woche<input type='number' step='0.5' min='0' max='5' name='weekly_workdays'></label>
        <label>Arbeitstage/Jahr<input type='number' step='1' min='0' name='annual_workdays'></label>
        <label>Hinweis<textarea name='note'></textarea></label><button>Abschnitt speichern</button>
      </form>
      <form method='post' action='/vacation/management/account-adjustment'>
        <h2>Kontokorrektur/Zusatzurlaub</h2>
        <label>Mitarbeiter<select name='employee_id'>{employee_options}</select></label>
        <label>Jahr<input type='number' name='year' value='{selected_year}'></label>
        <label>Konto<select name='account_type'><option value='annual'>Jahresurlaub</option><option value='carryover'>Resturlaub Vorjahr</option><option value='additional'>Zusatzurlaub</option><option value='special'>Sonderurlaub</option></select></label>
        <label>Betrag (+ Gutschrift, − Abzug)<input type='number' step='0.5' name='amount' required></label>
        <label>Begründung<textarea name='reason' required></textarea></label><button>Korrektur buchen</button>
      </form>
      <form method='post' action='/vacation/management/closure'>
        <h2>Betriebsferien</h2>
        <label>Bezeichnung<input name='name' required></label><label>Von<input type='date' name='start_date' required></label><label>Bis<input type='date' name='end_date' required></label>
        <label>Abteilungs-ID (leer = Firma)<input type='number' name='department_id'></label>
        <label><input type='checkbox' name='deduct_vacation' checked> Auf Urlaub anrechnen</label>
        <label>Hinweis<textarea name='note'></textarea></label><button>Betriebsferien speichern</button>
      </form>
    </div>
    <h2>Betriebsferien</h2><table><thead><tr><th>Name</th><th>Von</th><th>Bis</th><th>Urlaubsabzug</th></tr></thead><tbody>{closure_rows}</tbody></table>
    """
    return _layout("Urlaubsverwaltung 5.6.33", body)


@router.post("/vacation/management/profile")
def save_profile(
    request: Request,
    employee_id: int = Form(...),
    calculation_model: str = Form("five_day"),
    base_entitlement: float = Form(30.0),
    weekly_workdays: float = Form(5.0),
    annual_workdays: float = Form(260.0),
    manual_entitlement: str = Form(""),
    automatic_proration: str = Form("off"),
    db: Session = Depends(get_db),
):
    user, denied = _admin(request, db)
    if denied:
        return denied
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return RedirectResponse("/vacation/management", status_code=303)
    profile = get_or_create_profile(db, employee)
    profile.calculation_model = calculation_model if calculation_model in {"five_day", "fixed_part_time", "irregular_year", "manual"} else "five_day"
    profile.base_entitlement = max(0.0, base_entitlement)
    profile.weekly_workdays = min(5.0, max(0.0, weekly_workdays))
    profile.annual_workdays = max(0.0, annual_workdays)
    profile.manual_entitlement = float(manual_entitlement) if manual_entitlement.strip() else None
    profile.automatic_proration = automatic_proration == "on"
    profile.updated_at = datetime.now()
    db.query(VacationAccount).filter(VacationAccount.employee_id == employee.id, VacationAccount.account_type == "annual").delete(synchronize_session=False)
    log_action(db, user.employee_number, "vacation_profile_updated", "employees", str(employee.id), profile.calculation_model)
    db.commit()
    return RedirectResponse("/vacation/management", status_code=303)


@router.post("/vacation/management/period")
def save_period(
    request: Request,
    employee_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    weekly_workdays: str = Form(""),
    annual_workdays: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    user, denied = _admin(request, db)
    if denied:
        return denied
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    if end >= start:
        db.add(VacationSchedulePeriod(employee_id=employee_id, start_date=start, end_date=end, weekly_workdays=float(weekly_workdays) if weekly_workdays else None, annual_workdays=float(annual_workdays) if annual_workdays else None, note=note.strip() or None))
        db.query(VacationAccount).filter(VacationAccount.employee_id == employee_id, VacationAccount.year == start.year, VacationAccount.account_type == "annual").delete(synchronize_session=False)
        log_action(db, user.employee_number, "vacation_schedule_period_created", "employees", str(employee_id), f"{start} bis {end}")
        db.commit()
    return RedirectResponse("/vacation/management", status_code=303)


@router.post("/vacation/management/account-adjustment")
def account_adjustment(
    request: Request,
    employee_id: int = Form(...),
    year: int = Form(...),
    account_type: str = Form("annual"),
    amount: float = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
):
    user, denied = _admin(request, db)
    if denied:
        return denied
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee:
        account = get_or_create_account(db, employee, year, account_type)
        account.entitlement = round(float(account.entitlement or 0) + amount, 2)
        account.updated_at = datetime.now()
        db.add(VacationLedgerEntry(employee_id=employee.id, year=year, account_type=account_type, amount=-amount, balance_after=account_balance(account), action="manual_adjustment", reason=reason.strip(), actor=user.employee_number))
        log_action(db, user.employee_number, "vacation_account_adjusted", "employees", str(employee.id), f"{account_type}: {amount:+.1f}; {reason[:200]}")
        db.commit()
    return RedirectResponse(f"/vacation/management?year={year}", status_code=303)


@router.post("/vacation/management/closure")
def create_closure(
    request: Request,
    name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    department_id: str = Form(""),
    deduct_vacation: str = Form("off"),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    user, denied = _admin(request, db)
    if denied:
        return denied
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    if end >= start:
        row = CompanyClosure(name=name.strip(), start_date=start, end_date=end, department_id=int(department_id) if department_id else None, deduct_vacation=deduct_vacation == "on", note=note.strip() or None)
        db.add(row)
        log_action(db, user.employee_number, "company_closure_created", "company_closures", "new", f"{name}: {start} bis {end}")
        db.commit()
    return RedirectResponse("/vacation/management", status_code=303)


@router.post("/vacation/{request_id}/illness")
def convert_vacation_to_illness(
    request_id: int,
    request: Request,
    reason: str = Form("Arbeitsunfähigkeit während des Urlaubs"),
    db: Session = Depends(get_db),
):
    user, denied = _admin(request, db)
    if denied:
        return denied
    row = db.query(VacationRequest).filter(VacationRequest.id == request_id).first()
    if row and row.status == "genehmigt" and row.request_type in {"abwesenheit", "urlaub"}:
        reverse_request(db, row, user.employee_number, "illness_refund", reason)
        row.request_type = "krank"
        row.decision_comment = ((row.decision_comment or "") + f" | In Krankheit umgewandelt: {reason}").strip(" |")
        log_action(db, user.employee_number, "vacation_converted_to_illness", "vacation_requests", str(row.id), reason[:300])
        db.commit()
    return RedirectResponse("/vacation/approvals", status_code=303)
