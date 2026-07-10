from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from sqlalchemy import text


def _cmd(cmd: list[str], timeout: int = 3) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        out = (p.stdout or p.stderr or '').strip()
        return p.returncode == 0, out[:4000]
    except Exception as exc:
        return False, str(exc)


def _service_status(name: str) -> dict:
    ok, state = _cmd(['systemctl', 'is-active', name])
    enabled_ok, enabled = _cmd(['systemctl', 'is-enabled', name])
    return {
        'name': name,
        'ok': ok,
        'state': (state or 'unknown').strip(),
        'enabled': (enabled or 'unknown').strip(),
        'enabled_ok': enabled_ok,
    }


def _read_first(path: str, default: str = '') -> str:
    try:
        return Path(path).read_text(errors='ignore').splitlines()[0].strip()
    except Exception:
        return default


def system_status(db) -> dict:
    disk = shutil.disk_usage('/')
    load = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
    pg_ok = False
    pg_msg = ''
    table_count = None
    employee_count = None
    open_plausibility_count = None
    try:
        db.execute(text('SELECT 1'))
        pg_ok = True
        pg_msg = 'OK'
        try:
            table_count = db.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")).scalar()
        except Exception:
            table_count = None
        try:
            employee_count = db.execute(text('SELECT COUNT(*) FROM employees')).scalar()
        except Exception:
            employee_count = None
        try:
            open_plausibility_count = db.execute(text("SELECT COUNT(*) FROM plausibility_issues WHERE status='offen'")).scalar()
        except Exception:
            open_plausibility_count = None
    except Exception as exc:
        pg_msg = str(exc)

    mem_total = _read_first('/proc/meminfo')
    service_log_ok, service_log = _cmd(['journalctl', '-u', 'stempeluhr', '-n', '20', '--no-pager'], timeout=5)

    return {
        'time': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        'hostname': os.uname().nodename if hasattr(os, 'uname') else '',
        'disk_total_gb': round(disk.total / 1024**3, 1),
        'disk_free_gb': round(disk.free / 1024**3, 1),
        'disk_used_percent': round((disk.used / disk.total) * 100, 1) if disk.total else 0,
        'load1': round(load[0], 2),
        'load5': round(load[1], 2),
        'load15': round(load[2], 2),
        'meminfo': mem_total,
        'postgresql_ok': pg_ok,
        'postgresql_message': pg_msg,
        'table_count': table_count,
        'employee_count': employee_count,
        'open_plausibility_count': open_plausibility_count,
        'services': [
            _service_status('stempeluhr'),
            _service_status('postgresql'),
            _service_status('stempeluhr-agent'),
        ],
        'backup_dir_exists': Path('/opt/stempeluhr/backups').exists(),
        'plugin_dir_exists': Path('/opt/stempeluhr/plugins').exists(),
        'install_log_exists': Path('/var/log/stempeluhr/install.log').exists(),
        'service_log': service_log if service_log_ok else service_log,
    }
