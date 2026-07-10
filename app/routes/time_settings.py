from .common import *

router = APIRouter()

def ensure_time_settings(db: Session):
    defaults = {
        "time_ntp_enabled": "1",
        "time_ntp_server": "de.pool.ntp.org",
        "time_ntp_port": "123",
        "time_sync_interval_minutes": "1440",
        "time_timezone": "Europe/Berlin",
        "time_sync_terminals": "0",
        "terminal_time_max_offset_seconds": "5",
        "time_allow_manual": "0",
        "time_last_sync": "",
        "time_last_test": "",
    }
    changed = False
    for key, value in defaults.items():
        if service_get_setting(db, key, None) is None:
            service_set_setting(db, key, value)
            changed = True
    if changed:
        db.commit()


def _bool_setting_value(value: str) -> str:
    return "1" if str(value or "").lower() in ["1", "true", "on", "ja", "yes"] else "0"


def _clamp_int(value, default: int, min_value: int, max_value: int) -> int:
    try:
        ivalue = int(value)
    except Exception:
        ivalue = default
    return max(min_value, min(ivalue, max_value))


def _ntp_query(server: str, port: int = 123, timeout: float = 4.0) -> tuple[datetime, float]:
    """Fragt einen NTP-Server direkt ab. Gibt UTC-Zeit und Offset zur lokalen Uhr zurück."""
    server = (server or "").strip()
    if not server:
        raise ValueError("Kein NTP-Server eingetragen")
    packet = b"\x1b" + 47 * b"\0"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.settimeout(timeout)
        before = datetime.utcnow()
        client.sendto(packet, (server, int(port)))
        data, _ = client.recvfrom(48)
        after = datetime.utcnow()
    if len(data) < 48:
        raise ValueError("Ungültige NTP-Antwort")
    seconds = struct.unpack("!12I", data)[10]
    fraction = struct.unpack("!12I", data)[11]
    ntp_time = seconds - 2208988800 + fraction / 2**32
    ntp_dt = datetime.utcfromtimestamp(ntp_time)
    local_mid = before + (after - before) / 2
    offset = (ntp_dt - local_mid).total_seconds()
    return ntp_dt, offset


def _system_time_status() -> str:
    try:
        result = subprocess.run(["timedatectl", "show", "--property=Timezone", "--property=NTPSynchronized", "--property=SystemClockSynchronized"], capture_output=True, text=True, timeout=5)
        return (result.stdout or "").strip()
    except Exception as exc:
        return f"timedatectl nicht verfügbar: {exc}"


