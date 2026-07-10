from .common import *

router = APIRouter()

@router.get("/corrections", response_class=HTMLResponse)
def corrections(
    request: Request,
    employee_id: int = 0,
    entry_type: str = "",
    method: str = "",
    date_from: str = "",
    date_to: str = "",
    show_deleted: bool = False,
    db: Session = Depends(get_db)
):
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect

    settings = service_settings_dict(db)

    try:
        correction_days_back = int(settings.get("correction_days_back", "14"))
    except Exception:
        correction_days_back = 14

    correction_days_back = max(0, min(365, correction_days_back))
    cutoff = datetime.now() - timedelta(days=correction_days_back)

    visible_ids = correction_visible_employee_ids(db, user)
    query = db.query(TimeEntry).filter(TimeEntry.timestamp >= cutoff, TimeEntry.employee_id.in_(visible_ids))
    if show_deleted:
        query = query.filter(TimeEntry.deleted == True)
    else:
        query = query.filter(not_deleted_filter())

    if employee_id and employee_id in visible_ids:
        query = query.filter(TimeEntry.employee_id == employee_id)

    if entry_type:
        query = query.filter(TimeEntry.entry_type == entry_type)

    if method:
        query = query.filter(TimeEntry.method == method)

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(TimeEntry.timestamp >= dt_from)
        except Exception:
            pass

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(TimeEntry.timestamp < dt_to)
        except Exception:
            pass

    entries = query.order_by(TimeEntry.timestamp.desc()).limit(500).all()

    employees = db.query(Employee).filter(Employee.active == True, Employee.id.in_(visible_ids)).order_by(Employee.last_name, Employee.first_name).all()
    corrections = db.query(Correction).order_by(Correction.changed_at.desc()).limit(100).all() if can_manage_all_corrections(user) else []

    return templates.TemplateResponse("corrections.html", {
        "request": request,
        "user": user,
        "employees": employees,
        "entries": entries,
        "corrections": corrections,
        "filters": {
            "employee_id": employee_id,
            "entry_type": entry_type,
            "method": method,
            "date_from": date_from,
            "date_to": date_to,
            "show_deleted": show_deleted
        },
        "correction_days_back": correction_days_back,
        "cutoff": cutoff
    })


