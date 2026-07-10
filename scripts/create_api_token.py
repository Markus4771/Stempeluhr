#!/usr/bin/env python3
"""Erzeugt einen API-Key für die Stempeluhr.

Aufruf auf dem Raspberry:
  cd /opt/stempeluhr
  sudo -u stempeluhr .venv/bin/python scripts/create_api_token.py n8n

Der API-Key wird nur einmal angezeigt. In der Datenbank wird nur SHA256 gespeichert.
"""
import hashlib
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import ApiToken, Setting  # noqa: E402


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "api"
    raw = "sk_stempeluhr_" + secrets.token_urlsafe(32)
    db = SessionLocal()
    try:
        row = ApiToken(name=name, token=token_hash(raw), role="api", active=True)
        db.add(row)
        setting = db.query(Setting).filter(Setting.key == "api_enabled").first()
        if not setting:
            db.add(Setting(key="api_enabled", value="true"))
        elif str(setting.value).lower() not in {"true", "1", "ja", "yes", "on"}:
            setting.value = "true"
        db.commit()
        print("API-Key erstellt")
        print("Name:", name)
        print("Key:", raw)
        print("Wichtig: Diesen Key jetzt speichern. Er wird nicht erneut angezeigt.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