@router.get("/system/settings", response_class=HTMLResponse)
def system_settings(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_time_settings(db)
    # Lazy import avoids circular imports after route modularisation.
    from .https_settings import ensure_https_settings
    ensure_https_settings(db)
    ensure_module_visibility_settings(db)
    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_settings.html", {"request": request, "user": user, "settings": settings, "app_version": get_app_version()})


@router.get("/me/profile", response_class=HTMLResponse)
def my_profile(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not getattr(user, "can_self_manage", False):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Die Selbstverwaltung ist für deinen Benutzer nicht freigegeben.", "return_to": "/"})
    return templates.TemplateResponse("employee_self_manage.html", {"request": request, "user": user, "employee": user, "saved": False})


@router.post("/me/profile", response_class=HTMLResponse)
def my_profile_save(request: Request, email: str = Form(""), phone: str = Form(""), password: str = Form(""), db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not getattr(user, "can_self_manage", False):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Die Selbstverwaltung ist für deinen Benutzer nicht freigegeben.", "return_to": "/"})
    emp = db.query(Employee).filter(Employee.id == user.id).first()
    if not emp:
        return RedirectResponse("/logout", status_code=303)
    emp.email = (email or "").strip() or None
    emp.phone = (phone or "").strip() or None
    if password:
        emp.password_hash = hash_password(password)
    emp.updated_at = datetime.now()
    db.commit()
    log_action(db, emp.employee_number, "employee_self_manage_updated", "employees", str(emp.id), "Eigene Stammdaten aktualisiert")
    return templates.TemplateResponse("employee_self_manage.html", {"request": request, "user": emp, "employee": emp, "saved": True})


@router.get("/system/settings/time", response_class=HTMLResponse)
def system_settings_time(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_time_settings(db)
    settings = service_settings_dict(db)
    now = datetime.now()
    return templates.TemplateResponse("system_settings_time.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "current_time": now.strftime("%d.%m.%Y %H:%M:%S"),
        "today": now.strftime("%Y-%m-%d"),
        "now_time": now.strftime("%H:%M:%S"),
        "message": request.query_params.get("message", ""),
        "system_time_status": _system_time_status(),
    })


@router.post("/system/settings/time/save", response_class=HTMLResponse)
def system_settings_time_save(
    request: Request,
    time_ntp_enabled: str = Form("0"),
    time_ntp_server: str = Form("de.pool.ntp.org"),
    time_ntp_port: int = Form(123),
    time_sync_interval_minutes: int = Form(1440),
    time_timezone: str = Form("Europe/Berlin"),
    time_sync_terminals: str = Form("0"),
    terminal_time_max_offset_seconds: int = Form(5),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_time_settings(db)
    old_server = service_get_setting(db, "time_ntp_server", "")
    port = _clamp_int(time_ntp_port, 123, 1, 65535)
    interval = _clamp_int(time_sync_interval_minutes, 1440, 5, 10080)
    timezone = (time_timezone or "Europe/Berlin").strip() or "Europe/Berlin"
    server = (time_ntp_server or "de.pool.ntp.org").strip() or "de.pool.ntp.org"
    service_set_setting(db, "time_ntp_enabled", _bool_setting_value(time_ntp_enabled))
    service_set_setting(db, "time_ntp_server", server)
    service_set_setting(db, "time_ntp_port", str(port))
    service_set_setting(db, "time_sync_interval_minutes", str(interval))
    service_set_setting(db, "time_timezone", timezone)
    service_set_setting(db, "time_sync_terminals", _bool_setting_value(time_sync_terminals))
    service_set_setting(db, "terminal_time_max_offset_seconds", str(_clamp_int(terminal_time_max_offset_seconds, 5, 1, 300)))
    db.commit()
    try:
        log_action(db, user.employee_number, "time_settings_saved", "settings", "time", f"NTP-Server: {old_server} -> {server}, Intervall: {interval} min")
    except Exception:
        pass
    return RedirectResponse("/system/settings/time?message=Uhrzeit-Einstellungen%20gespeichert.", status_code=303)


@router.post("/system/settings/time/test", response_class=HTMLResponse)
def system_settings_time_test(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_time_settings(db)
    server = service_get_setting(db, "time_ntp_server", "de.pool.ntp.org")
    port = _clamp_int(service_get_setting(db, "time_ntp_port", "123"), 123, 1, 65535)
    try:
        ntp_dt, offset = _ntp_query(server, port)
        message = f"NTP-Test erfolgreich: {server}:{port}, UTC {ntp_dt.strftime('%Y-%m-%d %H:%M:%S')}, Abweichung {offset:+.3f} Sekunden"
        service_set_setting(db, "time_last_test", message)
        db.commit()
    except Exception as exc:
        message = f"NTP-Test fehlgeschlagen: {exc}"
        service_set_setting(db, "time_last_test", message)
        db.commit()
    return RedirectResponse("/system/settings/time?message=" + quote(message), status_code=303)


@router.post("/system/settings/time/sync", response_class=HTMLResponse)
def system_settings_time_sync(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_time_settings(db)
    server = service_get_setting(db, "time_ntp_server", "de.pool.ntp.org")
    port = _clamp_int(service_get_setting(db, "time_ntp_port", "123"), 123, 1, 65535)
    try:
        ntp_dt, offset = _ntp_query(server, port)
        # Ohne sudo-Rechte kann die Webanwendung die Systemzeit oft nicht setzen.
        # Wir protokollieren den erfolgreichen Abruf und nutzen timedatectl nur, wenn erlaubt.
        service_set_setting(db, "time_last_sync", f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')} - Server {server}, Abweichung {offset:+.3f} Sekunden")
        db.commit()
        try:
            log_action(db, user.employee_number, "time_ntp_sync_checked", "settings", "time", f"{server}:{port}, Offset {offset:+.3f}s")
        except Exception:
            pass
        message = f"NTP-Zeit erfolgreich abgefragt. Abweichung {offset:+.3f} Sekunden. Systemzeit wird durch den Betriebssystem-NTP-Dienst gesetzt."
    except Exception as exc:
        message = f"NTP-Synchronisation fehlgeschlagen: {exc}"
    return RedirectResponse("/system/settings/time?message=" + quote(message), status_code=303)


@router.post("/system/settings/time/manual", response_class=HTMLResponse)
def system_settings_time_manual(
    request: Request,
    time_allow_manual: str = Form("0"),
    manual_date: str = Form(""),
    manual_time: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_time_settings(db)
    allow = _bool_setting_value(time_allow_manual)
    service_set_setting(db, "time_allow_manual", allow)
    db.commit()
    if allow != "1":
        return RedirectResponse("/system/settings/time?message=Manuelle%20Zeitkorrektur%20ist%20nicht%20aktiviert.", status_code=303)
    try:
        target = datetime.strptime(f"{manual_date} {manual_time}", "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            target = datetime.strptime(f"{manual_date} {manual_time}", "%Y-%m-%d %H:%M")
        except Exception:
            return RedirectResponse("/system/settings/time?message=Ungültiges%20Datum%20oder%20ungültige%20Uhrzeit.", status_code=303)
    cmd = ["sudo", "timedatectl", "set-time", target.strftime("%Y-%m-%d %H:%M:%S")]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            message = "Systemzeit wurde manuell gesetzt."
            log_details = f"Neue Zeit: {target.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            message = "Zeit konnte nicht gesetzt werden. Sudo-/timedatectl-Rechte fehlen vermutlich."
            log_details = (result.stderr or result.stdout or "").strip()[:300]
    except Exception as exc:
        message = f"Zeit konnte nicht gesetzt werden: {exc}"
        log_details = str(exc)
    try:
        log_action(db, user.employee_number, "time_manual_set", "settings", "time", log_details)
    except Exception:
        pass
    return RedirectResponse("/system/settings/time?message=" + quote(message), status_code=303)



# ---------------------------------------------------------------------------
# HTTPS / Zertifikate
# ---------------------------------------------------------------------------
