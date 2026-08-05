"""Historische, rein statistische Vorschlaege fuer Plausibilitaetsfaelle."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, time
from statistics import median, pstdev
from typing import Any

from sqlalchemy.orm import Session

from app.models import TimeEntry


def _minutes(value: datetime) -> int:
    return value.hour * 60 + value.minute


def _clock(minutes: int | float) -> str:
    value = int(round(minutes)) % (24 * 60)
    return f"{value // 60:02d}:{value % 60:02d}"


def employee_booking_pattern(db: Session, employee_id: int, target_day, lookback_days: int = 90) -> dict[str, Any]:
    start = datetime.combine(target_day - timedelta(days=lookback_days), time.min)
    end = datetime.combine(target_day, time.min)
    rows = (
        db.query(TimeEntry)
        .filter(TimeEntry.employee_id == employee_id, TimeEntry.timestamp >= start, TimeEntry.timestamp < end)
        .order_by(TimeEntry.timestamp.asc())
        .all()
    )
    grouped: dict[Any, list[TimeEntry]] = defaultdict(list)
    for row in rows:
        if getattr(row, "deleted", False):
            continue
        if row.timestamp.weekday() != target_day.weekday():
            continue
        grouped[row.timestamp.date()].append(row)

    samples: dict[str, list[int]] = defaultdict(list)
    for entries in grouped.values():
        by_type: dict[str, list[TimeEntry]] = defaultdict(list)
        for entry in entries:
            by_type[str(entry.entry_type or "")].append(entry)
        for entry_type, typed in by_type.items():
            typed.sort(key=lambda item: item.timestamp)
            chosen = typed[0] if entry_type in {"kommen", "pause_start"} else typed[-1]
            samples[entry_type].append(_minutes(chosen.timestamp))

    suggestions: dict[str, dict[str, Any]] = {}
    for entry_type, values in samples.items():
        if len(values) < 3:
            continue
        spread = pstdev(values) if len(values) > 1 else 0.0
        confidence = "hoch" if len(values) >= 8 and spread <= 20 else "mittel" if len(values) >= 5 and spread <= 45 else "niedrig"
        suggestions[entry_type] = {
            "time": _clock(median(values)),
            "samples": len(values),
            "spread_minutes": round(spread, 1),
            "confidence": confidence,
        }

    return {
        "lookback_days": lookback_days,
        "weekday": target_day.strftime("%A"),
        "days_considered": len(grouped),
        "suggestions": suggestions,
        "disclaimer": "Statistischer Vorschlag aus historischen Buchungen; keine automatische Zeitkorrektur.",
    }
