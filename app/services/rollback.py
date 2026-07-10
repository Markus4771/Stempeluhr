from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path('/opt/stempeluhr/backups')


def list_rollback_backups() -> list[dict]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in sorted(BACKUP_DIR.glob('pre_update_*.tar.gz'), reverse=True):
        rows.append({'name': p.name, 'path': str(p), 'size': p.stat().st_size, 'mtime': datetime.fromtimestamp(p.stat().st_mtime).strftime('%d.%m.%Y %H:%M:%S')})
    return rows[:50]


def create_manual_restore_point(note: str = '') -> dict:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / f'manual_restore_point_{datetime.now().strftime("%Y%m%d_%H%M%S")}.tar.gz'
    cmd = ['tar', '-czf', str(target), '-C', '/opt', 'stempeluhr']
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
    return {'ok': p.returncode == 0, 'file': str(target), 'message': (p.stdout or p.stderr or '').strip(), 'note': note}
