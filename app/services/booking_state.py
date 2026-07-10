"""Zentraler Zustandsautomat für Stempeluhr-Buchungen.

Diese Datei ist bewusst unabhängig von den Web-Routen, damit Raspberry,
Schnellbuchung, API und spätere Terminal-Clients dieselbe Logik nutzen.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import TimeEntry

VALID_ENTRY_TYPES = {"kommen", "gehen", "pause_start", "pause_ende"}
ENTRY_ALIASES = {
    "kommend": "kommen",
    "kommen": "kommen",
    "in": "kommen",
    "checkin": "kommen",
    "check_in": "kommen",
    "gehend": "gehen",
    "gehen": "gehen",
    "out": "gehen",
    "checkout": "gehen",
    "check_out": "gehen",
    "pause": "pause_start",
    "pausestart": "pause_start",
    "pause_start": "pause_start",
    "pausebeginn": "pause_start",
    "pause_ende": "pause_ende",
    "pauseende": "pause_ende",
    "pause_end": "pause_ende",
}

STATE_ABSENT = "abwesend"
STATE_PRESENT = "anwesend"
STATE_PAUSE = "pause"


@dataclass
class BookingState:
    employee_id: int
    date: date
    state: str
    last_entry: Optional[TimeEntry]
    last_valid_entry: Optional[TimeEntry]
    invalid_entries: int = 0

    @property
    def next_auto_entry_type(self) -> str:
        if self.state == STATE_PRESENT:
            return "gehen"
        if self.state == STATE_PAUSE:
            return "pause_ende"
        return "kommen"


def normalize_entry_type(value: str) -> str:
    key = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return ENTRY_ALIASES.get(key, key)


def is_valid_entry_type(value: str) -> bool:
    return normalize_entry_type(value) in VALID_ENTRY_TYPES


def _not_deleted_filter():
    # Ältere Installationen haben gelöschte Felder ggf. als NULL.
    return or_(TimeEntry.deleted == False, TimeEntry.deleted.is_(None))


def day_bounds(day: Optional[date] = None) -> tuple[datetime, datetime]:
    d = day or date.today()
    start = datetime.combine(d, datetime.min.time())
    return start, start + timedelta(days=1)


def entries_for_day(db: Session, employee_id: int, day: Optional[date] = None) -> list[TimeEntry]:
    start, end = day_bounds(day)
    return list(
        db.query(TimeEntry)
        .filter(
            TimeEntry.employee_id == employee_id,
            TimeEntry.timestamp >= start,
            TimeEntry.timestamp < end,
            _not_deleted_filter(),
        )
        .order_by(TimeEntry.timestamp.asc(), TimeEntry.id.asc())
        .all()
    )


def latest_entry(db: Session, employee_id: int) -> Optional[TimeEntry]:
    return (
        db.query(TimeEntry)
        .filter(TimeEntry.employee_id == employee_id, _not_deleted_filter())
        .order_by(TimeEntry.timestamp.desc(), TimeEntry.id.desc())
        .first()
    )


def transition_state(current_state: str, entry_type: str) -> Optional[str]:
    typ = normalize_entry_type(entry_type)
    if current_state == STATE_ABSENT and typ == "kommen":
        return STATE_PRESENT
    if current_state == STATE_PRESENT and typ == "pause_start":
        return STATE_PAUSE
    if current_state == STATE_PRESENT and typ == "gehen":
        return STATE_ABSENT
    if current_state == STATE_PAUSE and typ == "pause_ende":
        return STATE_PRESENT
    return None


def allowed_next_entries(current_state: str) -> set[str]:
    if current_state == STATE_ABSENT:
        return {"kommen"}
    if current_state == STATE_PRESENT:
        return {"gehen", "pause_start"}
    if current_state == STATE_PAUSE:
        return {"pause_ende"}
    return {"kommen"}


def get_booking_state(db: Session, employee_id: int, day: Optional[date] = None) -> BookingState:
    d = day or date.today()
    current = STATE_ABSENT
    last_valid = None
    invalid = 0
    entries = entries_for_day(db, employee_id, d)
    for entry in entries:
        next_state = transition_state(current, entry.entry_type)
        if next_state is None:
            invalid += 1
            continue
        current = next_state
        last_valid = entry
    return BookingState(
        employee_id=employee_id,
        date=d,
        state=current,
        last_entry=entries[-1] if entries else None,
        last_valid_entry=last_valid,
        invalid_entries=invalid,
    )


def determine_auto_entry_type(db: Session, employee_id: int, day: Optional[date] = None) -> str:
    return get_booking_state(db, employee_id, day).next_auto_entry_type


def is_valid_transition_for_employee(db: Session, employee_id: int, next_type: str, day: Optional[date] = None) -> bool:
    state = get_booking_state(db, employee_id, day)
    return normalize_entry_type(next_type) in allowed_next_entries(state.state)


def explain_next_action(db: Session, employee_id: int, day: Optional[date] = None) -> dict:
    state = get_booking_state(db, employee_id, day)
    return {
        "state": state.state,
        "next_entry_type": state.next_auto_entry_type,
        "last_entry_type": normalize_entry_type(state.last_entry.entry_type) if state.last_entry else None,
        "last_entry_time": state.last_entry.timestamp.isoformat(timespec="seconds") if state.last_entry and state.last_entry.timestamp else None,
        "invalid_entries": state.invalid_entries,
    }
