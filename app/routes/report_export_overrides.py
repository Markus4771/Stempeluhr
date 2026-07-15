from __future__ import annotations

import csv
import io
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from .common import Employee, TimeEntry, datetime, timedelta, not_deleted_filter, templates
from .reports import (
    _absence_summary,
    _entries_for_rows,
    _resolve_report_context,
    _stamp_entries,
    _team_statistics,
)

router = APIRouter()


def _stamp_map(entries: list[TimeEntry]) -> dict[tuple[int, object], dict[str, str]]:
    grouped: dict[tuple[int, object], dict[str, list[str]]] = defaultdict(lambda: {"kommen": [], "gehen": []})
    for entry in entries or []:
        typ = str(entry.entry_type or "").lower()
        if typ in {"kommen", "come", "in"}:
            grouped[(entry.employee_id, entry.timestamp.date())]["kommen"].append(entry.timestamp.strftime("%H:%M:%S"))
        elif typ in {"gehen", "leave", "out"}:
            grouped[(entry.employee_id, entry.timestamp.date())]["gehen"].append(entry.timestamp.strftime("%H:%M:%S"))
    result = {}
    for key, values in grouped.items():
        result[key] = {
            "kommen": ", ".join(values["kommen"]),
            "gehen": ", ".join(values["gehen"]),
        }
    return result


def _enhanced_csv(result: dict, entries: list[TimeEntry]) -> bytes:
    stamps = _stamp_map(entries)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Datum", "Mitarbeiter", "Kommen", "Gehen", "Soll (Std.)", "Brutto (Std.)",
        "Pause gesamt (Std.)", "Netto (Std.)", "Tag +/- (Std.)"
    ])
    for row in result.get("rows", []):
        times = stamps.get((row.employee_id, row.date), {})
        writer.writerow([
            row.date.strftime("%d.%m.%Y"),
            row.employee_name,
            times.get("kommen", ""),
            times.get("gehen", ""),
            f"{row.target_hours:.2f}".replace(".", ","),
            f"{row.gross_hours:.2f}".replace(".", ","),
            f"{row.break_hours:.2f}".replace(".", ","),
            f"{row.net_hours:.2f}".replace(".", ","),
            f"{row.overtime_hours:.2f}".replace(".", ","),
        ])
    totals = result.get("totals", {})
    writer.writerow([
        "Summe", "", "", "",
        f"{float(totals.get('target_hours', 0)):.2f}".replace(".", ","),
        f"{float(totals.get('gross_hours', 0)):.2f}".replace(".", ","),
        f"{float(totals.get('break_hours', 0)):.2f}".replace(".", ","),
        f"{float(totals.get('net_hours', 0)):.2f}".replace(".", ","),
        f"{float(totals.get('overtime_hours', 0)):.2f}".replace(".", ","),
    ])
    writer.writerow([])
    writer.writerow(["Alle Stempelzeiten"])
    writer.writerow(["Datum", "Uhrzeit", "Mitarbeiter", "Buchung", "Methode", "Terminal"])
    for entry in entries:
        typ = str(entry.entry_type or "").lower()
        label = "Kommen" if typ in {"kommen", "come", "in"} else "Gehen" if typ in {"gehen", "leave", "out"} else str(entry.entry_type or "")
        writer.writerow([
            entry.timestamp.strftime("%d.%m.%Y"),
            entry.timestamp.strftime("%H:%M:%S"),
            f"{entry.employee.first_name} {entry.employee.last_name}",
            label,
            entry.method or "",
            entry.terminal or "",
        ])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


@router.get("/reports/export.csv")
def reports_export_csv_with_times(
    request: Request,
    employee_id: int = 0,
    period: str = "month",
    date_from: str = "",
    date_to: str = "",
    db: Session = Depends(get_db),
):
    ctx = _resolve_report_context(request, db, employee_id, period, date_from, date_to)
    if not ctx:
        return RedirectResponse("/login", status_code=303)
    user, visible_ids, visible_employees, employee_id, period, start_day, end_day, result = ctx
    selected_ids = [employee_id] if employee_id else visible_ids
    entries = _entries_for_rows(_stamp_entries(db, selected_ids, start_day, end_day), result["rows"])
    filename = f"stempeluhr_report_{start_day.isoformat()}_{end_day.isoformat()}.csv"
    return Response(
        content=_enhanced_csv(result, entries),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/reports/print", response_class=HTMLResponse)
def reports_print_with_times(
    request: Request,
    employee_id: int = 0,
    period: str = "month",
    date_from: str = "",
    date_to: str = "",
    db: Session = Depends(get_db),
):
    ctx = _resolve_report_context(request, db, employee_id, period, date_from, date_to)
    if not ctx:
        return RedirectResponse("/login", status_code=303)
    user, visible_ids, visible_employees, employee_id, period, start_day, end_day, result = ctx
    selected_ids = [employee_id] if employee_id else visible_ids
    entries = _entries_for_rows(_stamp_entries(db, selected_ids, start_day, end_day), result["rows"])
    return templates.TemplateResponse("reports_print.html", {
        "request": request,
        "user": user,
        "entries": entries,
        "stamp_times": _stamp_map(entries),
        "worktime_rows": result["rows"],
        "worktime_totals": result["totals"],
        "team_stats": _team_statistics(result["rows"]),
        "absence_summary": _absence_summary(db, start_day, end_day, selected_ids),
        "filters": {"date_from": start_day.isoformat(), "date_to": end_day.isoformat(), "period": period},
    })
