from sqlalchemy.orm import Session
from app.models import Setting


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row and row.value is not None else default


def set_setting(db: Session, key: str, value: str) -> Setting:
    row = db.query(Setting).filter(Setting.key == key).first()
    if not row:
        row = Setting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    return row


def settings_dict(db: Session) -> dict[str, str]:
    return {s.key: s.value for s in db.query(Setting).all()}
