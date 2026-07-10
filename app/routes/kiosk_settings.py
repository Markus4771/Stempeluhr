from .common import *

router = APIRouter()

KIOSK_LXDE_AUTOSTART_PATH = Path('/home/pi/.config/lxsession/LXDE-pi/autostart')
KIOSK_LABWC_AUTOSTART_PATH = Path('/home/pi/.config/labwc/autostart')
KIOSK_SERVICE_PATH = Path('/etc/systemd/system/stempeluhr-kiosk.service')


def _home_for_user(user_name: str) -> Path:
    user_name = (user_name or 'pi').strip() or 'pi'
    return Path('/home') / user_name


def _desktop_hint() -> str:
    # Debian 13/Raspberry Pi OS Bookworm/Trixie nutzt häufig labwc/Wayland.
    if Path('/etc/xdg/labwc').exists() or Path('/usr/share/wayland-sessions').exists():
        return 'labwc'
    if Path('/etc/xdg/lxsession').exists() or Path('/usr/share/xsessions').exists():
        return 'lxde'
    return 'labwc'


def _autostart_path(user_name: str, mode: str = 'auto') -> Path:
    mode = (mode or 'auto').strip().lower()
    home = _home_for_user(user_name)
    if mode == 'lxde':
        return home / '.config/lxsession/LXDE-pi/autostart'
    if mode == 'labwc':
        return home / '.config/labwc/autostart'
    return home / ('.config/labwc/autostart' if _desktop_hint() == 'labwc' else '.config/lxsession/LXDE-pi/autostart')


def ensure_kiosk_settings(db: Session):
    defaults = {
        'kiosk_enabled': '1',
        'kiosk_url': 'http://10.0.0.48:8000/raspberry',
        'kiosk_user': 'pi',
        'kiosk_browser': 'auto',
        'kiosk_desktop': 'auto',
        'kiosk_autostart_path': str(_autostart_path('pi', 'auto')),
        'kiosk_last_status': '',
        'raspberry_agent_enabled': '1',
        'raspberry_agent_log': '/var/log/stempeluhr-agent.log',
    }
    changed = False
    for key, value in defaults.items():
        if service_get_setting(db, key, None) is None:
            service_set_setting(db, key, value)
            changed = True
    if changed:
        db.commit()


def _browser_cmd(configured: str = 'auto') -> str:
    configured = (configured or 'auto').strip()
    if configured and configured != 'auto':
        return configured
    for candidate in ('chromium', 'chromium-browser'):
        if shutil.which(candidate):
            return candidate
    return 'chromium'


def _autostart_content(url: str, browser: str, desktop: str = 'auto') -> str:
    url = (url or 'http://10.0.0.48:8000/raspberry').strip()
    browser = _browser_cmd(browser)
    resolved_desktop = _desktop_hint() if (desktop or 'auto') == 'auto' else (desktop or 'labwc')
    if resolved_desktop == 'lxde':
        return '\n'.join([
            '@xset s off',
            '@xset -dpms',
            '@xset s noblank',
            '@/opt/stempeluhr/scripts/stempeluhr-raspberry-agent --once',
            '',
        ])
    # labwc/Wayland-Autostart ist ein Shell-Skript. Kein @ vor Befehlen.
    return '\n'.join([
        '#!/bin/sh',
        'xset s off 2>/dev/null || true',
        'xset -dpms 2>/dev/null || true',
        'xset s noblank 2>/dev/null || true',
        'systemctl --user restart stempeluhr-agent.service >/tmp/stempeluhr-agent-autostart.log 2>&1 || /opt/stempeluhr/scripts/stempeluhr-raspberry-agent --once >>/tmp/stempeluhr-agent-autostart.log 2>&1 &',
        '',
    ])


def _chromium_running() -> str:
    try:
        result = subprocess.run(['pgrep', '-a', 'chromium'], text=True, capture_output=True, timeout=5)
        return result.stdout.strip()
    except Exception:
        return ''


