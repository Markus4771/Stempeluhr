from .common import *
from . import dashboard as dashboard_routes

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def privacy_dashboard_home(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user:
        return dashboard_routes.index(request, db)
    return templates.TemplateResponse("dashboard_public.html", {
        "request": request,
        "user": None,
    })


@router.get("/dashboard", response_class=HTMLResponse)
def privacy_dashboard_alias(request: Request, db: Session = Depends(get_db)):
    return privacy_dashboard_home(request, db)
