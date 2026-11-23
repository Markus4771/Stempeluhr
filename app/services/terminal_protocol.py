from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database import Base, engine

PROTOCOL_VERSION = "1.0"
KNOWN_CAPABILITIES = {
    "display",
    "rfid",
    "nfc",
    "qr",
    "barcode",
    "pin",
    "fingerprint",
    "camera",
    "speaker",
    "buzzer",
    "led",
    "relay",
    "bluetooth",
    "offline_buffer",
}


class TerminalCapability(Base):
    __tablename__ = "terminal_capabilities"
    __table_args__ = (UniqueConstraint("terminal_id", "capability", name="ux_terminal_capability"),)

    id = Column(Integer, primary_key=True)
    terminal_id = Column(Integer, ForeignKey("terminals.id", ondelete="CASCADE"), nullable=False, index=True)
    capability = Column(String(80), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    details = Column(Text, nullable=True)
    detected_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


def ensure_terminal_protocol_schema() -> None:
    Base.metadata.create_all(bind=engine, tables=[TerminalCapability.__table__])


def normalize_capabilities(values: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not isinstance(values, list):
        return result
    for item in values:
        if isinstance(item, str):
            name = item.strip().lower()
            details = None
            enabled = True
        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("capability") or "").strip().lower()
            details = item.get("details")
            enabled = bool(item.get("enabled", True))
        else:
            continue
        if not name or name in seen:
            continue
        seen.add(name)
        result.append({"name": name, "enabled": enabled, "details": details})
    return result


def protocol_response(*, terminal_id: int, command: str | None = None) -> dict[str, Any]:
    return {
        "status": "ok",
        "protocol_version": PROTOCOL_VERSION,
        "terminal_id": terminal_id,
        "server_time": datetime.now().isoformat(timespec="seconds"),
        "command": command,
    }