def _agent_status() -> str:
    lines = []
    try:
        result = subprocess.run(['/opt/stempeluhr/scripts/stempeluhr-raspberry-agent', '--status'], text=True, capture_output=True, timeout=5)
        if result.stdout.strip():
            lines.append(result.stdout.strip())
        if result.stderr.strip():
            lines.append(result.stderr.strip())
    except Exception as exc:
        lines.append(f'Agent-Status nicht verfuegbar: {exc}')
    try:
        log_path = Path('/var/log/stempeluhr-agent.log')
        if log_path.exists():
            tail = subprocess.run(['tail', '-n', '20', str(log_path)], text=True, capture_output=True, timeout=5)
            if tail.stdout.strip():
                lines.append('Letzte Agent-Logs:\n' + tail.stdout.strip())
    except Exception:
        pass
    return '\n\n'.join(lines)



def _safe_exists(path: Path):
    """Existenzprüfung ohne internen Fehler bei fehlenden Rechten."""
    try:
        return path.exists(), ''
    except PermissionError as exc:
        return False, f'Keine Leserechte für {path}: {exc}'
    except Exception as exc:
        return False, f'Autostart-Status konnte nicht geprüft werden: {exc}'


def _safe_read(path: Path):
    try:
        return path.read_text(encoding='utf-8'), ''
    except FileNotFoundError:
        return '', ''
    except PermissionError as exc:
        return '', f'Autostart konnte wegen fehlender Rechte nicht gelesen werden: {exc}'
    except Exception as exc:
        return '', f'Autostart konnte nicht gelesen werden: {exc}'


def _run_kiosk_helper(args, timeout=15):
    """Root-Helper für Kiosk-Dateien in /home/pi. Verhindert FastAPI-PermissionError."""
    helper = shutil.which('stempeluhr-kiosk-helper') or '/usr/local/sbin/stempeluhr-kiosk-helper'
    cmd = ['sudo', helper] + list(args)
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        out = (result.stdout or '').strip()
        err = (result.stderr or '').strip()
        return result.returncode, out, err
    except Exception as exc:
        return 99, '', str(exc)


