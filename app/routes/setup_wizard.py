from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from .common import templates, require_system_admin_response
from app.database import get_db
from app.services.settings_service import get_setting, set_setting

router = APIRouter()

@router.get('/setup', response_class=HTMLResponse)
def setup_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    settings = {k: get_setting(db, k, '') for k in ['setup_completed','email_enabled','backup_enabled','plausibility_enabled','api_enabled']}
    return templates.TemplateResponse('setup_wizard.html', {'request': request, 'user': user, 'settings': settings})

@router.post('/setup')
def setup_save(request: Request, setup_completed: str = Form('0'), api_enabled: str = Form('0'), db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    set_setting(db, 'setup_completed', 'true' if setup_completed == '1' else 'false')
    set_setting(db, 'api_enabled', 'true' if api_enabled == '1' else 'false')
    db.commit()
    return RedirectResponse('/setup', status_code=303)
