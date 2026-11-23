from pydantic import BaseModel
from typing import Optional


class ClockRequest(BaseModel):
    # Neue generische 6.x-Felder.
    auth_provider: Optional[str] = None
    auth_credential: Optional[str] = None

    # Abwärtskompatibilität für bestehende RFID-Terminals und Integrationen.
    rfid_code: Optional[str] = None
    employee_number: Optional[str] = None
    password: Optional[str] = None

    entry_type: str
    terminal: Optional[str] = "web"
    terminal_id: Optional[int] = None
    note: Optional[str] = None


class EmployeeCreate(BaseModel):
    employee_number: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    rfid_code: Optional[str] = None
    password: Optional[str] = None


class CorrectionCreate(BaseModel):
    employee_id: int
    old_value: Optional[str] = None
    new_value: str
    reason: str
    changed_by: str = "admin"


class SettingUpdate(BaseModel):
    key: str
    value: str
