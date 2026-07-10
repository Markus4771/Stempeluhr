from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from uuid import uuid4
from urllib.parse import quote

import caldav
import recurring_ical_events
from icalendar import Calendar
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Holiday
from app.routes.common import templates, require_system_admin_response, log_action
from app.services.settings_service import get_setting, set_setting, settings_dict

SYNC_LOG_KEY = "caldav_sync_log_json"

router = APIRouter()

ACCOUNTS_KEY = "caldav_accounts_json"


def _load_accounts(db: Session) -> list[dict]:
    raw = get_setting(db, ACCOUNTS_KEY, "[]") or "[]"
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_accounts(db: Session, accounts: list[dict]) -> None:
    set_setting(db, ACCOUNTS_KEY, json.dumps(accounts, ensure_ascii=False, indent=2))
    db.commit()


def _append_sync_log(db: Session, account: dict | None, status: str, message: str) -> None:
    raw = get_setting(db, SYNC_LOG_KEY, "[]") or "[]"
    try:
        log = json.loads(raw)
        if not isinstance(log, list):
            log = []
    except Exception:
        log = []
    log.insert(0, {
        "time": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "account": (account or {}).get("name", "System"),
        "status": status,
        "message": message,
    })
    set_setting(db, SYNC_LOG_KEY, json.dumps(log[:50], ensure_ascii=False, indent=2))


def _load_sync_log(db: Session) -> list[dict]:
    raw = get_setting(db, SYNC_LOG_KEY, "[]") or "[]"
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _interval_hours(account: dict) -> int | None:
    value = str(account.get("interval") or "daily").strip().lower()
    if value in {"manual", "none", "aus"}:
        return None
    if value in {"hourly", "1h"}:
        return 1
    if value == "6h":
        return 6
    return 24


def _sync_due(account: dict) -> bool:
    if not _bool(account.get("enabled")):
        return False
    hours = _interval_hours(account)
    if hours is None:
        return False
    last = str(account.get("last_sync") or "").strip()
    if not last:
        return True
    try:
        last_dt = datetime.strptime(last, "%d.%m.%Y %H:%M:%S")
        return datetime.now() - last_dt >= timedelta(hours=max(1, hours))
    except Exception:
        return True


def sync_due_caldav_accounts(db: Session) -> tuple[int, int]:
    accounts = _load_accounts(db)
    total_new = 0
    processed = 0
    changed = False
    year = datetime.now().year
    for account in accounts:
        if str(account.get("purpose") or "holidays") not in {"holidays", "company"}:
            continue
        if not _sync_due(account):
            continue
        processed += 1
        try:
            count = _import_holidays_for_account(db, account, year)
            total_new += count
            _append_sync_log(db, account, "OK", account.get("last_status") or f"{count} Feiertage importiert")
        except Exception as exc:
            account["last_status"] = f"Fehler: {exc}"
            account["last_sync"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            _append_sync_log(db, account, "FEHLER", str(exc))
        changed = True
    if changed:
        _save_accounts(db, accounts)
    return processed, total_new



def _absence_calendar_slug(name: str) -> str:
    text = (name or "Abwesenheit").strip() or "Abwesenheit"
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "abwesenheit"

def _bool(v) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "on", "yes", "ja", "aktiv"}


def _account_by_id(accounts: list[dict], account_id: str) -> dict | None:
    for account in accounts:
        if str(account.get("id")) == str(account_id):
            return account
    return None


def _client(account: dict):
    url = (account.get("server_url") or "").strip()
    username = (account.get("username") or "").strip() or None
    password = account.get("password") or None
    if not url:
        raise RuntimeError("Server-URL fehlt.")
    return caldav.DAVClient(url=url, username=username, password=password)


def _list_calendars(account: dict) -> list[dict]:
    if not (account.get("server_url") or "").strip():
        raise RuntimeError("Server-URL fehlt.")
    client = _client(account)
    principal = client.principal()
    result = []
    for cal in principal.calendars():
        name = ""
        try:
            name = cal.get_properties(["{DAV:}displayname"]).get("{DAV:}displayname", "")
        except Exception:
            name = ""
        if not name:
            name = str(getattr(cal, "name", "") or "")
        if not name:
            name = str(cal.url).rstrip("/").split("/")[-1]
        result.append({"name": name, "url": str(cal.url)})
    return result


