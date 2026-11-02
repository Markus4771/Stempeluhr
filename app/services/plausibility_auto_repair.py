"""Konservative automatische Reparaturen für Plausibilitätsfälle.

Automatisch verändert werden ausschließlich eindeutig identische Doppelbuchungen.
Zeitwerte werden niemals geschätzt oder ergänzt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, PlausibilityIssue, TimeEntry


@dataclass
class RepairProposal:
    issue_id: int
    employee_id: int
    issue_date: str
    repair_type: str
    title: str
    description: str
    keep_entry_id: int
    remove_entry_ids: list[int]
    timestamp: str
    entry_type: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_duplicate_issue(issue: PlausibilityIssue) -> bool:
    text = f"{issue.check_type or ''} {issue.message or ''}".lower()
    return "doppel" in text or "duplicate" in text


def _day_entries(db: Session, issue: PlausibilityIssue) -> list[TimeEntry]:
    start = datetime.combine(issue.issue_date, time.min)
    end = datetime.combine(issue.issue_date, time.max)
    return (
        db.query(TimeEntry)
        .filter(
            TimeEntry.employee_id == issue.employee_id,
            TimeEntry.timestamp >= start,
            TimeEntry.timestamp <= end,
            (TimeEntry.deleted.is_(False) | TimeEntry.deleted.is_(None)),
        )
        .order_by(TimeEntry.timestamp.asc(), TimeEntry.id.asc())
        .all()
    )


def proposal_for_issue(db: Session, issue: PlausibilityIssue) -> RepairProposal | None:
    if issue.status != "offen" or not _is_duplicate_issue(issue):
        return None

    groups: dict[tuple, list[TimeEntry]] = {}
    for entry in _day_entries(db, issue):
        # Nur exakt gleiche Buchungen gelten als automatisch sicher reparierbar.
        key = (
            entry.timestamp,
            str(entry.entry_type or ""),
            str(entry.method or ""),
            str(entry.terminal or ""),
            entry.terminal_id,
            entry.project_id,
        )
        groups.setdefault(key, []).append(entry)

    duplicates = [rows for rows in groups.values() if len(rows) > 1]
    if not duplicates:
        return None

    # Pro Fall wird zunächst genau eine identische Gruppe repariert. Nach einer
    # erneuten Prüfung können weitere Gruppen als eigener Vorschlag erscheinen.
    rows = sorted(duplicates[0], key=lambda row: row.id)
    keep = rows[0]
    remove = rows[1:]
    return RepairProposal(
        issue_id=issue.id,
        employee_id=issue.employee_id,
        issue_date=issue.issue_date.isoformat(),
        repair_type="exact_duplicate",
        title="Exakte Doppelbuchung entfernen",
        description=(
            f"Buchung {keep.entry_type} um {keep.timestamp.strftime('%H:%M:%S')} "
            f"ist {len(rows)}-mal vollständig identisch vorhanden. "
            "Der älteste Datensatz bleibt erhalten."
        ),
        keep_entry_id=keep.id,
        remove_entry_ids=[row.id for row in remove],
        timestamp=keep.timestamp.isoformat(timespec="seconds"),
        entry_type=keep.entry_type,
    )


def list_safe_proposals(db: Session) -> list[RepairProposal]:
    issues = (
        db.query(PlausibilityIssue)
        .filter(PlausibilityIssue.status == "offen")
        .order_by(PlausibilityIssue.issue_date.asc(), PlausibilityIssue.id.asc())
        .all()
    )
    result: list[RepairProposal] = []
    for issue in issues:
        proposal = proposal_for_issue(db, issue)
        if proposal:
            result.append(proposal)
    return result


def apply_proposal(db: Session, proposal: RepairProposal, actor: str) -> dict[str, Any]:
    issue = db.query(PlausibilityIssue).filter(PlausibilityIssue.id == proposal.issue_id).first()
    if not issue or issue.status != "offen":
        raise ValueError("Plausibilitätsfall ist nicht mehr offen")

    current = proposal_for_issue(db, issue)
    if not current or current.as_dict() != proposal.as_dict():
        raise ValueError("Der Reparaturvorschlag ist nicht mehr aktuell")

    now = datetime.now()
    removed: list[int] = []
    for entry_id in proposal.remove_entry_ids:
        entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
        if not entry or entry.deleted is True:
            continue
        entry.deleted = True
        entry.deleted_at = now
        entry.deleted_by = actor
        entry.delete_reason = f"Automatische Plausibilitätsreparatur, Fall #{issue.id}; exakte Doppelbuchung"
        removed.append(entry.id)

    if not removed:
        raise ValueError("Keine reparierbare Doppelbuchung mehr vorhanden")

    issue.status = "erledigt"
    issue.resolved_at = now
    issue.resolved_by = actor
    issue.comment = (
        f"Automatisch repariert: Datensatz {proposal.keep_entry_id} behalten; "
        f"Doppelbuchung(en) {', '.join(map(str, removed))} revisionssicher gelöscht."
    )
    db.add(AuditLog(
        actor=actor,
        action="plausibility_auto_repair",
        entity="plausibility_issue",
        entity_id=str(issue.id),
        details=issue.comment,
        created_at=now,
    ))
    db.commit()
    return {"issue_id": issue.id, "kept": proposal.keep_entry_id, "removed": removed}
