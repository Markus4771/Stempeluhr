from .common import *

router = APIRouter()

@router.get("/system/settings/security", response_class=HTMLResponse)
def system_settings_security(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_settings_security.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "saved": request.query_params.get("saved") == "1",
        "message": request.query_params.get("message", ""),
        "error": request.query_params.get("error", ""),
    })


@router.post("/system/settings/security", response_class=HTMLResponse)
def system_settings_security_save(
    request: Request,
    security_network_filter_enabled: str = Form("0"),
    security_allowed_networks: str = Form(""),
    security_admin_network_filter_enabled: str = Form("0"),
    security_admin_allowed_networks: str = Form(""),
    security_api_network_filter_enabled: str = Form("0"),
    security_api_allowed_networks: str = Form(""),
    security_force_https: str = Form("0"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    from app.services.network_security import validate_cidr_text

    for label, raw in [
        ("Erlaubte Netzwerke", security_allowed_networks),
        ("Admin-Netze", security_admin_allowed_networks),
        ("API-Netze", security_api_allowed_networks),
    ]:
        ok, err = validate_cidr_text(raw)
        if not ok:
            return RedirectResponse(
                "/system/settings/security?error=" + quote(f"{label}: ungültiges Netzwerk - {err}"),
                status_code=303,
            )

    def flag(value: str) -> str:
        return "true" if str(value).lower() in ["1", "true", "on", "ja", "yes"] else "false"

    old = service_settings_dict(db)
    service_set_setting(db, "security_network_filter_enabled", flag(security_network_filter_enabled))
    service_set_setting(db, "security_allowed_networks", (security_allowed_networks or "").strip())
    service_set_setting(db, "security_admin_network_filter_enabled", flag(security_admin_network_filter_enabled))
    service_set_setting(db, "security_admin_allowed_networks", (security_admin_allowed_networks or "").strip())
    service_set_setting(db, "security_api_network_filter_enabled", flag(security_api_network_filter_enabled))
    service_set_setting(db, "security_api_allowed_networks", (security_api_allowed_networks or "").strip())
    service_set_setting(db, "security_force_https", flag(security_force_https))
    db.commit()

    try:
        details = (
            f"Netzwerkfilter: {old.get('security_network_filter_enabled', 'false')} -> {flag(security_network_filter_enabled)}; "
            f"HTTPS erzwingen: {old.get('security_force_https', 'false')} -> {flag(security_force_https)}"
        )
        log_action(db, user.employee_number, "security_network_settings_saved", "settings", "security", details)
    except Exception:
        pass

    return RedirectResponse("/system/settings/security?saved=1&message=Sicherheitseinstellungen%20gespeichert.", status_code=303)

@router.get("/system/settings/general", response_class=HTMLResponse)
def system_settings_general(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    ensure_employee_number_length_setting(db)
    ensure_break_settings(db)
    ensure_module_visibility_settings(db)
    if service_get_setting(db, "booking_auto_delay_seconds", None) is None:
        service_set_setting(db, "booking_auto_delay_seconds", "3")
    if service_get_setting(db, "booking_status_display_seconds", None) is None:
        service_set_setting(db, "booking_status_display_seconds", "5")
    if service_get_setting(db, "absence_calendar_name", None) is None:
        service_set_setting(db, "absence_calendar_name", "Abwesenheit")
    if service_get_setting(db, "holiday_ics_import_enabled", None) is None:
        service_set_setting(db, "holiday_ics_import_enabled", "1")
    if service_get_setting(db, "holiday_ics_expiry_warning_enabled", None) is None:
        service_set_setting(db, "holiday_ics_expiry_warning_enabled", "1")
    if service_get_setting(db, "holiday_ics_warn_days", None) is None:
        service_set_setting(db, "holiday_ics_warn_days", "45")
    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_settings_general.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "saved": request.query_params.get("saved") == "1",
        "message": request.query_params.get("message", ""),
        "error": request.query_params.get("error", ""),
    })


@router.post("/system/settings/general", response_class=HTMLResponse)
def system_settings_general_save(
    request: Request,
    company_name: str = Form(""),
    correction_days_back: int = Form(14),
    employee_number_length: int = Form(4),
    auto_break_enabled: str = Form("0"),
    booking_auto_delay_seconds: int = Form(3),
    booking_status_display_seconds: int = Form(5),
    absence_calendar_name: str = Form("Abwesenheit"),
    holiday_ics_import_enabled: str = Form("0"),
    holiday_ics_expiry_warning_enabled: str = Form("0"),
    holiday_ics_warn_days: int = Form(45),
    module_settings_departments_enabled: str = Form("0"),
    module_settings_plausibility_enabled: str = Form("0"),
    module_settings_breaks_enabled: str = Form("0"),
    module_settings_backup_enabled: str = Form("0"),
    module_settings_email_enabled: str = Form("0"),
    module_settings_caldav_enabled: str = Form("0"),
    module_settings_api_enabled: str = Form("0"),
    module_settings_terminals_enabled: str = Form("0"),
    module_settings_time_enabled: str = Form("0"),
    module_settings_https_enabled: str = Form("0"),
    module_settings_security_enabled: str = Form("0"),
    module_settings_offboarding_enabled: str = Form("0"),
    module_settings_dsgvo_enabled: str = Form("0"),
    fixed_admin_password: str = Form(""),
    logo_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    def upsert_setting(key: str, value: str):
        service_set_setting(db, key, value)

    try:
        correction_days_back = int(correction_days_back or 14)
    except Exception:
        correction_days_back = 14
    correction_days_back = max(0, min(correction_days_back, 365))

    try:
        employee_number_length = int(employee_number_length or 4)
    except Exception:
        employee_number_length = 4
    employee_number_length = clamp_employee_number_length(employee_number_length)

    upsert_setting("company_name", (company_name or "").strip())
    upsert_setting("correction_days_back", str(correction_days_back))
    try:
        booking_auto_delay_seconds = int(booking_auto_delay_seconds or 3)
    except Exception:
        booking_auto_delay_seconds = 3
    booking_auto_delay_seconds = max(1, min(booking_auto_delay_seconds, 30))

    try:
        booking_status_display_seconds = int(booking_status_display_seconds or 5)
    except Exception:
        booking_status_display_seconds = 5
    booking_status_display_seconds = max(1, min(booking_status_display_seconds, 60))

    upsert_setting("employee_number_length", str(employee_number_length))
    upsert_setting("auto_break_enabled", "1" if str(auto_break_enabled).lower() in ["1", "true", "on", "ja"] else "0")
    upsert_setting("booking_auto_delay_seconds", str(booking_auto_delay_seconds))
    upsert_setting("booking_status_display_seconds", str(booking_status_display_seconds))
    upsert_setting("absence_calendar_name", (absence_calendar_name or "Abwesenheit").strip() or "Abwesenheit")
    try:
        holiday_ics_warn_days = int(holiday_ics_warn_days or 45)
    except Exception:
        holiday_ics_warn_days = 45
    holiday_ics_warn_days = max(1, min(holiday_ics_warn_days, 365))
    upsert_setting("holiday_ics_import_enabled", "1" if holiday_ics_import_enabled == "1" else "0")
    upsert_setting("holiday_ics_expiry_warning_enabled", "1" if holiday_ics_expiry_warning_enabled == "1" else "0")
    upsert_setting("holiday_ics_warn_days", str(holiday_ics_warn_days))

    def module_flag(value: str) -> str:
        return "1" if str(value).lower() in ["1", "true", "on", "ja", "yes"] else "0"

    # Allgemeine Einstellungen bleiben immer aktiv; nur die weiteren Untermenüs sind schaltbar.
    module_values = {
        "module_settings_departments_enabled": module_settings_departments_enabled,
        "module_settings_plausibility_enabled": module_settings_plausibility_enabled,
        "module_settings_breaks_enabled": module_settings_breaks_enabled,
        "module_settings_backup_enabled": module_settings_backup_enabled,
        "module_settings_email_enabled": module_settings_email_enabled,
        "module_settings_caldav_enabled": module_settings_caldav_enabled,
        "module_settings_api_enabled": module_settings_api_enabled,
        "module_settings_terminals_enabled": module_settings_terminals_enabled,
        "module_settings_time_enabled": module_settings_time_enabled,
        "module_settings_https_enabled": module_settings_https_enabled,
        "module_settings_security_enabled": module_settings_security_enabled,
        "module_settings_offboarding_enabled": module_settings_offboarding_enabled,
        "module_settings_dsgvo_enabled": module_settings_dsgvo_enabled,
    }
    for key, value in module_values.items():
        upsert_setting(key, module_flag(value))

    # Optional: Firmenlogo speichern, wenn eine Datei ausgewählt wurde.
    try:
        if logo_file and logo_file.filename:
            suffix = Path(logo_file.filename).suffix.lower()
            if suffix in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]:
                logo_dir = UPLOAD_DIR
                logo_dir.mkdir(parents=True, exist_ok=True)
                target = logo_dir / f"company_logo{suffix}"
                with target.open("wb") as f:
                    shutil.copyfileobj(logo_file.file, f)
                upsert_setting("logo_path", f"/static/uploads/{target.name}")
    except Exception:
        pass

    # Optional: Passwort des festen Notfall-Admins ändern.
    if fixed_admin_password:
        fixed_admin = db.query(Employee).filter(Employee.employee_number == "admin").first()
        if fixed_admin:
            fixed_admin.password_hash = hash_password(fixed_admin_password)

    db.commit()

    try:
        log_action(db, user.employee_number, "settings_general_saved", "settings", "general", f"Mitarbeiternummer Stellen: {employee_number_length}")
    except Exception:
        pass

    return RedirectResponse(url="/system/settings/general?saved=1&message=Allgemeine%20Einstellungen%20gespeichert.", status_code=303)


@router.post("/system/settings/general/reset-worktimes", response_class=HTMLResponse)
def system_settings_general_reset_worktimes(
    request: Request,
    confirm_password: str = Form(""),
    confirm_text: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    if not verify_password(confirm_password or "", user.password_hash or ""):
        return RedirectResponse("/system/settings/general?error=" + quote("Passwort falsch. Arbeitszeiten wurden nicht zurückgesetzt."), status_code=303)

    if (confirm_text or "").strip() != "ARBEITSZEITEN ZURÜCKSETZEN":
        return RedirectResponse("/system/settings/general?error=" + quote("Bestätigungstext falsch. Bitte exakt ARBEITSZEITEN ZURÜCKSETZEN eingeben."), status_code=303)

    counts = {}
    for model, name in [
        (PlausibilityIssue, "Plausibilitätsfälle"),
        (Correction, "Korrekturen"),
        (TimeEntry, "Buchungen"),
    ]:
        try:
            counts[name] = db.query(model).delete(synchronize_session=False)
        except Exception:
            counts[name] = "Fehler"

    try:
        from app.models import WorkTimeAccount
        counts["Arbeitszeitkonto"] = db.query(WorkTimeAccount).delete(synchronize_session=False)
    except Exception:
        pass

    db.add(AuditLog(
        actor=user.employee_number,
        action="worktimes_reset",
        entity="system",
        entity_id="new_start",
        details="Arbeitszeiten zurückgesetzt: " + ", ".join([f"{k}={v}" for k, v in counts.items()]),
    ))
    db.commit()
    return RedirectResponse("/system/settings/general?saved=1&message=" + quote("Arbeitszeiten wurden auf Neuanfang zurückgesetzt. Mitarbeiter, Einstellungen und Abwesenheiten bleiben erhalten."), status_code=303)


# ---------------------------------------------------------------------------
# Offboarding
# ---------------------------------------------------------------------------


@router.post("/system/settings/general/delete-test-data", response_class=HTMLResponse)
def system_settings_general_delete_test_data(
    request: Request,
    confirm_password: str = Form(""),
    confirm_text: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    # Schutz gegen versehentliches Löschen: Admin-Passwort und Bestätigungstext sind Pflicht.
    if not verify_password(confirm_password or "", user.password_hash or ""):
        return RedirectResponse("/system/settings/general?error=" + quote("Passwort falsch. Daten wurden nicht gelöscht."), status_code=303)

    if (confirm_text or "").strip() != "TESTDATEN LÖSCHEN":
        return RedirectResponse("/system/settings/general?error=" + quote("Bestätigungstext falsch. Bitte exakt TESTDATEN LÖSCHEN eingeben."), status_code=303)

    counts = {}
    # Test-/Bewegungsdaten löschen, aber Benutzer, Rollen, Einstellungen und Systemkonfiguration erhalten.
    for model, name in [
        (PlausibilityIssue, "Plausibilität"),
        (Correction, "Korrekturen"),
        (TimeEntry, "Buchungen"),
        (VacationRequest, "Abwesenheiten"),
        (Holiday, "Feiertage"),
    ]:
        try:
            counts[name] = db.query(model).delete(synchronize_session=False)
        except Exception:
            counts[name] = "Fehler"

    # Arbeitszeitkonten optional löschen, wenn Modell vorhanden/importiert ist.
    try:
        from app.models import WorkTimeAccount
        counts["Arbeitszeitkonto"] = db.query(WorkTimeAccount).delete(synchronize_session=False)
    except Exception:
        pass

    db.add(AuditLog(
        actor=user.employee_number,
        action="test_data_deleted",
        entity="system",
        entity_id="test_phase",
        details="Testdaten gelöscht: " + ", ".join([f"{k}={v}" for k, v in counts.items()]),
    ))
    db.commit()
    return RedirectResponse("/system/settings/general?saved=1&message=" + quote("Testdaten wurden gelöscht. Mitarbeiter, Rollen und Einstellungen bleiben erhalten."), status_code=303)


@router.get("/system/settings/breaks", response_class=HTMLResponse)
def system_settings_breaks(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_break_settings(db)
    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_settings_breaks.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "saved": request.query_params.get("saved") == "1",
    })


@router.post("/system/settings/breaks", response_class=HTMLResponse)
def system_settings_breaks_save(
    request: Request,
    auto_break_enabled: str = Form("0"),
    auto_break_threshold_1_hours: float = Form(6),
    auto_break_deduct_1_minutes: float = Form(30),
    auto_break_threshold_2_hours: float = Form(9),
    auto_break_deduct_2_minutes: float = Form(45),
    auto_break_only_missing_break: str = Form("0"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    def clamp_float(value, default, minimum, maximum):
        try:
            value = float(value)
        except Exception:
            value = default
        return max(minimum, min(maximum, value))

    service_set_setting(db, "auto_break_enabled", "1" if str(auto_break_enabled).lower() in ["1", "true", "on", "ja"] else "0")
    service_set_setting(db, "auto_break_threshold_1_hours", str(clamp_float(auto_break_threshold_1_hours, 6, 0, 24)))
    service_set_setting(db, "auto_break_deduct_1_minutes", str(clamp_float(auto_break_deduct_1_minutes, 30, 0, 240)))
    service_set_setting(db, "auto_break_threshold_2_hours", str(clamp_float(auto_break_threshold_2_hours, 9, 0, 24)))
    service_set_setting(db, "auto_break_deduct_2_minutes", str(clamp_float(auto_break_deduct_2_minutes, 45, 0, 240)))
    service_set_setting(db, "auto_break_only_missing_break", "1" if str(auto_break_only_missing_break).lower() in ["1", "true", "on", "ja"] else "0")
    db.commit()

    try:
        log_action(db, user.employee_number, "settings_breaks_saved", "settings", "breaks", "Pausenregelung gespeichert")
    except Exception:
        pass

    return RedirectResponse("/system/settings/breaks?saved=1", status_code=303)


@router.get("/system")
def system_redirect(request: Request):
    return RedirectResponse("/system/settings", status_code=303)
