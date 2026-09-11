from .common import *

router = APIRouter()


@router.post("/corrections/{entry_id}/restore", response_class=HTMLResponse)
def correction_restore_save(
    entry_id: int,
    request: Request,
    reason: str = Form("Wiederherstellung über Korrekturliste"),
    db: Session = Depends(get_db),
):
    """Stellt eine revisionssicher gelöschte Buchung wieder her.

    Die ursprüngliche Buchung bleibt dieselbe Datenbankzeile. Die
    Wiederherstellung wird zusätzlich in der Korrektur-History und im
    Audit-Log protokolliert.
    """
    user, redirect = require_corrections_response(request, db)
    if redirect:
        return redirect

    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Fehler",
            "message": "Buchung nicht gefunden.",
            "return_to": "/corrections?show_deleted=1",
        })

    if not can_correct_entry(db, user, entry):
        return templates.TemplateResponse("message.html", {
            "request": request,
            "user": user,
            "title": "Keine Berechtigung",
            "message": "Für diese Buchung ist keine Korrektur erlaubt.",
            "return_to": "/corrections?show_deleted=1",
        })

    if not entry.deleted:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Nicht gelöscht",
            "message": "Diese Buchung ist nicht als gelöscht markiert.",
            "return_to": "/corrections",
        })

    reason = (reason or "").strip()
    if len(reason) < 3:
        reason = "Wiederherstellung über Korrekturliste"

    actor = getattr(user, "employee_number", "admin") or "admin"
    deleted_at = entry.deleted_at
    deleted_by = entry.deleted_by
    delete_reason = entry.delete_reason

    old_value = (
        "deleted=true; "
        f"deleted_at={deleted_at}; "
        f"deleted_by={deleted_by}; "
        f"delete_reason={delete_reason}"
    )

    entry.deleted = False
    entry.deleted_at = None
    entry.deleted_by = None
    entry.delete_reason = None
    entry.corrected = True

    correction = Correction(
        employee_id=entry.employee_id,
        time_entry_id=entry.id,
        old_value=old_value,
        new_value="deleted=false; restored=true",
        reason=f"Wiederherstellung: {reason}",
        changed_by=actor,
        status="genehmigt",
    )
    db.add(correction)
    db.commit()

    log_action(
        db,
        actor,
        "time_entry_restored",
        "time_entries",
        str(entry.id),
        reason,
    )

    return templates.TemplateResponse("message.html", {
        "request": request,
        "title": "Buchung wiederhergestellt",
        "message": "Die Buchung wurde wieder aktiviert. Löschung und Wiederherstellung bleiben in der Korrektur-History protokolliert.",
        "return_to": "/corrections?show_deleted=1",
    })