@router.get("/corrections/new", response_class=HTMLResponse)
def correction_new_form(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect

    visible_ids = correction_visible_employee_ids(db, user)
    employees = db.query(Employee).filter(Employee.active == True, Employee.id.in_(visible_ids)).order_by(Employee.last_name, Employee.first_name).all()
    return templates.TemplateResponse("correction_new.html", {
        "request": request,
        "user": user,
        "employees": employees,
        "today": datetime.now().strftime("%Y-%m-%d"),
        "now_time": datetime.now().strftime("%H:%M"),
        "error": None
    })


@router.post("/corrections/new", response_class=HTMLResponse)
def correction_new_save(
    request: Request,
    employee_id: int = Form(...),
    timestamp_date: str = Form(...),
    timestamp_time: str = Form(...),
    entry_type: str = Form(...),
    method: str = Form("manual_add"),
    terminal: str = Form("Korrektur-Menü"),
    note: str = Form(""),
    reason: str = Form(...),
    db: Session = Depends(get_db)
):
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect

    visible_ids = correction_visible_employee_ids(db, user)
    employees = db.query(Employee).filter(Employee.active == True, Employee.id.in_(visible_ids)).order_by(Employee.last_name, Employee.first_name).all()

    if employee_id not in visible_ids:
        return templates.TemplateResponse("correction_new.html", {"request": request, "user": user, "employees": employees, "today": timestamp_date, "now_time": timestamp_time, "error": "Keine Berechtigung für diesen Mitarbeiter."})

    if entry_type not in VALID_ENTRY_TYPES:
        return templates.TemplateResponse("correction_new.html", {
            "request": request,
            "user": user,
            "employees": employees,
            "today": timestamp_date,
            "now_time": timestamp_time,
            "error": "Ungültiger Buchungstyp."
        })

    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.active == True).first()
    if not employee:
        return templates.TemplateResponse("correction_new.html", {
            "request": request,
            "user": user,
            "employees": employees,
            "today": timestamp_date,
            "now_time": timestamp_time,
            "error": "Mitarbeiter nicht gefunden oder nicht aktiv."
        })

    try:
        new_timestamp = datetime.strptime(f"{timestamp_date} {timestamp_time}", "%Y-%m-%d %H:%M")
    except Exception:
        return templates.TemplateResponse("correction_new.html", {
            "request": request,
            "user": user,
            "employees": employees,
            "today": timestamp_date,
            "now_time": timestamp_time,
            "error": "Datum oder Uhrzeit ist ungültig."
        })

    entry = TimeEntry(
        employee_id=employee_id,
        timestamp=new_timestamp,
        entry_type=entry_type,
        method=method or "manual_add",
        terminal=terminal or "Korrektur-Menü",
        note=note,
        corrected=True
    )
    db.add(entry)
    db.flush()

    new_value = (
        f"employee_id={employee_id}; "
        f"timestamp={new_timestamp}; "
        f"entry_type={entry_type}; "
        f"method={method or 'manual_add'}; "
        f"terminal={terminal or 'Korrektur-Menü'}; "
        f"note={note}"
    )

    correction = Correction(
        employee_id=employee_id,
        time_entry_id=entry.id,
        old_value="NEUER EINTRAG",
        new_value=new_value,
        reason=reason,
        changed_by=user.employee_number,
        status="genehmigt"
    )
    db.add(correction)
    db.commit()

    log_action(db, user.employee_number, "time_entry_added_manually", "time_entries", str(entry.id), reason)

    return templates.TemplateResponse("message.html", {
        "request": request,
        "title": "Eintrag hinzugefügt",
        "message": "Der Zeiteintrag wurde angelegt und in der Korrektur-History protokolliert.",
        "return_to": "/corrections"
    })


@router.get("/corrections/{entry_id}/history", response_class=HTMLResponse)
def correction_history(entry_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect

    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Fehler",
            "message": "Buchung nicht gefunden",
            "return_to": "/corrections"
        })

    history = db.query(Correction).filter(Correction.time_entry_id == entry_id).order_by(Correction.changed_at.desc()).all()
    return templates.TemplateResponse("correction_history.html", {
        "request": request,
        "user": user,
        "entry": entry,
        "history": history
    })


@router.get("/corrections/{entry_id}/edit", response_class=HTMLResponse)
def correction_edit_form(entry_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect

    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Fehler",
            "message": "Buchung nicht gefunden",
            "return_to": "/corrections"
        })
    if not can_correct_entry(db, user, entry):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Für diese Buchung ist keine Korrektur erlaubt.", "return_to": "/corrections"})

    settings = service_settings_dict(db)
    try:
        correction_days_back = int(settings.get("correction_days_back", "14"))
    except Exception:
        correction_days_back = 14

    cutoff = datetime.now() - timedelta(days=correction_days_back)
    if entry.timestamp < cutoff:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Korrektur nicht möglich",
            "message": f"Diese Buchung liegt außerhalb der erlaubten Korrekturfrist von {correction_days_back} Tagen.",
            "return_to": "/corrections"
        })

    visible_ids = correction_visible_employee_ids(db, user)
    employees = db.query(Employee).filter(Employee.active == True, Employee.id.in_(visible_ids)).order_by(Employee.last_name, Employee.first_name).all()

    return templates.TemplateResponse("correction_edit.html", {
        "request": request,
        "user": user,
        "entry": entry,
        "employees": employees,
        "correction_days_back": correction_days_back,
        "error": None
    })

