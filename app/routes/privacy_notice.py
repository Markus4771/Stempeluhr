from .common import *

router = APIRouter()


@router.get("/datenschutz", response_class=HTMLResponse)
def public_privacy_notice(request: Request, db: Session = Depends(get_db)):
    settings = service_settings_dict(db)
    privacy_version = settings.get("onboarding_privacy_version", "1.0")
    privacy_text = settings.get(
        "onboarding_privacy_text",
        "Ich habe die Datenschutzbestimmungen zur Nutzung der Stempeluhr gelesen und stimme der Verarbeitung meiner Daten zur Arbeitszeiterfassung zu.",
    )
    return templates.TemplateResponse("privacy_notice.html", {
        "request": request,
        "user": current_user(request, db),
        "privacy_version": privacy_version,
        "privacy_text": privacy_text,
        "privacy_officer_name": settings.get("privacy_officer_name", ""),
        "privacy_officer_email": settings.get("privacy_officer_email", ""),
        "privacy_processing_purpose": settings.get("privacy_processing_purpose", ""),
        "privacy_legal_basis": settings.get("privacy_legal_basis", ""),
        "privacy_retention_years": settings.get("privacy_retention_years", "10"),
        "privacy_notice_text": settings.get("privacy_notice_text", ""),
    })
