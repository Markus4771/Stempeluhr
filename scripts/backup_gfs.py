#!/usr/bin/env python3
import gzip
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

APP_DIR = Path("/opt/stempeluhr")
ENV_PATH = APP_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DB_TYPE = os.getenv("DATABASE_TYPE", "postgresql").lower()
DB_HOST = os.getenv("DATABASE_HOST", "127.0.0.1")
DB_PORT = os.getenv("DATABASE_PORT", "5432")
DB_NAME = os.getenv("DATABASE_NAME", "stempeluhr")
DB_USER = os.getenv("DATABASE_USER", "stempeluhr")
DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "stempeluhr_passwort_aendern")
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)

def get_settings():
    try:
        with engine().begin() as conn:
            rows = conn.execute(text("SELECT key, value FROM settings")).fetchall()
            return {r[0]: r[1] for r in rows}
    except Exception as exc:
        print(f"Warnung: Einstellungen konnten nicht gelesen werden: {exc}")
        return {}

def set_setting(key, value):
    try:
        with engine().begin() as conn:
            conn.execute(text("""
                INSERT INTO settings (key, value)
                VALUES (:key, :value)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """), {"key": key, "value": value})
    except Exception as exc:
        print(f"Warnung: Setting {key} konnte nicht gesetzt werden: {exc}")

def audit(action, details):
    try:
        with engine().begin() as conn:
            conn.execute(text("""
                INSERT INTO audit_logs (actor, action, entity, entity_id, details, created_at)
                VALUES ('system', :action, 'backup', '', :details, NOW())
            """), {"action": action, "details": details[:1000]})
    except Exception as exc:
        print(f"Warnung: Audit nicht möglich: {exc}")

def rotate(folder: Path, keep: int):
    folder.mkdir(parents=True, exist_ok=True)
    files = sorted(folder.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink()
            audit("backup_rotated_deleted", str(old))
        except Exception as exc:
            print(f"Kann Backup nicht löschen {old}: {exc}")

def pg_dump_to(sql_path: Path):
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    cmd = ["pg_dump", "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, DB_NAME]
    with sql_path.open("wb") as f:
        result = subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="ignore") or "pg_dump fehlgeschlagen")

def copy_to_smb(local_file: Path, settings: dict, kind: str):
    if settings.get("backup_target", "local") not in ["smb", "local_smb"]:
        return None

    subpath = settings.get("backup_smb_path", "").strip().strip("/")
    mountpoint = Path(settings.get("backup_smb_mountpoint", "/mnt/stempeluhr_backup"))

    if not mountpoint.exists():
        raise RuntimeError(f"SMB-Mountpoint existiert nicht: {mountpoint}. Bitte SMB-Verbindung testen/speichern.")

    if subprocess.run(["mountpoint", "-q", str(mountpoint)]).returncode != 0:
        raise RuntimeError(f"SMB-Mountpoint ist nicht eingebunden: {mountpoint}. Bitte SMB-Verbindung testen/speichern.")

    dest_dir = mountpoint / subpath / kind if subpath else mountpoint / kind
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / local_file.name
    shutil.copy2(local_file, dest)
    return dest

def create_backup(kind="daily"):
    settings = get_settings()
    backup_path = Path(settings.get("backup_path", "/opt/stempeluhr/backups"))
    for sub in ["daily", "weekly", "monthly", "yearly"]:
        (backup_path / sub).mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    work_dir = Path("/tmp") / f"stempeluhr_backup_{stamp}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        if settings.get("backup_include_database", "true") == "true" and DB_TYPE == "postgresql":
            sql_path = work_dir / "postgres.sql"
            pg_dump_to(sql_path)
            with sql_path.open("rb") as src, gzip.open(str(sql_path) + ".gz", "wb") as dst:
                shutil.copyfileobj(src, dst)
            sql_path.unlink(missing_ok=True)

        if settings.get("backup_include_config", "true") == "true" and ENV_PATH.exists():
            shutil.copy2(ENV_PATH, work_dir / ".env")

        if (APP_DIR / "version.txt").exists():
            shutil.copy2(APP_DIR / "version.txt", work_dir / "version.txt")

        if settings.get("backup_include_uploads", "true") == "true" and (APP_DIR / "app/static/uploads").exists():
            shutil.copytree(APP_DIR / "app/static/uploads", work_dir / "uploads", dirs_exist_ok=True)

        if (APP_DIR / "docs").exists():
            shutil.copytree(APP_DIR / "docs", work_dir / "docs", dirs_exist_ok=True)

        (work_dir / "backup_info.txt").write_text(
            f"Stempeluhr Backup\nZeit: {now.isoformat(timespec='seconds')}\nTyp: {kind}\nDatenbank: {DB_NAME}\n",
            encoding="utf-8"
        )

        target = backup_path / kind / f"stempeluhr_{kind}_{stamp}.tar.gz"
        with tarfile.open(target, "w:gz") as tar:
            tar.add(work_dir, arcname=f"stempeluhr_backup_{stamp}")

        created = [target]

        if kind == "daily":
            if now.weekday() == 6:
                weekly = backup_path / "weekly" / f"stempeluhr_weekly_{now.strftime('%Y-W%U')}_{stamp}.tar.gz"
                shutil.copy2(target, weekly)
                created.append(weekly)
            if now.day == 1:
                monthly = backup_path / "monthly" / f"stempeluhr_monthly_{now.strftime('%Y-%m')}_{stamp}.tar.gz"
                shutil.copy2(target, monthly)
                created.append(monthly)
            if now.month == 1 and now.day == 1:
                yearly = backup_path / "yearly" / f"stempeluhr_yearly_{now.strftime('%Y')}_{stamp}.tar.gz"
                shutil.copy2(target, yearly)
                created.append(yearly)

        for f in list(created):
            smb_dest = copy_to_smb(f, settings, f.parent.name)
            if smb_dest:
                print(f"SMB-Kopie erstellt: {smb_dest}")

        rotate(backup_path / "daily", int(settings.get("backup_daily_keep", "30")))
        rotate(backup_path / "weekly", int(settings.get("backup_weekly_keep", "4")))
        rotate(backup_path / "monthly", int(settings.get("backup_monthly_keep", "12")))
        rotate(backup_path / "yearly", int(settings.get("backup_yearly_keep", "10")))

        set_setting("backup_last_status", "erfolgreich")
        set_setting("backup_last_time", now.strftime("%d.%m.%Y %H:%M:%S"))
        set_setting("backup_last_file", str(target))
        audit("backup_created", str(target))
        print(f"Backup erstellt: {target}")
        return 0

    except Exception as exc:
        msg = f"fehlgeschlagen: {exc}"
        set_setting("backup_last_status", msg)
        set_setting("backup_last_time", now.strftime("%d.%m.%Y %H:%M:%S"))
        audit("backup_failed", msg)
        print(f"Backup fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if kind not in ["daily", "weekly", "monthly", "yearly"]:
        kind = "daily"
    raise SystemExit(create_backup(kind))
