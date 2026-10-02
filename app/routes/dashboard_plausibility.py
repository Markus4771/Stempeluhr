"""Dashboard-Statistik für wirklich offene Plausibilitätsfälle nach Priorität."""
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


def severity_bucket(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in CRITICAL_VALUES:
        return "critical"
    if normalized in INFO_VALUES:
        return "info"
    return "warning"


@router.get("/plausibility-summary")
def plausibility_summary(db: Session = Depends(get_db)):
    """Liefert ausschließlich Fälle mit Status ``offen``.

    ``geprueft`` bedeutet, dass ein Fall bereits behandelt wurde und ggf. nur noch
    dokumentarisch oder zur abschließenden Freigabe erhalten bleibt. Solche Fälle
    dürfen deshalb nicht in der Dashboard-Kachel „offene Meldungen“ erscheinen.
    """
    rows = (
        db.query(PlausibilityIssue.severity, func.count(PlausibilityIssue.id))
        .filter(func.lower(func.coalesce(PlausibilityIssue.status, "offen")) == "offen")
        .group_by(PlausibilityIssue.severity)
        .all()
    )
    counts = {"critical": 0, "warning": 0, "info": 0}
    for severity, count in rows:
        counts[severity_bucket(severity)] += int(count or 0)
    counts["total"] = counts["critical"] + counts["warning"] + counts["info"]

    reviewed = (
        db.query(func.count(PlausibilityIssue.id))
        .filter(func.lower(func.coalesce(PlausibilityIssue.status, "offen")) == "geprueft")
        .scalar()
        or 0
    )

    return {
        "status": "ok",
        "counts": counts,
        "reviewed": int(reviewed),
        "links": {
            "all": "/plausibility?status=offen",
            "critical": "/plausibility?status=offen&severity=critical",
            "warning": "/plausibility?status=offen&severity=warning",
            "info": "/plausibility?status=offen&severity=info",
            "reviewed": "/plausibility?status=geprueft",
        },
    }
