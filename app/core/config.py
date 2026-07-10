from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
BACKUP_DIR = Path(os.environ.get("STEMPELUHR_BACKUP_DIR", "/opt/stempeluhr/backups"))
SECRET_KEY = os.environ.get("STEMPELUHR_SECRET_KEY", "stempeluhr-change-me-2026-v4-3-0")