@router.get('/system/settings/kiosk', response_class=HTMLResponse)
def system_settings_kiosk(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_kiosk_settings(db)
    settings = service_settings_dict(db)
    kiosk_user = settings.get('kiosk_user', 'pi') or 'pi'
    desktop_mode = settings.get('kiosk_desktop', 'auto') or 'auto'
    resolved_path = _autostart_path(kiosk_user, desktop_mode)
    stored_path = settings.get('kiosk_autostart_path') or str(resolved_path)
    autostart_path = Path(stored_path)
    autostart_exists, autostart_status_error = _safe_exists(autostart_path)
    content, read_error = _safe_read(autostart_path) if autostart_exists else ('', '')
    if autostart_status_error:
        # Fallback über Root-Helper, falls der Webdienst /home/pi nicht lesen darf.
        rc, out, err = _run_kiosk_helper(['exists', str(autostart_path)])
        if rc == 0:
            autostart_exists = (out.strip() == '1')
            autostart_status_error = ''
        elif err:
            autostart_status_error = err
    if autostart_exists and not content:
        rc, out, err = _run_kiosk_helper(['read', str(autostart_path)])
        if rc == 0:
            content = out
            read_error = ''
        elif err:
            read_error = err
    if read_error:
        content = read_error
    browser_auto = _browser_cmd(settings.get('kiosk_browser', 'auto'))
    return templates.TemplateResponse('system_settings_kiosk.html', {
        'request': request,
        'user': user,
        'settings': settings,
        'autostart_exists': autostart_exists,
        'autostart_content': content,
        'browser_auto': browser_auto,
        'desktop_auto': _desktop_hint(),
        'resolved_autostart_path': str(resolved_path),
        'chromium_running': _chromium_running(),
        'agent_status': _agent_status(),
        'autostart_status_error': autostart_status_error,
        'saved': request.query_params.get('saved'),
        'message': request.query_params.get('message', ''),
        'error': request.query_params.get('error', ''),
    })


@router.post('/system/settings/kiosk/save', response_class=HTMLResponse)
def system_settings_kiosk_save(
    request: Request,
    kiosk_enabled: str = Form('0'),
    kiosk_url: str = Form('http://10.0.0.48:8000/raspberry'),
    kiosk_user: str = Form('pi'),
    kiosk_browser: str = Form('auto'),
    kiosk_desktop: str = Form('auto'),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_kiosk_settings(db)
    url = (kiosk_url or '').strip() or 'http://10.0.0.48:8000/raspberry'
    if not (url.startswith('http://') or url.startswith('https://')):
        return RedirectResponse('/system/settings/kiosk?error=' + quote('Die Kiosk-URL muss mit http:// oder https:// beginnen.'), status_code=303)
    kiosk_user_clean = (kiosk_user or 'pi').strip() or 'pi'
    desktop_clean = (kiosk_desktop or 'auto').strip().lower() or 'auto'
    if desktop_clean not in ['auto', 'labwc', 'lxde']:
        desktop_clean = 'auto'
    path = _autostart_path(kiosk_user_clean, desktop_clean)
    service_set_setting(db, 'kiosk_enabled', '1' if str(kiosk_enabled).lower() in ['1','true','on','ja'] else '0')
    service_set_setting(db, 'kiosk_url', url)
    service_set_setting(db, 'kiosk_user', kiosk_user_clean)
    service_set_setting(db, 'kiosk_browser', (kiosk_browser or 'auto').strip() or 'auto')
    service_set_setting(db, 'kiosk_desktop', desktop_clean)
    service_set_setting(db, 'kiosk_autostart_path', str(path))
    service_set_setting(db, 'kiosk_last_status', 'Konfiguration gespeichert: ' + datetime.now().strftime('%d.%m.%Y %H:%M'))
    db.commit()
    log_action(db, user.employee_number, 'kiosk_settings_saved', 'settings', 'kiosk', f'Kiosk-URL: {url}, Desktop: {desktop_clean}')
    return RedirectResponse('/system/settings/kiosk?saved=1&message=' + quote('Kiosk-Einstellungen gespeichert.'), status_code=303)


@router.post('/system/settings/kiosk/write-autostart', response_class=HTMLResponse)
def system_settings_kiosk_write(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_kiosk_settings(db)
    settings = service_settings_dict(db)
    url = settings.get('kiosk_url') or 'http://10.0.0.48:8000/raspberry'
    browser = _browser_cmd(settings.get('kiosk_browser', 'auto'))
    kiosk_user = settings.get('kiosk_user', 'pi') or 'pi'
    desktop = settings.get('kiosk_desktop', 'auto') or 'auto'
    path = _autostart_path(kiosk_user, desktop)
    content = _autostart_content(url, browser, desktop)
    rc, out, err = _run_kiosk_helper(['write', str(path), kiosk_user, content], timeout=20)
    if rc != 0:
        # Fallback für Installationen ohne Helper, wenn der Dienst zufällig ausreichend Rechte hat.
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            path.chmod(0o755)
            try:
                subprocess.run(['chown', '-R', f'{kiosk_user}:{kiosk_user}', str(_home_for_user(kiosk_user) / '.config')], timeout=10, check=False)
            except Exception:
                pass
        except Exception as exc:
            detail = err or str(exc)
            return RedirectResponse('/system/settings/kiosk?error=' + quote(f'Autostart konnte nicht geschrieben werden: {detail}'), status_code=303)
    service_set_setting(db, 'kiosk_autostart_path', str(path))
    status = f'Autostart geschrieben: {path} ({datetime.now().strftime("%d.%m.%Y %H:%M")})'
    service_set_setting(db, 'kiosk_last_status', status)
    db.commit()
    log_action(db, user.employee_number, 'kiosk_autostart_written', 'settings', 'kiosk', status)
    return RedirectResponse('/system/settings/kiosk?saved=1&message=' + quote('Kiosk-Autostart wurde geschrieben. Bitte Raspberry neu starten.'), status_code=303)
