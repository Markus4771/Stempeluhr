from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4

import caldav
from icalendar import Calendar, Event
import recurring_ical_events
from sqlalchemy.orm import Session

from app.models import Setting, Holiday, Employee, VacationRequest

def get_settings(db: Session) -> dict:
    return {s.key: s.value for s in db.query(Setting).all()}

def set_setting(db: Session, key: str, value: str):
    row = db.query(Setting).filter(Setting.key == key).first()
    if not row:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value

def caldav_client(settings: dict):
    url = settings.get("caldav_url", "").strip()
    username = settings.get("caldav_username", "").strip()
    password = settings.get("caldav_password", "")
    if not url:
        raise RuntimeError("CalDAV-URL fehlt.")
    return caldav.DAVClient(url=url, username=username or None, password=password or None)

def _as_bool(value: str, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "ja", "on", "aktiv", "enabled"}


def import_holidays_from_caldav(db: Session, year: int | None = None) -> int:
    """Importiert Feiertage aus einem CalDAV-Kalender in die lokale Feiertagstabelle.

    Die Einträge werden anhand von Datum + Name aktualisiert/angelegt. Vorhandene
    Feiertage werden nicht doppelt angelegt. Ganztägige Termine und wiederkehrende
    Termine werden berücksichtigt.
    """
    settings = get_settings(db)
    if not _as_bool(settings.get("caldav_holidays_enabled", "true"), True):
        set_setting(db, "caldav_last_status", "Feiertagsimport deaktiviert")
        db.commit()
        return 0

    calendar_url = settings.get("caldav_holiday_calendar_url", "").strip()
    if not calendar_url:
        raise RuntimeError("Feiertagskalender-URL fehlt.")

    if year is None:
        year = datetime.now().year

    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)

    client = caldav_client(settings)
    principal = client.principal()
    calendars = principal.calendars()

    target_calendar = None
    for cal in calendars:
        if str(cal.url).rstrip("/") == calendar_url.rstrip("/"):
            target_calendar = cal
            break

    if target_calendar is None:
        # fallback: direkte Kalender-URL verwenden
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
                if isinstance(dtstart, datetime):
                    holiday_date = dtstart.date()
                else:
                    holiday_date = dtstart

                if not isinstance(holiday_date, date):
                    continue

                # einfache Erkennung für halbe Feiertage/Firmentage
                summary_lower = summary.lower()
                half_day = any(token in summary_lower for token in ["halb", "1/2", "halber"])

                exists = db.query(Holiday).filter(
                    Holiday.date == holiday_date,
                    Holiday.name == summary,
                ).first()
                if exists:
                    exists.federal_state = "CalDAV"
                    exists.half_day = half_day
                    exists.active = True
                    updated += 1
                else:
                    db.add(Holiday(
                        name=summary,
                        date=holiday_date,
                        federal_state="CalDAV",
                        half_day=half_day,
                        active=True,
                    ))
                    count += 1
        except Exception:
            continue

    set_setting(db, "caldav_last_import", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    set_setting(db, "caldav_last_status", f"{count} Feiertage neu, {updated} aktualisiert")
    db.commit()
    return count


def should_auto_sync_holidays(db: Session) -> bool:
    settings = get_settings(db)
    if not _as_bool(settings.get("caldav_enabled", "false"), False):
        return False
    if not _as_bool(settings.get("caldav_holidays_enabled", "true"), True):
        return False
    last = settings.get("caldav_last_import", "").strip()
    try:
        interval = int(settings.get("caldav_holiday_sync_interval_hours", "24") or "24")
    except Exception:
        interval = 24
    if not last:
        return True
    try:
        last_dt = datetime.strptime(last, "%d.%m.%Y %H:%M:%S")
        return datetime.now() - last_dt >= timedelta(hours=max(1, interval))
    except Exception:
        return True


def build_vacation_ical(db: Session) -> str:
    settings = get_settings(db)
    calendar_name = (settings.get("absence_calendar_name") or "Abwesenheit").strip() or "Abwesenheit"

    cal = Calendar()
    cal.add("prodid", "-//Stempeluhr Professional//Abwesenheitskalender//DE")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    # NAME wird von manchen Clients verwendet, X-WR-CALNAME von Thunderbird/Apple/Outlook.
    cal.add("name", calendar_name)
    cal.add("x-wr-calname", calendar_name)
    cal.add("x-wr-caldesc", "Abwesenheitskalender aus der Stempeluhr")

    requests = (
        db.query(VacationRequest)
        .filter(VacationRequest.status == "genehmigt")
        .order_by(VacationRequest.start_date)
        .all()
    )

    for req in requests:
        emp = req.employee
        if not emp:
            continue
        ev = Event()
        ev.add("uid", f"vacation-{req.id}@stempeluhr")
        raw_type = (req.request_type or "Abwesenheit").strip()
        reason_map = {
            "abwesenheit": "Urlaub",
            "urlaub": "Urlaub",
            "krank": "Krank",
            "krankheit": "Krank",
            "berufsschule": "Berufsschule",
            "sonderurlaub": "Sonderurlaub",
            "homeoffice": "Homeoffice",
        }
        reason = reason_map.get(raw_type.lower(), raw_type.capitalize())
        if raw_type.lower() == "sonstiges" and req.custom_reason:
            reason = str(req.custom_reason).strip() or "Sonstiges"
        employee_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip() or getattr(emp, "employee_number", "Mitarbeiter")
        # 5.2.20: Externe Kalendertermine zeigen eindeutig Name und Abwesenheitsgrund.
        ev.add("summary", f"{employee_name} – {reason}")
        ev.add("dtstart", req.start_date)
        ev.add("dtend", req.end_date + timedelta(days=1))
        ev.add("dtstamp", datetime.now())
        description_parts = [f"Name: {employee_name}", f"Abwesenheitsgrund: {reason}"]
        if req.comment:
            description_parts.append(f"Kommentar: {req.comment}")
        ev.add("description", "\n".join(description_parts))
        cal.add_component(ev)

    return cal.to_ical().decode("utf-8")
