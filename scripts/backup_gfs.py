#!/usr/bin/env python3
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

APP_DIR = Path('/opt/stempeluhr')
CONFIG_DIR = Path('/etc/stempeluhr')
ENV_PATH = CONFIG_DIR / 'stempeluhr.env'
SECRET_PATH = CONFIG_DIR / 'secrets/database.conf'

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)
if SECRET_PATH.exists():
    load_dotenv(SECRET_PATH, override=True)

DB_TYPE = os.getenv('DATABASE_TYPE', 'postgresql').lower()
DB_HOST = os.getenv('DATABASE_HOST', '127.0.0.1')
DB_PORT = os.getenv('DATABASE_PORT', '5432')
DB_NAME = os.getenv('DATABASE_NAME', 'stempeluhr')
DB_USER = os.getenv('DATABASE_USER', 'stempeluhr')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD', '')
DATABASE_URL = URL.create(
    'postgresql+psycopg2', username=DB_USER, password=DB_PASSWORD,
    host=DB_HOST, port=int(DB_PORT), database=DB_NAME,
)


def engine():
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={'sslmode': 'disable'} if DB_HOST in {'127.0.0.1', 'localhost'} else {},
    )


def get_settings():
    try:
        with engine().begin() as conn:
            return {r[0]: r[1] for r in conn.execute(text('SELECT key, value FROM settings')).fetchall()}
    except Exception as exc:
        print(f'Warnung: Einstellungen konnten nicht gelesen werden: {exc}')
        return {}


def set_setting(key, value):
    try:
        with engine().begin() as conn:
            conn.execute(
                text('INSERT INTO settings (key,value) VALUES (:key,:value) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value'),
                {'key': key, 'value': value},
            )
    except Exception as exc:
        print(f'Warnung: Setting {key} konnte nicht gesetzt werden: {exc}')


def audit(action, details):
    try:
        with engine().begin() as conn:
            conn.execute(
                text("INSERT INTO audit_logs (actor,action,entity,entity_id,details,created_at) VALUES ('system',:action,'backup','',:details,NOW())"),
                {'action': action, 'details': details[:1000]},
            )
    except Exception as exc:
        print(f'Warnung: Audit nicht möglich: {exc}')


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def rotate(folder, keep):
    folder.mkdir(parents=True, exist_ok=True)
    for old in sorted(folder.glob('*.tar.gz'), key=lambda p: p.stat().st_mtime, reverse=True)[keep:]:
        try:
            old.unlink()
            sidecar = old.with_suffix(old.suffix + '.sha256')
            sidecar.unlink(missing_ok=True)
            audit('backup_rotated_deleted', str(old))
        except Exception as exc:
            print(f'Kann Backup nicht löschen {old}: {exc}')


def pg_dump_to(sql_path):
    env = os.environ.copy()
    env['PGPASSWORD'] = DB_PASSWORD
    env['PGSSLMODE'] = 'disable' if DB_HOST in {'127.0.0.1', 'localhost'} else env.get('PGSSLMODE', 'prefer')
    with sql_path.open('wb') as handle:
        result = subprocess.run(
            ['pg_dump', '--no-owner', '--no-privileges', '-h', DB_HOST, '-p', DB_PORT, '-U', DB_USER, DB_NAME],
            env=env, stdout=handle, stderr=subprocess.PIPE,
        )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode('utf-8', errors='ignore') or 'pg_dump fehlgeschlagen')
    if not sql_path.exists() or sql_path.stat().st_size == 0:
        raise RuntimeError('pg_dump hat eine leere Sicherungsdatei erzeugt')


def copy_to_smb(local_file, settings, kind):
    if settings.get('backup_target', 'local') not in ['smb', 'local_smb']:
        return None
    subpath = settings.get('backup_smb_path', '').strip().strip('/')
    mountpoint = Path(settings.get('backup_smb_mountpoint', '/mnt/stempeluhr_backup'))
    if not mountpoint.exists() or subprocess.run(['mountpoint', '-q', str(mountpoint)]).returncode != 0:
        raise RuntimeError(f'SMB-Mountpoint nicht eingebunden: {mountpoint}')
    dest_dir = mountpoint / subpath / kind if subpath else mountpoint / kind
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / local_file.name
    shutil.copy2(local_file, dest)
    sidecar = local_file.with_suffix(local_file.suffix + '.sha256')
    if sidecar.exists():
        shutil.copy2(sidecar, dest.with_suffix(dest.suffix + '.sha256'))
    return dest


def copy_config(work_dir):
    target = work_dir / 'config'
    target.mkdir(mode=0o700)
    if ENV_PATH.exists():
        shutil.copy2(ENV_PATH, target / 'stempeluhr.env')
    secrets = CONFIG_DIR / 'secrets'
    if secrets.exists():
        shutil.copytree(secrets, target / 'secrets', dirs_exist_ok=True)


