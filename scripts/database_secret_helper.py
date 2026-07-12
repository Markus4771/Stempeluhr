#!/usr/bin/env python3
"""Privilegierter Helfer zum atomaren Ändern des lokalen PostgreSQL-Passworts.

Das Skript wird ausschließlich über einen eng begrenzten sudoers-Eintrag aufgerufen.
Es schreibt niemals Passwörter in stdout oder Logs.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CONFIG_DIR = Path("/etc/stempeluhr")
ENV_FILE = CONFIG_DIR / "stempeluhr.env"
SECRETS_DIR = CONFIG_DIR / "secrets"
DB_SECRET_FILE = SECRETS_DIR / "database.conf"
BACKUP_DIR = CONFIG_DIR / "backup-secrets"
ALLOWED_USER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def read_payload(path: Path) -> dict:
    st = path.stat()
    if not path.is_file() or st.st_mode & 0o077:
        fail("Übergabedatei muss eine geschützte reguläre Datei sein.")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_atomic(path: Path, content: str, mode: int = 0o640) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        shutil.chown(temp, user="root", group="stempeluhr")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def remove_password_from_env() -> None:
    if not ENV_FILE.exists():
        return
    lines = []
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if raw.strip().startswith("DATABASE_PASSWORD="):
            continue
        lines.append(raw)
    write_atomic(ENV_FILE, "\n".join(lines).rstrip() + "\n")


def alter_role(user: str, password: str) -> None:
    env = os.environ.copy()
    env["PGOPTIONS"] = "-c password_encryption=scram-sha-256"
    sql = "ALTER ROLE \"{}\" WITH LOGIN PASSWORD %s".format(user.replace('"', '""'))
    subprocess.run(
        ["runuser", "-u", "postgres", "--", "psql", "-v", "ON_ERROR_STOP=1", "postgres", "-c", sql],
        input=password + "\n",
        text=True,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def test_connection(host: str, port: str, database: str, user: str, password: str) -> None:
    env = os.environ.copy()
    env.update({"PGPASSWORD": password, "PGSSLMODE": "disable"})
    subprocess.run(
        ["psql", "-h", host, "-p", port, "-U", user, "-d", database, "-tAc", "SELECT 1"],
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=20,
    )


def main() -> None:
    if os.geteuid() != 0:
        fail("Dieses Skript muss als root ausgeführt werden.")
    if len(sys.argv) != 2:
        fail("Aufruf: database_secret_helper.py <geschützte-json-datei>")

    payload_path = Path(sys.argv[1]).resolve()
    allowed_root = Path("/var/lib/stempeluhr/tmp").resolve()
    if allowed_root not in payload_path.parents:
        fail("Ungültiger Übergabepfad.")

    payload = read_payload(payload_path)
    user = str(payload.get("user") or "stempeluhr")
    database = str(payload.get("database") or "stempeluhr")
    host = str(payload.get("host") or "127.0.0.1")
    port = str(payload.get("port") or "5432")
    password = str(payload.get("password") or "")

    if host not in {"127.0.0.1", "localhost"}:
        fail("Passwortänderung ist nur für die lokale PostgreSQL-Datenbank zulässig.")
    if not ALLOWED_USER.fullmatch(user) or not ALLOWED_USER.fullmatch(database):
        fail("Ungültiger Datenbankname oder Benutzername.")
    if len(password) < 16 or len(password) > 256:
        fail("Das Datenbankpasswort muss 16 bis 256 Zeichen lang sein.")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(BACKUP_DIR, 0o700)
    if ENV_FILE.exists():
        shutil.copy2(ENV_FILE, BACKUP_DIR / "stempeluhr.env.before-db-password")
    if DB_SECRET_FILE.exists():
        shutil.copy2(DB_SECRET_FILE, BACKUP_DIR / "database.conf.before-db-password")

    old_secret = DB_SECRET_FILE.read_text(encoding="utf-8") if DB_SECRET_FILE.exists() else None
    try:
        alter_role(user, password)
        test_connection(host, port, database, user, password)
        secret = f"DATABASE_PASSWORD={password}\n"
        write_atomic(DB_SECRET_FILE, secret)
        remove_password_from_env()
    except Exception as exc:
        if old_secret is not None:
            write_atomic(DB_SECRET_FILE, old_secret)
        fail(f"Datenbankpasswort konnte nicht sicher geändert werden: {type(exc).__name__}")


if __name__ == "__main__":
    main()
