from pathlib import Path
import os
import secrets

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
BACKUP_DIR = Path(os.environ.get("STEMPELUHR_BACKUP_DIR", "/opt/stempeluhr/backups"))

# Datei, in der der generierte Schlüssel abgelegt wird, falls die
# Umgebungsvariable fehlt. Liegt neben der übrigen Konfiguration und
# bleibt über Neustarts hinweg stabil.
SECRET_KEY_FILE = Path(
    os.environ.get(
        "STEMPELUHR_SECRET_KEY_FILE",
        "/var/lib/stempeluhr/secret_key",
    )
)

# Frühere Versionen nutzten einen festen, im Quelltext sichtbaren Schlüssel.
# Damit waren Session-Cookies fälschbar. Diese Werte gelten als
# unsicher und werden nicht mehr verwendet.
INSECURE_SECRET_KEYS = frozenset({
    "stempeluhr-change-me-2026-v4-3-0",
    "stempeluhr-change-me",
    "change-me",
    "changeme",
    "secret",
})


def _generate_secret_key() -> str:
    """Erzeugt einen zufälligen Schlüssel und legt ihn persistent ab.

    Der Schlüssel wird nur einmal erzeugt. Beim nächsten Start wird er
    aus der Datei gelesen, damit bestehende Sessions gültig bleiben.
    """
    key = secrets.token_urlsafe(48)
    try:
        SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        SECRET_KEY_FILE.write_text(key, encoding="utf-8")
        os.chmod(SECRET_KEY_FILE, 0o600)
    except OSError:
        # Ohne Schreibrecht bleibt der Key nur fuer diesen Start
        # gueltig. Das ist besser als ein vorhersagbarer Schluessel,
        # fuehrt aber zu einem Neustart-Verlust der Sessions.
        pass
    return key


def _load_secret_key() -> str:
    """Laedt den Session-Schluessel aus der Umgebung oder aus der Datei."""
    env_key = os.environ.get("STEMPELUHR_SECRET_KEY", "").strip()
    if env_key and env_key not in INSECURE_SECRET_KEYS:
        return env_key

    try:
        stored = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        stored = ""
    if stored and stored not in INSECURE_SECRET_KEYS:
        return stored

    return _generate_secret_key()


SECRET_KEY = _load_secret_key()
SECRET_KEY_IS_INSECURE = SECRET_KEY in INSECURE_SECRET_KEYS
