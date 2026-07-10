from sqlalchemy.orm import Session
from app.models import Setting

SETTING_KEY = "employee_number_length"
DEFAULT_LENGTH = 4
MIN_LENGTH = 1
MAX_LENGTH = 20


def ensure_employee_number_length_setting(db: Session) -> None:
    row = db.query(Setting).filter(Setting.key == SETTING_KEY).first()
    if not row:
        db.add(Setting(key=SETTING_KEY, value=str(DEFAULT_LENGTH)))
        db.commit()


def clamp_employee_number_length(value) -> int:
    try:
        length = int(value or DEFAULT_LENGTH)
    except Exception:
        length = DEFAULT_LENGTH
    return max(MIN_LENGTH, min(length, MAX_LENGTH))


def get_employee_number_length(db: Session) -> int:
    ensure_employee_number_length_setting(db)
    row = db.query(Setting).filter(Setting.key == SETTING_KEY).first()
    return clamp_employee_number_length(row.value if row else DEFAULT_LENGTH)


def normalize_employee_number(value: str, length: int) -> str:
    value = (value or "").strip()
    if value.isdigit():
        return value.zfill(length)
    return value


def validate_employee_number(value: str, length: int):
    value = (value or "").strip()
    if not value:
        return False, "Mitarbeiternummer darf nicht leer sein."
    if not value.isdigit():
        return False, "Mitarbeiternummer darf nur aus Zahlen bestehen."
    if len(value) != length:
        return False, f"Mitarbeiternummer muss genau {length} Stellen haben."
    return True, ""