@router.post("/corrections/{entry_id}/edit", response_class=HTMLResponse)
def correction_edit_save(
    entry_id: int,
    request: Request,
    employee_id: int = Form(...),
    timestamp_date: str = Form(...),
    timestamp_time: str = Form(...),
    entry_type: str = Form(...),
    method: str = Form("manual_correction"),
    terminal: str = Form(""),
    note: str = Form(""),
    reason: str = Form(...),
    db: Session = Depends(get_db)
):
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect

    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Fehler",
            "message": "Buchung nicht gefunden",
            "return_to": "/corrections"
        })
    if not can_correct_entry(db, user, entry):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Für diese Buchung ist keine Korrektur erlaubt.", "return_to": "/corrections"})

    settings = service_settings_dict(db)
    try:
        correction_days_back = int(settings.get("correction_days_back", "14"))
    except Exception:
        correction_days_back = 14

    cutoff = datetime.now() - timedelta(days=correction_days_back)
    if entry.timestamp < cutoff:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Korrektur nicht möglich",
            "message": f"Diese Buchung liegt außerhalb der erlaubten Korrekturfrist von {correction_days_back} Tagen.",
            "return_to": "/corrections"
        })

    visible_ids = correction_visible_employee_ids(db, user)
    if employee_id not in visible_ids:
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Korrektur auf diesen Mitarbeiter ist nicht erlaubt.", "return_to": "/corrections"})

    if entry_type not in VALID_ENTRY_TYPES:
        employees = db.query(Employee).filter(Employee.active == True, Employee.id.in_(visible_ids)).order_by(Employee.last_name, Employee.first_name).all()
        return templates.TemplateResponse("correction_edit.html", {
            "request": request,
            "user": user,
            "entry": entry,
            "employees": employees,
            "correction_days_back": correction_days_back,
            "error": "Ungültiger Buchungstyp."
        })

    try:
        new_timestamp = datetime.strptime(f"{timestamp_date} {timestamp_time}", "%Y-%m-%d %H:%M")
    except Exception:
        employees = db.query(Employee).filter(Employee.active == True).order_by(Employee.last_name, Employee.first_name).all()
        return templates.TemplateResponse("correction_edit.html", {
            "request": request,
            "user": user,
            "entry": entry,
            "employees": employees,
            "correction_days_back": correction_days_back,
            "error": "Datum oder Uhrzeit ist ungültig."
        })

    old_value = (
        f"employee_id={entry.employee_id}; "
        f"timestamp={entry.timestamp}; "
        f"entry_type={entry.entry_type}; "
        f"method={entry.method}; "
        f"terminal={entry.terminal}; "
        f"note={entry.note}"
    )

    entry.employee_id = employee_id
    entry.timestamp = new_timestamp
    entry.entry_type = entry_type
    entry.method = method or "manual_correction"
    entry.terminal = terminal or entry.terminal
    entry.note = note
    entry.corrected = True

    new_value = (
        f"employee_id={employee_id}; "
        f"timestamp={new_timestamp}; "
        f"entry_type={entry_type}; "
        f"method={method}; "
        f"terminal={terminal}; "
        f"note={note}"
    )

    correction = Correction(
        employee_id=employee_id,
        time_entry_id=entry.id,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        changed_by=user.employee_number,
        status="genehmigt"
    )

    db.add(correction)
    db.commit()

    log_action(db, user.employee_number, "time_entry_corrected", "time_entries", str(entry.id), reason)

    return templates.TemplateResponse("message.html", {
        "request": request,
        "title": "Korrektur gespeichert",
        "message": "Die Buchung wurde geändert.",
        "return_to": "/corrections"
    })

@router.post("/corrections/add")
def correction_add(
    request: Request,
    employee_id: int = Form(...),
    time_entry_id: int = Form(0),
    old_value: str = Form(""),
    new_value: str = Form(...),
    reason: str = Form(...),
    changed_by: str = Form("admin"),
    db: Session = Depends(get_db)
):
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect
    visible_ids = correction_visible_employee_ids(db, user)
    if employee_id not in visible_ids:
        return RedirectResponse("/corrections", 303)

    c = Correction(
        employee_id=employee_id,
        time_entry_id=time_entry_id or None,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        changed_by=user.employee_number
    )
    db.add(c)
    db.commit()
    log_action(db, user.employee_number, "correction_created", "corrections", str(c.id), reason)
    return RedirectResponse("/corrections", 303)