def verify_archive(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError('Backup-Archiv fehlt oder ist leer')
    with tarfile.open(path, 'r:gz') as archive:
        names = archive.getnames()
        if not any(name.endswith('manifest.json') for name in names):
            raise RuntimeError('Backup enthält kein manifest.json')
        bad_member = archive.next()
        while bad_member is not None:
            if bad_member.name.startswith('/') or '..' in Path(bad_member.name).parts:
                raise RuntimeError(f'Unsicherer Archivpfad: {bad_member.name}')
            bad_member = archive.next()


def create_backup(kind='daily'):
    settings = get_settings()
    backup_path = Path(settings.get('backup_path', '/opt/stempeluhr/backups')).expanduser()
    for sub in ['daily', 'weekly', 'monthly', 'yearly']:
        (backup_path / sub).mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    stamp = now.strftime('%Y-%m-%d_%H-%M-%S')
    work_dir = Path('/tmp') / f'stempeluhr_backup_{stamp}'
    work_dir.mkdir(mode=0o700)

    try:
        included = {'database': False, 'config': False, 'uploads': False, 'docs': False, 'version': False}

        if settings.get('backup_include_database', 'true') == 'true' and DB_TYPE == 'postgresql':
            sql = work_dir / 'postgres.sql'
            pg_dump_to(sql)
            with sql.open('rb') as src, gzip.open(str(sql) + '.gz', 'wb') as dst:
                shutil.copyfileobj(src, dst)
            sql.unlink(missing_ok=True)
            included['database'] = True

        if settings.get('backup_include_config', 'true') == 'true':
            copy_config(work_dir)
            included['config'] = True

        if (APP_DIR / 'version.txt').exists():
            shutil.copy2(APP_DIR / 'version.txt', work_dir / 'version.txt')
            included['version'] = True

        if settings.get('backup_include_uploads', 'true') == 'true' and (APP_DIR / 'app/static/uploads').exists():
            shutil.copytree(APP_DIR / 'app/static/uploads', work_dir / 'uploads', dirs_exist_ok=True)
            included['uploads'] = True

        if (APP_DIR / 'docs').exists():
            shutil.copytree(APP_DIR / 'docs', work_dir / 'docs', dirs_exist_ok=True)
            included['docs'] = True

        manifest = {
            'format': 'stempeluhr-backup-v2',
            'created_at': now.isoformat(timespec='seconds'),
            'kind': kind,
            'application_version': (APP_DIR / 'version.txt').read_text(encoding='utf-8').strip() if (APP_DIR / 'version.txt').exists() else 'unknown',
            'database_type': DB_TYPE,
            'database_name': DB_NAME,
            'included': included,
        }
        (work_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        (work_dir / 'backup_info.txt').write_text(
            f'Stempeluhr Backup\nZeit: {now.isoformat(timespec="seconds")}\nTyp: {kind}\nDatenbank: {DB_NAME}\nFormat: v2\n',
            encoding='utf-8',
        )

        target = backup_path / kind / f'stempeluhr_{kind}_{stamp}.tar.gz'
        temp_target = target.with_suffix(target.suffix + '.part')
        with tarfile.open(temp_target, 'w:gz') as archive:
            archive.add(work_dir, arcname=f'stempeluhr_backup_{stamp}')
        os.chmod(temp_target, 0o600)
        verify_archive(temp_target)
        temp_target.replace(target)

        checksum = sha256_file(target)
        checksum_file = target.with_suffix(target.suffix + '.sha256')
        checksum_file.write_text(f'{checksum}  {target.name}\n', encoding='ascii')
        os.chmod(checksum_file, 0o600)

        created = [target]
        if kind == 'daily':
            if now.weekday() == 6:
                created.append(Path(shutil.copy2(target, backup_path / 'weekly' / f'stempeluhr_weekly_{now.strftime("%Y-W%U")}_{stamp}.tar.gz')))
            if now.day == 1:
                created.append(Path(shutil.copy2(target, backup_path / 'monthly' / f'stempeluhr_monthly_{now.strftime("%Y-%m")}_{stamp}.tar.gz')))
            if now.month == 1 and now.day == 1:
                created.append(Path(shutil.copy2(target, backup_path / 'yearly' / f'stempeluhr_yearly_{now.strftime("%Y")}_{stamp}.tar.gz')))

        for path in created:
            os.chmod(path, 0o600)
            if path != target:
                copy_checksum = path.with_suffix(path.suffix + '.sha256')
                copy_checksum.write_text(f'{sha256_file(path)}  {path.name}\n', encoding='ascii')
                os.chmod(copy_checksum, 0o600)
            dest = copy_to_smb(path, settings, path.parent.name)
            if dest:
                print(f'SMB-Kopie erstellt: {dest}')

        for folder, key, default in [
            ('daily', 'backup_daily_keep', '30'),
            ('weekly', 'backup_weekly_keep', '4'),
            ('monthly', 'backup_monthly_keep', '12'),
            ('yearly', 'backup_yearly_keep', '10'),
        ]:
            rotate(backup_path / folder, int(settings.get(key, default)))

        set_setting('backup_last_status', 'erfolgreich')
        set_setting('backup_last_time', now.strftime('%d.%m.%Y %H:%M:%S'))
        set_setting('backup_last_file', str(target))
        audit('backup_created', f'{target}; sha256={checksum}')
        print(f'Backup erstellt und geprüft: {target}')
        return 0
    except Exception as exc:
        set_setting('backup_last_status', f'fehlgeschlagen: {exc}')
        set_setting('backup_last_time', now.strftime('%d.%m.%Y %H:%M:%S'))
        audit('backup_failed', str(exc))
        print(f'Backup fehlgeschlagen: {exc}', file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == '__main__':
    selected = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    raise SystemExit(create_backup(selected if selected in ['daily', 'weekly', 'monthly', 'yearly'] else 'daily'))
