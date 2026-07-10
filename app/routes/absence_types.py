from .common import *

router = APIRouter()


def _slugify_absence_code(name: str) -> str:
    value = (name or "").strip().lower()
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value[:50] or f"art_{uuid4().hex[:8]}"


def ensure_default_absence_types(db: Session):
    defaults = [
        ("Urlaub", "abwesenheit", True, False, 10),
        ("Krank", "krank", False, False, 20),
        ("Homeoffice", "homeoffice", True, False, 30),
        ("Dienstreise", "dienstreise", True, False, 40),
        ("Fortbildung", "fortbildung", True, False, 50),
        ("Berufsschule", "berufsschule", False, False, 60),
        ("Sonstiges", "sonstiges", True, True, 90),
    ]
    changed = False
    for name, code, requires_approval, requires_text, sort_order in defaults:
        existing = db.query(AbsenceType).filter(AbsenceType.code == code).first()
        if not existing:
            db.add(AbsenceType(
                name=name,
                code=code,
                active=True,
                requires_approval=requires_approval,
                requires_text=requires_text,
                sort_order=sort_order,
            ))
            changed = True
    if changed:
        db.commit()


@router.get("/system/settings/absence-types", response_class=HTMLResponse)
def absence_types_settings(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not is_system_admin(user):
        return RedirectResponse("/login", status_code=303)
    ensure_default_absence_types(db)
    types = db.query(AbsenceType).order_by(AbsenceType.sort_order, AbsenceType.name).all()
    used = {row[0]: row[1] for row in db.query(VacationRequest.request_type, func.count(VacationRequest.id)).group_by(VacationRequest.request_type).all()}
    return templates.TemplateResponse("system_absence_types.html", {
        "request": request,
        "user": user,
        "types": types,
        "used": used,
        "error": None,
    })


@router.post("/system/settings/absence-types/add", response_class=HTMLResponse)
def absence_type_add(
    request: Request,
    name: str = Form(...),
    code: str = Form(""),
    requires_approval: str = Form("off"),
    requires_text: str = Form("off"),
    active: str = Form("on"),
    sort_order: int = Form(100),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not is_system_admin(user):
        return RedirectResponse("/login", status_code=303)
    ensure_default_absence_types(db)
    clean_name = name.strip()
    clean_code = _slugify_absence_code(code or clean_name)
    if len(clean_name) < 2:
        return RedirectResponse("/system/settings/absence-types?error=name", status_code=303)
    if db.query(AbsenceType).filter(AbsenceType.code == clean_code).first():
        clean_code = f"{clean_code}_{uuid4().hex[:4]}"
    db.add(AbsenceType(
        name=clean_name,
        code=clean_code,
        active=(active == "on"),
        requires_approval=(requires_approval == "on"),
        requires_text=(requires_text == "on"),
        sort_order=sort_order,
    ))
    db.commit()
    log_action(db, user.employee_number, "absence_type_created", "absence_types", clean_code, clean_name)
    return RedirectResponse("/system/settings/absence-types", status_code=303)


@router.post("/system/settings/absence-types/{type_id}/update")
def absence_type_update(
    type_id: int,
    request: Request,
    name: str = Form(...),
    requires_approval: str = Form("off"),
    requires_text: str = Form("off"),
    active: str = Form("off"),
    sort_order: int = Form(100),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not is_system_admin(user):
        return RedirectResponse("/login", status_code=303)
    item = db.query(AbsenceType).filter(AbsenceType.id == type_id).first()
    if item:
        item.name = name.strip() or item.name
        item.requires_approval = requires_approval == "on"
        item.requires_text = requires_text == "on"
        item.active = active == "on"
        item.sort_order = sort_order
        item.updated_at = datetime.now()
        db.commit()
        log_action(db, user.employee_number, "absence_type_updated", "absence_types", str(item.id), item.name)
    return RedirectResponse("/system/settings/absence-types", status_code=303)


@router.post("/system/settings/absence-types/{type_id}/delete")
def absence_type_delete(type_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not is_system_admin(user):
        return RedirectResponse("/login", status_code=303)
    item = db.query(AbsenceType).filter(AbsenceType.id == type_id).first()
    if not item:
        return RedirectResponse("/system/settings/absence-types", status_code=303)
    used_count = db.query(VacationRequest).filter(VacationRequest.request_type == item.code).count()
    if used_count > 0:
        item.active = False
        item.updated_at = datetime.now()
        db.commit()
        log_action(db, user.employee_number, "absence_type_deactivated_used", "absence_types", str(item.id), item.name)
    else:
        log_action(db, user.employee_number, "absence_type_deleted", "absence_types", str(item.id), item.name)
        db.delete(item)
        db.commit()
    return RedirectResponse("/system/settings/absence-types", status_code=303)
