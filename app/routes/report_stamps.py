from .common import *

router = APIRouter()


def _parse_report_date(value: str, fallback: date) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return fallback


@router.get("/reports/stamps", response_class=HTMLResponse)
def report_stamps(
    request: Request,
    employee_id: int = 0,
    date_from: str = "",
    date_to: str = "",
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    visible_ids = report_visible_employee_ids(db, user)
    elevated = is_hr_or_admin(user) or role_name(user) == "Teamleiter"

    if not elevated:
        selected_ids = [user.id]
    elif employee_id and employee_id in visible_ids:
        selected_ids = [employee_id]
    else:
        selected_ids = visible_ids

    today = date.today()
    start_day = _parse_report_date(date_from, today.replace(day=1))
    end_day = _parse_report_date(date_to, today)
    if end_day < start_day:
        end_day = start_day

    start_dt = datetime.combine(start_day, datetime.min.time())
    end_dt = datetime.combine(end_day + timedelta(days=1), datetime.min.time())

    query = db.query(TimeEntry).join(Employee, TimeEntry.employee_id == Employee.id)
    if selected_ids:
        query = query.filter(
            TimeEntry.employee_id.in_(selected_ids),
            TimeEntry.timestamp >= start_dt,
            TimeEntry.timestamp < end_dt,
            not_deleted_filter(),
        )
    else:
        query = query.filter(TimeEntry.id == -1)

    entries = query.order_by(TimeEntry.timestamp.asc(), TimeEntry.id.asc()).all()
    return templates.TemplateResponse("report_stamps.html", {
        "request": request,
        "user": user,
        "entries": entries,
    })
