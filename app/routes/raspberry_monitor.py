from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .common import templates, require_system_admin_response
from app.database import get_db
from app.models import RaspberryClient

router = APIRouter()
SCREENSHOT_DIR = Path('/var/lib/stempeluhr/raspberry-screenshots')


def _online(client: RaspberryClient) -> bool:
    try:
        return bool(client.last_seen and client.last_seen > datetime.now() - timedelta(seconds=90))
    except Exception:
        return False


def _client_dict(c: RaspberryClient) -> dict:
    return {
        'id': c.id,
        'hostname': c.hostname,
        'ip_address': c.ip_address,
        'online': _online(c),
        'chromium_running': bool(c.chromium_running),
        'kiosk_url': c.kiosk_url,
        'fullscreen': bool(c.fullscreen),
        'last_seen': c.last_seen.strftime('%d.%m.%Y %H:%M:%S') if c.last_seen else None,
        'agent_version': c.agent_version,
        'cpu_percent': c.cpu_percent,
        'ram_percent': c.ram_percent,
        'temperature': c.temperature,
        'uptime': c.uptime,
        'pending_command': c.pending_command,
        'command_result': c.command_result,
        'last_screenshot_path': c.last_screenshot_path,
    }


@router.get('/system/raspberry-monitor', response_class=HTMLResponse)
def raspberry_monitor_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    clients = db.query(RaspberryClient).order_by(desc(RaspberryClient.last_seen)).all()
    return RedirectResponse('/system/monitoring#raspberry-terminals', status_code=303)


@router.get('/api/v1/raspberry/clients')
def raspberry_clients_api(db: Session = Depends(get_db)):
    return {'clients': [_client_dict(c) for c in db.query(RaspberryClient).order_by(desc(RaspberryClient.last_seen)).all()]}


@router.post('/api/v1/raspberry/heartbeat')
@router.post('/api/v1/raspberry/heartbeat-json')
async def raspberry_heartbeat_json(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
    except Exception:
        data = {}
    hostname = str(data.get('hostname') or 'unknown').strip()[:150]
    client = db.query(RaspberryClient).filter(RaspberryClient.hostname == hostname).first()
    if not client:
        client = RaspberryClient(hostname=hostname, created_at=datetime.now())
        db.add(client)
    client.ip_address = str(data.get('ip_address') or (request.client.host if request.client else ''))[:100]
    client.agent_version = str(data.get('agent_version') or '')[:50]
    client.app_version = str(data.get('app_version') or '')[:50]
    client.debian_version = str(data.get('debian_version') or '')[:200]
    client.chromium_running = bool(data.get('chromium_running'))
    client.kiosk_url = str(data.get('kiosk_url') or '')
    client.fullscreen = bool(data.get('fullscreen'))
    client.wayland_display = str(data.get('wayland_display') or '')[:100]
    client.display_name = str(data.get('display') or '')[:100]
    try:
        client.cpu_percent = float(data.get('cpu_percent') or 0)
    except Exception:
        client.cpu_percent = 0
    try:
        client.ram_percent = float(data.get('ram_percent') or 0)
    except Exception:
        client.ram_percent = 0
    client.temperature = str(data.get('temperature') or '')[:50]
    client.uptime = str(data.get('uptime') or '')[:100]
    client.last_log = str(data.get('last_log') or '')[-4000:]
    client.last_seen = datetime.now()
    client.updated_at = datetime.now()
    command = client.pending_command
    db.commit()
    return {'status': 'ok', 'command': command}


@router.post('/api/v1/raspberry/command-result')
async def raspberry_command_result(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
    except Exception:
        data = {}
    hostname = str(data.get('hostname') or 'unknown').strip()[:150]
    command = str(data.get('command') or '').strip()[:100]
    result = str(data.get('result') or '').strip()[:1000]
    client = db.query(RaspberryClient).filter(RaspberryClient.hostname == hostname).first()
    if client:
        if not command or client.pending_command == command:
            client.pending_command = None
        client.command_result = result or 'Befehl abgeschlossen'
        client.command_finished_at = datetime.now()
        client.updated_at = datetime.now()
        db.commit()
    return {'status': 'ok'}


@router.post('/api/v1/raspberry/screenshot')
async def raspberry_screenshot(request: Request, file: UploadFile = File(...), hostname: str = Form('unknown'), db: Session = Depends(get_db)):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    safe_host = ''.join(ch for ch in hostname if ch.isalnum() or ch in ('-', '_', '.'))[:100] or 'unknown'
    target = SCREENSHOT_DIR / f'{safe_host}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    content = await file.read()
    if not content:
        return JSONResponse({'status': 'error', 'message': 'Leere Screenshot-Datei'}, status_code=400)
    target.write_bytes(content)
    client = db.query(RaspberryClient).filter(RaspberryClient.hostname == hostname).first()
    if not client:
        client = RaspberryClient(hostname=hostname, created_at=datetime.now())
        db.add(client)
    client.ip_address = str(request.client.host if request.client else client.ip_address or '')[:100]
    client.last_screenshot_path = str(target)
    client.pending_command = None if client.pending_command == 'screenshot' else client.pending_command
    client.command_result = f'Bildschirmfoto gespeichert: {target.name}'
    client.command_finished_at = datetime.now()
    client.last_seen = datetime.now()
    client.updated_at = datetime.now()
    db.commit()
    return {'status': 'ok', 'path': str(target), 'size': len(content)}


@router.get('/system/raspberry-monitor/screenshot/{client_id}')
def raspberry_screenshot_view(client_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    client = db.query(RaspberryClient).get(client_id)
    if not client or not client.last_screenshot_path or not Path(client.last_screenshot_path).exists():
        return HTMLResponse('<h1>Kein Screenshot vorhanden</h1><p><a href="/system/raspberry-monitor">zurück</a></p>', status_code=404)
    from fastapi.responses import FileResponse
    return FileResponse(client.last_screenshot_path, media_type='image/png')


@router.post('/system/raspberry-monitor/{client_id}/command')
async def raspberry_command(client_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    form = await request.form()
    command = str(form.get('command') or '').strip()
    allowed = {'screenshot', 'restart_chromium', 'clear_cache'}
    client = db.query(RaspberryClient).get(client_id)
    if client and command in allowed:
        client.pending_command = command
        client.command_requested_at = datetime.now()
        client.command_result = 'Befehl wartet auf Raspberry-Agent'
        client.updated_at = datetime.now()
        db.commit()
    return RedirectResponse('/system/monitoring#raspberry-terminals', status_code=303)