def _import_holidays_for_account(db: Session, account: dict, year: int | None = None) -> int:
    calendar_url = (account.get("calendar_url") or "").strip()
    if not calendar_url:
        raise RuntimeError("Kein Kalender ausgewählt.")
    if year is None:
        year = datetime.now().year
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)

    client = _client(account)
    target_calendar = caldav.Calendar(client=client, url=calendar_url)
    events = target_calendar.date_search(start=start, end=end, expand=True)
    count = 0
    updated = 0
    for item in events:
        try:
            cal = Calendar.from_ical(item.data)
            expanded = recurring_ical_events.of(cal).between(start, end)
            components = expanded or list(cal.walk("VEVENT"))
            for ev in components:
                summary = str(ev.get("SUMMARY", "Feiertag")).strip() or "Feiertag"
                dtstart_prop = ev.get("DTSTART")
                if not dtstart_prop:
                    continue
                dtstart = dtstart_prop.dt
                holiday_date = dtstart.date() if isinstance(dtstart, datetime) else dtstart
                if not isinstance(holiday_date, date):
                    continue
                summary_lower = summary.lower()
                half_day = any(token in summary_lower for token in ["halb", "1/2", "halber"])
                exists = db.query(Holiday).filter(Holiday.date == holiday_date, Holiday.name == summary).first()
                if exists:
                    exists.federal_state = account.get("name") or "CalDAV"
                    exists.half_day = half_day
                    exists.active = True
                    updated += 1
                else:
                    db.add(Holiday(name=summary, date=holiday_date, federal_state=account.get("name") or "CalDAV", half_day=half_day, active=True))
                    count += 1
        except Exception:
            continue
    account["last_sync"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    account["last_status"] = f"{count} Feiertage neu, {updated} aktualisiert"
    db.commit()
    return count


@router.get("/system/settings/caldav", response_class=HTMLResponse)
def caldav_accounts_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    accounts = _load_accounts(db)
    settings = settings_dict(db)
    return templates.TemplateResponse("system_caldav_accounts.html", {"request": request, "user": user, "accounts": accounts, "settings": settings, "message": request.query_params.get("message", ""), "calendars": [], "edit_account": None, "sync_log": _load_sync_log(db), "holiday_count": db.query(Holiday).filter(Holiday.active == True).count(), "all_holiday_count": db.query(Holiday).count()})


@router.get("/system/settings/caldav/accounts", response_class=HTMLResponse)
def caldav_accounts_alias(request: Request, db: Session = Depends(get_db)):
    return caldav_accounts_page(request, db)


@router.get("/system/settings/caldav/{account_id}/edit", response_class=HTMLResponse)
def caldav_account_edit(account_id: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    accounts = _load_accounts(db)
    account = _account_by_id(accounts, account_id)
    if not account:
        return RedirectResponse("/system/settings/caldav/accounts?message=Konto%20nicht%20gefunden", status_code=303)
    return templates.TemplateResponse("system_caldav_accounts.html", {"request": request, "user": user, "accounts": accounts, "settings": settings_dict(db), "message": request.query_params.get("message", ""), "calendars": [], "edit_account": account, "sync_log": _load_sync_log(db), "holiday_count": db.query(Holiday).filter(Holiday.active == True).count(), "all_holiday_count": db.query(Holiday).count()})


@router.post("/system/settings/caldav/global-save", response_class=HTMLResponse)
def caldav_global_settings_save(
    request: Request,
    absence_calendar_name: str = Form("Abwesenheit"),
    absence_calendar_username: str = Form(""),
    absence_calendar_password: str = Form(""),
    absence_calendar_auth_enabled: str = Form("0"),
    holiday_ics_import_enabled: str = Form("0"),
    holiday_ics_expiry_warning_enabled: str = Form("0"),
    holiday_ics_warn_days: int = Form(45),
    caldav_holidays_affect_target_hours: str = Form("0"),
    caldav_half_day_factor: str = Form("0.5"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    clean_absence_name = (absence_calendar_name or "Abwesenheit").strip() or "Abwesenheit"
    clean_absence_user = (absence_calendar_username or "").strip()
    set_setting(db, "absence_calendar_name", clean_absence_name)
    set_setting(db, "absence_calendar_slug", _absence_calendar_slug(clean_absence_name))
    set_setting(db, "absence_calendar_username", clean_absence_user)
    if absence_calendar_password:
        set_setting(db, "absence_calendar_password", absence_calendar_password)
    # Wenn Benutzer/Passwort gepflegt sind, wird der Schutz automatisch aktiviert.
    auth_should_be_enabled = _bool(absence_calendar_auth_enabled) or bool(clean_absence_user and (absence_calendar_password or settings_dict(db).get("absence_calendar_password", "")))
    set_setting(db, "absence_calendar_auth_enabled", "1" if auth_should_be_enabled else "0")
    set_setting(db, "holiday_ics_import_enabled", "1" if _bool(holiday_ics_import_enabled) else "0")
    set_setting(db, "holiday_ics_expiry_warning_enabled", "1" if _bool(holiday_ics_expiry_warning_enabled) else "0")
    try:
        warn_days = max(1, min(365, int(holiday_ics_warn_days or 45)))
    except Exception:
        warn_days = 45
    set_setting(db, "holiday_ics_warn_days", str(warn_days))
    set_setting(db, "caldav_holidays_affect_target_hours", "true" if _bool(caldav_holidays_affect_target_hours) else "false")
    set_setting(db, "caldav_half_day_factor", (caldav_half_day_factor or "0.5").strip() or "0.5")
    db.commit()
    try:
        log_action(db, user.employee_number, "caldav_global_settings_saved", "settings", "caldav", "Kalender-IN/OUT-Einstellungen gespeichert")
    except Exception:
        pass
    return RedirectResponse("/system/settings/caldav/accounts?message=Kalender-Einstellungen%20gespeichert", status_code=303)


@router.post("/system/settings/caldav/save", response_class=HTMLResponse)
def caldav_account_save(
    request: Request,
    account_id: str = Form(""),
    name: str = Form(""),
    server_url: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
    calendar_url: str = Form(""),
    calendar_name: str = Form(""),
    purpose: str = Form("holidays"),
    interval: str = Form("daily"),
    enabled: str = Form("0"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    accounts = _load_accounts(db)
    account = _account_by_id(accounts, account_id) if account_id else None
    if not account:
        account = {"id": str(uuid4()), "created_at": datetime.now().isoformat(timespec="seconds")}
        accounts.append(account)
    account["name"] = (name or "CalDAV-Konto").strip() or "CalDAV-Konto"
    account["server_url"] = (server_url or "").strip()
    account["username"] = (username or "").strip()
    if not account["server_url"]:
        return RedirectResponse("/system/settings/caldav/accounts?message=Server-URL%20fehlt", status_code=303)
    if password:
        account["password"] = password
    account["calendar_url"] = (calendar_url or "").strip()
    account["calendar_name"] = (calendar_name or "").strip()
    account["purpose"] = (purpose or "holidays").strip()
    account["interval"] = (interval or "daily").strip()
    account["enabled"] = _bool(enabled)
    account["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_accounts(db, accounts)
    try:
        log_action(db, user.employee_number, "caldav_account_saved", "settings", account["id"], account["name"])
    except Exception:
        pass
    return RedirectResponse("/system/settings/caldav/accounts?message=CalDAV-Konto%20gespeichert", status_code=303)


@router.post("/system/settings/caldav/test", response_class=HTMLResponse)
def caldav_account_test(
    request: Request,
    account_id: str = Form(""),
    name: str = Form(""),
    server_url: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
    calendar_url: str = Form(""),
    calendar_name: str = Form(""),
    purpose: str = Form("holidays"),
    interval: str = Form("daily"),
    enabled: str = Form("0"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    accounts = _load_accounts(db)
    temp = {"id": account_id or "new", "name": name, "server_url": server_url, "username": username, "password": password, "calendar_url": calendar_url, "calendar_name": calendar_name, "purpose": purpose, "interval": interval, "enabled": _bool(enabled)}
    if account_id:
        existing = _account_by_id(accounts, account_id)
        if existing and not password:
            temp["password"] = existing.get("password", "")
    try:
        calendars = _list_calendars(temp)
        message = f"Verbindung erfolgreich. {len(calendars)} Kalender gefunden."
    except Exception as exc:
        calendars = []
        message = f"Verbindung fehlgeschlagen: {exc}"
    return templates.TemplateResponse("system_caldav_accounts.html", {"request": request, "user": user, "accounts": accounts, "settings": settings_dict(db), "message": message, "calendars": calendars, "edit_account": temp, "sync_log": _load_sync_log(db), "holiday_count": db.query(Holiday).filter(Holiday.active == True).count(), "all_holiday_count": db.query(Holiday).count()})


@router.post("/system/settings/caldav/delete", response_class=HTMLResponse)
def caldav_account_delete(request: Request, account_id: str = Form(""), db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    accounts = [a for a in _load_accounts(db) if str(a.get("id")) != str(account_id)]
    _save_accounts(db, accounts)
    try:
        log_action(db, user.employee_number, "caldav_account_deleted", "settings", account_id, "CalDAV-Konto gelöscht")
    except Exception:
        pass
    return RedirectResponse("/system/settings/caldav/accounts?message=CalDAV-Konto%20gelöscht", status_code=303)


@router.post("/system/settings/caldav/sync", response_class=HTMLResponse)
def caldav_account_sync(request: Request, account_id: str = Form(""), year: int = Form(0), db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    accounts = _load_accounts(db)
    account = _account_by_id(accounts, account_id)
    if not account:
        return RedirectResponse("/system/settings/caldav/accounts?message=Konto%20nicht%20gefunden", status_code=303)
    try:
        count = _import_holidays_for_account(db, account, year or datetime.now().year)
        _save_accounts(db, accounts)
        message = f"Synchronisation erfolgreich: {count} neue Feiertage importiert."
        try:
            log_action(db, user.employee_number, "caldav_account_synced", "holidays", account_id, message)
        except Exception:
            pass
    except Exception as exc:
        account["last_status"] = f"Fehler: {exc}"
        _save_accounts(db, accounts)
        message = f"Synchronisation fehlgeschlagen: {exc}"
    return RedirectResponse("/system/settings/caldav/accounts?message=" + quote(message), status_code=303)


@router.post("/system/settings/caldav/sync-all", response_class=HTMLResponse)
def caldav_account_sync_all(request: Request, year: int = Form(0), db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    accounts = _load_accounts(db)
    sync_year = year or datetime.now().year
    total = 0
    done = 0
    errors = 0
    for account in accounts:
        if not _bool(account.get("enabled")):
            continue
        if str(account.get("purpose") or "holidays") not in {"holidays", "company"}:
            continue
        done += 1
        try:
            count = _import_holidays_for_account(db, account, sync_year)
            total += count
            _append_sync_log(db, account, "OK", account.get("last_status") or f"{count} Feiertage importiert")
        except Exception as exc:
            errors += 1
            account["last_sync"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            account["last_status"] = f"Fehler: {exc}"
            _append_sync_log(db, account, "FEHLER", str(exc))
    _save_accounts(db, accounts)
    message = f"{done} aktive Kalender synchronisiert, {total} neue Feiertage importiert"
    if errors:
        message += f", {errors} Fehler"
    try:
        log_action(db, user.employee_number, "caldav_accounts_sync_all", "holidays", str(sync_year), message)
    except Exception:
        pass
    return RedirectResponse("/system/settings/caldav/accounts?message=" + quote(message), status_code=303)


@router.post("/system/settings/caldav/delete-holidays", response_class=HTMLResponse)
def caldav_delete_all_holidays(request: Request, db: Session = Depends(get_db)):
    """Löscht alle importierten Feiertage für eine saubere Neukonfiguration.

    5.2.18: Feiertagskalender ist ein Import in die Arbeitszeitberechnung.
    Dieser Button entfernt nur Feiertage, nicht Abwesenheiten oder externe Kalenderfeeds.
    """
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    count = db.query(Holiday).count()
    db.query(Holiday).delete(synchronize_session=False)
    set_setting(db, "holiday_ics_last_import", "")
    set_setting(db, "holiday_ics_last_status", f"{count} Feiertage gelöscht; Neukonfiguration möglich")
    _append_sync_log(db, None, "OK", f"Alle Feiertage gelöscht: {count}")
    db.commit()
    try:
        log_action(db, user.employee_number, "holidays_deleted_all", "holidays", "all", f"{count} Feiertage gelöscht")
    except Exception:
        pass
    return RedirectResponse("/system/settings/caldav/accounts?message=" + quote(f"{count} Feiertage gelöscht. Der Feiertagsimport kann neu konfiguriert werden."), status_code=303)


@router.post("/system/settings/caldav/import-holidays-ics-accounts", response_class=HTMLResponse)
async def caldav_import_holidays_ics_accounts(
    request: Request,
    ics_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Importiert Feiertage aus einer iCal-Datei direkt aus der neuen Kalender-IN-Seite."""
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    settings = settings_dict(db)
    if settings.get("holiday_ics_import_enabled", "1") not in ["1", "true", "on"]:
        return RedirectResponse("/system/settings/caldav/accounts?message=" + quote("ICS-Feiertagsimport ist deaktiviert."), status_code=303)
    filename = (ics_file.filename or "feiertage.ics").lower()
    if not filename.endswith(".ics"):
        return RedirectResponse("/system/settings/caldav/accounts?message=" + quote("Bitte eine .ics-Datei auswählen."), status_code=303)
    try:
        content = await ics_file.read()
        from app.routes.vacation import import_holidays_from_ics_content
        count, latest = import_holidays_from_ics_content(db, content, source_name="ICS", actor=user.employee_number)
        msg = f"{count} Feiertage aus iCal importiert."
        if latest:
            msg += f" Letzter Termin: {latest}."
        _append_sync_log(db, {"name": "iCal-Feiertagsdatei"}, "OK", msg)
        try:
            log_action(db, user.employee_number, "holiday_ics_imported", "holidays", filename, msg)
        except Exception:
            pass
        db.commit()
        return RedirectResponse("/system/settings/caldav/accounts?message=" + quote(msg), status_code=303)
    except Exception as exc:
        _append_sync_log(db, {"name": "iCal-Feiertagsdatei"}, "FEHLER", str(exc))
        db.commit()
        return RedirectResponse("/system/settings/caldav/accounts?message=" + quote(f"iCal-Import fehlgeschlagen: {exc}"), status_code=303)
