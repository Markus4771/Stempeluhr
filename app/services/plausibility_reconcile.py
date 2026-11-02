"""Abgleich gespeicherter Plausibilitätsfälle mit dem aktuellen Buchungsstand."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AuditLog, PlausibilityIssue
from app.services.plausibility import scan_day


def reconcile_open_plausibility_issues(db: Session, *, limit_days: int = 180) -> dict:
    """Prüft offene/geprüfte Fälle erneut und schließt nicht mehr vorhandene Ursachen.

    Die reguläre Prüfung liefert alle aktuell erkannten Prüfarten zurück. Gespeicherte
    offene Fälle, deren Kombination aus Mitarbeiter, Datum und Prüfart nicht mehr
    erkannt wird, werden revisionssicher auf ``erledigt`` gesetzt.
    """
    candidates = (
        db.query(PlausibilityIssue)
        .filter(PlausibilityIssue.status.in_(["offen", "geprueft"]))
        .order_by(PlausibilityIssue.issue_date.desc(), PlausibilityIssue.id.desc())
        .all()
    )
    if not candidates:
        return {"checked": 0, "resolved": 0, "days": 0}

    by_day: dict = defaultdict(list)
    for issue in candidates:
        by_day[issue.issue_date].append(issue)

    selected_days = sorted(by_day.keys(), reverse=True)[:max(1, int(limit_days))]
    resolved = 0
    checked = 0

    for day in selected_days:
        rows = by_day[day]
        employee_ids = sorted({row.employee_id for row in rows})
        detected = scan_day(db, day, employee_ids=employee_ids, send_employee_mail=False)
        active_keys = {(row.employee_id, row.check_type) for row in detected}

        for issue in rows:
            checked += 1
            if (issue.employee_id, issue.check_type) in active_keys:
                continue
            issue.status = "erledigt"
            issue.resolved_at = datetime.now()
            issue.resolved_by = "SYSTEM-ABGLEICH"
            old_comment = (issue.comment or "").strip()
            note = "Automatisch erledigt: Ursache ist nach erneuter Prüfung nicht mehr vorhanden."
            issue.comment = f"{old_comment}\n{note}".strip()
            issue.updated_at = datetime.now()
            resolved += 1

    if resolved:
        db.add(AuditLog(
            actor="system",
            action="plausibility_reconcile",
            entity="plausibility",
            entity_id="open",
            details=f"{resolved} von {checked} offenen/geprüften Fällen automatisch erledigt",
        ))
    db.commit()
    return {"checked": checked, "resolved": resolved, "days": len(selected_days)}
