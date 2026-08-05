"""Dashboard-Statistik für offene Plausibilitätsfälle nach Priorität."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PlausibilityIssue

router = APIRouter(prefix="/api/dashboard", tags=["dashboard-plausibility"])

CRITICAL_VALUES = {"rot", "red", "critical", "kritisch", "fehler", "danger"}
WARNING_VALUES = {"gelb", "yellow", "warning", "warnung", "mittel"}
INFO_VALUES = {"blau", "blue", "info", "hinweis", "gruen", "green", "ok"}
CLOSED_STATUSES = {"erledigt", "gelöst", "geloest", "geschlossen", "resolved", "closed", "ignoriert"}


def severity_bucket(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in CRITICAL_VALUES:
        return "critical"
    if normalized in INFO_VALUES:
        return "info"
    # Bestehende Daten verwenden standardmäßig "gelb". Unbekannte Werte werden
    # deshalb vorsichtig als Warnung eingeordnet, nicht als kritischer Fehler.
    return "warning"


@router.get("/plausibility-summary")
def plausibility_summary(db: Session = Depends(get_db)):
    rows = (
        db.query(PlausibilityIssue.severity, func.count(PlausibilityIssue.id))
        .filter(func.lower(func.coalesce(PlausibilityIssue.status, "offen")).notin_(CLOSED_STATUSES))
        .group_by(PlausibilityIssue.severity)
        .all()
    )
    counts = {"critical": 0, "warning": 0, "info": 0}
    for severity, count in rows:
        counts[severity_bucket(severity)] += int(count or 0)
    counts["total"] = counts["critical"] + counts["warning"] + counts["info"]
    return {
        "status": "ok",
        "counts": counts,
        "links": {
            "all": "/plausibility",
            "critical": "/plausibility?severity=critical",
            "warning": "/plausibility?severity=warning",
            "info": "/plausibility?severity=info",
        },
    }