@router.get("/corrections/{entry_id}/delete", response_class=HTMLResponse)
def correction_delete_form(entry_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect

    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Fehler",
            "message": "Buchung nicht gefunden.",
            "return_to": "/corrections"
        })
    if not can_correct_entry(db, user, entry):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Für diese Buchung ist keine Korrektur erlaubt.", "return_to": "/corrections"})

    return templates.TemplateResponse("correction_delete.html", {
        "request": request,
        "user": user,
        "entry": entry,
        "error": None
    })


@router.post("/corrections/{entry_id}/delete", response_class=HTMLResponse)
def correction_delete_save(
    entry_id: int,
    request: Request,
    reason: str = Form(...),
    db: Session = Depends(get_db)
):
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect

    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Fehler",
            "message": "Buchung nicht gefunden.",
            "return_to": "/corrections"
        })
    if not can_correct_entry(db, user, entry):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Für diese Buchung ist keine Korrektur erlaubt.", "return_to": "/corrections"})

    reason = (reason or "").strip()
    if len(reason) < 3:
        return templates.TemplateResponse("correction_delete.html", {
            "request": request,
            "user": user,
            "entry": entry,
            "error": "Bitte einen nachvollziehbaren Grund für die Löschung angeben."
        })

    if entry.deleted:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Bereits gelöscht",
            "message": "Diese Buchung ist bereits als gelöscht markiert.",
            "return_to": "/corrections?show_deleted=1"
        })

    old_value = (
        f"employee_id={entry.employee_id}; "
        f"timestamp={entry.timestamp}; "
        f"entry_type={entry.entry_type}; "
        f"method={entry.method}; "
        f"terminal={entry.terminal}; "
        f"note={entry.note}"
    )

    actor = getattr(user, "employee_number", "admin") or "admin"
    entry.deleted = True
    entry.deleted_at = datetime.now()
    entry.deleted_by = actor
    entry.delete_reason = reason
    entry.corrected = True

    correction = Correction(
        employee_id=entry.employee_id,
        time_entry_id=entry.id,
        old_value=old_value,
        new_value="deleted=true",
        reason=f"Löschung: {reason}",
        changed_by=actor,
        status="genehmigt"
    )
    db.add(correction)
    db.commit()

    log_action(db, actor, "time_entry_deleted", "time_entries", str(entry.id), reason)

    return templates.TemplateResponse("message.html", {
        "request": request,
        "title": "Buchung gelöscht",
        "message": "Die Buchung wurde nicht endgültig entfernt, sondern revisionssicher als gelöscht markiert.",
        "return_to": "/corrections"
    })


@router.post("/corrections/{entry_id}/restore", response_class=HTMLResponse)
def correction_restore_save(entry_id: int, request: Request, reason: str = Form(...), db: Session = Depends(get_db)):
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect

    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": "Buchung nicht gefunden.", "return_to": "/corrections?show_deleted=1"})
    if not can_correct_entry(db, user, entry):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Für diese Buchung ist keine Korrektur erlaubt.", "return_to": "/corrections?show_deleted=1"})

    reason = (reason or "").strip()
    if len(reason) < 3:
        reason = "Wiederherstellung der gelöschten Buchung"

    actor = getattr(user, "employee_number", "admin") or "admin"
    entry.deleted = False
    entry.deleted_at = None
    entry.deleted_by = None
    entry.delete_reason = None
    entry.corrected = True

    correction = Correction(
        employee_id=entry.employee_id,
        time_entry_id=entry.id,
        old_value="deleted=true",
        new_value="deleted=false",
        reason=f"Wiederherstellung: {reason}",
        changed_by=actor,
        status="genehmigt"
    )
    db.add(correction)
    db.commit()
    log_action(db, actor, "time_entry_restored", "time_entries", str(entry.id), reason)

    return templates.TemplateResponse("message.html", {
        "request": request,
        "title": "Buchung wiederhergestellt",
        "message": "Die gelöschte Buchung wurde wiederhergestellt.",
        "return_to": "/corrections?show_deleted=1"
    })


