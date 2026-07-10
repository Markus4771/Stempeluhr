#!/usr/bin/env python3
"""Restore-Werkzeug für Stempeluhr Backups.

Stellt ausgewählte Bereiche aus einer von backup_gfs.py erzeugten .tar.gz-Datei wieder her.
Die Ausführung sollte als root/sudo erfolgen, weil /opt/stempeluhr und PostgreSQL-Zugriff benötigt werden.
"""
import argparse
import gzip
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path("/opt/stempeluhr")
ENV_PATH = APP_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DB_HOST = os.getenv("DATABASE_HOST", "127.0.0.1")
DB_PORT = os.getenv("DATABASE_PORT", "5432")
DB_NAME = os.getenv("DATABASE_NAME", "stempeluhr")
DB_USER = os.getenv("DATABASE_USER", "stempeluhr")
DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "stempeluhr_passwort_aendern")


def safe_extract(tar: tarfile.TarFile, target: Path) -> None:
    """Verhindert Path-Traversal beim Entpacken."""
    target_resolved = target.resolve()
    for member in tar.getmembers():
        member_path = (target / member.name).resolve()
        if not str(member_path).startswith(str(target_resolved)):
            raise RuntimeError(f"Unsicherer Pfad im Backup: {member.name}")
    tar.extractall(target)


def find_first(root: Path, name: str):
    for p in root.rglob(name):
        return p
    return None


def find_dir(root: Path, name: str):
    for p in root.rglob(name):
        if p.is_dir() and p.name == name:
            return p
    return None


def restore_database(extracted_root: Path) -> None:
    sql_gz = find_first(extracted_root, "postgres.sql.gz")
    if not sql_gz:
        raise RuntimeError("Im Backup wurde keine postgres.sql.gz gefunden.")

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    # Bestehende Verbindungen trennen und Datenbank leeren.
    terminate_sql = (
        "SELECT pg_terminate_backend(pid) "
        "FROM pg_stat_activity "
        "WHERE datname = current_database() AND pid <> pg_backend_pid();"
    )
    subprocess.run(
        ["psql", "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, "-d", DB_NAME, "-c", terminate_sql],
        env=env,
        check=True,
    )
    drop_sql = "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    subprocess.run(
        ["psql", "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, "-d", DB_NAME, "-c", drop_sql],
        env=env,
        check=True,
    )

    psql = subprocess.Popen(
        ["psql", "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, "-d", DB_NAME],
        env=env,
        stdin=subprocess.PIPE,
    )
    with gzip.open(sql_gz, "rb") as src:
        shutil.copyfileobj(src, psql.stdin)
    psql.stdin.close()
    rc = psql.wait()
    if rc != 0:
        raise RuntimeError("psql Restore ist fehlgeschlagen.")


def copy_replace(src: Path, dst: Path) -> None:
    if not src.exists():
        raise RuntimeError(f"Quelle fehlt: {src}")
    if dst.exists():
        backup = dst.with_name(dst.name + ".before_restore")
        if backup.exists():
            if backup.is_dir():
                shutil.rmtree(backup)
            else:
                backup.unlink()
        if dst.is_dir():
            shutil.move(str(dst), str(backup))
        else:
            shutil.move(str(dst), str(backup))
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stempeluhr Backup wiederherstellen")
    parser.add_argument("backup_file", help="Pfad zur .tar.gz Backup-Datei")
    parser.add_argument("--database", action="store_true")
    parser.add_argument("--no-database", action="store_true")
    parser.add_argument("--config", action="store_true")
    parser.add_argument("--no-config", action="store_true")
    parser.add_argument("--uploads", action="store_true")
    parser.add_argument("--no-uploads", action="store_true")
    parser.add_argument("--docs", action="store_true")
    parser.add_argument("--no-docs", action="store_true")
    args = parser.parse_args()

    backup_file = Path(args.backup_file)
    allowed_root = Path("/opt/stempeluhr/backups").resolve()
    if not backup_file.exists() or not backup_file.is_file():
        print("Backup-Datei existiert nicht.", file=sys.stderr)
        return 2
    if not str(backup_file.resolve()).startswith(str(allowed_root)):
        print("Backup-Datei liegt nicht im erlaubten Backup-Verzeichnis.", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="stempeluhr_restore_") as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(backup_file, "r:gz") as tar:
            safe_extract(tar, tmp_path)

        if args.database:
            restore_database(tmp_path)
            print("Datenbank wiederhergestellt.")

        if args.config:
            env_file = find_first(tmp_path, ".env")
            if not env_file:
                raise RuntimeError("Keine .env im Backup gefunden.")
            copy_replace(env_file, APP_DIR / ".env")
            print("Konfiguration wiederhergestellt.")

        if args.uploads:
            uploads = find_dir(tmp_path, "uploads")
            if not uploads:
                raise RuntimeError("Kein uploads-Ordner im Backup gefunden.")
            copy_replace(uploads, APP_DIR / "app/static/uploads")
            print("Uploads wiederhergestellt.")

        if args.docs:
            docs = find_dir(tmp_path, "docs")
            if not docs:
                raise RuntimeError("Kein docs-Ordner im Backup gefunden.")
            copy_replace(docs, APP_DIR / "docs")
            print("Dokumentation wiederhergestellt.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Restore fehlgeschlagen: {exc}", file=sys.stderr)
        raise SystemExit(1)
