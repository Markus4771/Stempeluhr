from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    permissions = Column(Text)


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    description = Column(Text)
    manager_employee_id = Column(Integer, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    employee_number = Column(String(20), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255))
    phone = Column(String(100))
    birth_date = Column(Date, nullable=True)
    entry_date = Column(Date, nullable=True)
    rfid_code = Column(String(100), unique=True)
    password_hash = Column(String(255))
    pin_code_hash = Column(String(255))
    role_id = Column(Integer, ForeignKey("roles.id"))
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_admin = Column(Boolean, default=False)
    can_self_correct = Column(Boolean, default=False)
    can_self_manage = Column(Boolean, default=False)
    plausibility_check_enabled = Column(Boolean, default=True)
    auto_break_enabled = Column(Boolean, default=True)
    weekly_hours = Column(Float, default=40.0)
    daily_hours = Column(Float, default=8.0)
    monday_hours = Column(Float, default=8.0)
    tuesday_hours = Column(Float, default=8.0)
    wednesday_hours = Column(Float, default=8.0)
    thursday_hours = Column(Float, default=8.0)
    friday_hours = Column(Float, default=8.0)
    saturday_hours = Column(Float, default=0.0)
    sunday_hours = Column(Float, default=0.0)
    vacation_days_total = Column(Float, default=30.0)
    vacation_days_used = Column(Float, default=0.0)
    vacation_days_remaining = Column(Float, default=30.0)
    sick_days = Column(Float, default=0.0)
    overtime_balance = Column(Float, default=0.0)
    active = Column(Boolean, default=True)
    status = Column(String(20), default="active")
    exit_date = Column(Date, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    offboarding_note = Column(Text, nullable=True)
    hired_at = Column(Date)
    left_at = Column(Date)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    onboarding_invited_at = Column(DateTime, nullable=True)
    onboarding_completed_at = Column(DateTime, nullable=True)
    privacy_accepted_at = Column(DateTime, nullable=True)
    privacy_version_accepted = Column(String(50), nullable=True)
    role = relationship("Role")
    department = relationship("Department", foreign_keys=[department_id])
    entries = relationship("TimeEntry", back_populates="employee")

class Terminal(Base):
    __tablename__ = "terminals"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    location = Column(String(255))
    terminal_code = Column(String(100), unique=True, nullable=True)
    api_key = Column(String(255))
    active = Column(Boolean, default=True)
    offline_buffer_enabled = Column(Boolean, default=True)
    description = Column(Text)
    last_seen = Column(DateTime)
    last_ip = Column(String(100))
    app_version = Column(String(50))
    time_sync_enabled = Column(Boolean, default=True)
    last_time_sync = Column(DateTime)
    time_offset_seconds = Column(Float)
    time_status = Column(String(50))
    time_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    customer = Column(String(255))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class TimeEntry(Base):
    __tablename__ = "time_entries"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    entry_type = Column(String(30), nullable=False)
    method = Column(String(30), nullable=False)
    terminal = Column(String(100))
    terminal_id = Column(Integer, ForeignKey("terminals.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    note = Column(Text)
    corrected = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(100), nullable=True)
    delete_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    employee = relationship("Employee", back_populates="entries")

class WorkTimeAccount(Base):
    __tablename__ = "work_time_accounts"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    target_hours = Column(Float, default=0.0)
    actual_hours = Column(Float, default=0.0)
    break_hours = Column(Float, default=0.0)
    overtime_hours = Column(Float, default=0.0)
    minus_hours = Column(Float, default=0.0)
    vacation_days = Column(Float, default=0.0)
    sick_days = Column(Float, default=0.0)
    locked = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.now)

class SickLeave(Base):
    __tablename__ = "sick_leaves"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Float, default=0.0)
    with_certificate = Column(Boolean, default=False)
    child_sick = Column(Boolean, default=False)
    work_accident = Column(Boolean, default=False)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Correction(Base):
    __tablename__ = "corrections"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    time_entry_id = Column(Integer, ForeignKey("time_entries.id"))
    old_value = Column(Text)
    new_value = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), default="genehmigt")
    changed_by = Column(String(100), nullable=False)
    changed_at = Column(DateTime, default=datetime.now, nullable=False)

class Holiday(Base):
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    federal_state = Column(String(50), default="BY")
    half_day = Column(Boolean, default=False)
    active = Column(Boolean, default=True)

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    license_plate = Column(String(50), unique=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class VehicleLog(Base):
    __tablename__ = "vehicle_logs"
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    km_start = Column(Integer)
    km_end = Column(Integer)
    purpose = Column(Text)
    customer = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)

class ApiToken(Base):
    __tablename__ = "api_tokens"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    role = Column(String(100), default="api")
    permissions = Column(Text, default="read")
    active = Column(Boolean, default=True)
    allowed_ips = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_used_at = Column(DateTime)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor = Column(String(100))
    action = Column(String(100), nullable=False)
    entity = Column(String(100))
    entity_id = Column(String(100))
    details = Column(Text)
    ip_address = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)




class DsgvoLog(Base):
    __tablename__ = "dsgvo_logs"
    id = Column(Integer, primary_key=True)
    action = Column(String(100), nullable=False)
    data_type = Column(String(100), nullable=False)
    record_id = Column(String(100))
    employee_id = Column(Integer, nullable=True)
    actor = Column(String(100), default="SYSTEM")
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class PlausibilityIssue(Base):
    __tablename__ = "plausibility_issues"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    issue_date = Column(Date, nullable=False)
    check_type = Column(String(100), nullable=False)
    severity = Column(String(20), default="gelb")
    message = Column(Text, nullable=False)
    status = Column(String(30), default="offen")
    notified_employee_at = Column(DateTime, nullable=True)
    notified_teamlead_at = Column(DateTime, nullable=True)
    comment = Column(Text)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    employee = relationship("Employee", foreign_keys=[employee_id])




class MailDispatchLog(Base):
    __tablename__ = "mail_dispatch_log"
    id = Column(Integer, primary_key=True)
    dispatch_date = Column(Date, nullable=False)
    dispatch_type = Column(String(100), nullable=False)
    recipient = Column(String(255), nullable=True)
    recipient_employee_id = Column(Integer, nullable=True)
    status = Column(String(50), default="started")
    issues_count = Column(Integer, default=0)
    details = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

class AbsenceType(Base):
    __tablename__ = "absence_types"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    active = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=True)
    requires_text = Column(Boolean, default=False)
    sort_order = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

class VacationRequest(Base):
    __tablename__ = "vacation_requests"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Float, default=0)
    half_day = Column(Boolean, default=False)

    request_type = Column(String(50), default="abwesenheit")
    custom_reason = Column(Text, nullable=True)
    status = Column(String(50), default="beantragt")

    comment = Column(Text)
    decision_comment = Column(Text)

    requested_at = Column(DateTime, default=datetime.now)
    decided_at = Column(DateTime)
    decided_by = Column(String(100))

    employee = relationship("Employee", foreign_keys=[employee_id])



class OnboardingToken(Base):
    __tablename__ = "onboarding_tokens"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    requested_by = Column(String(100), nullable=True)
    requested_ip = Column(String(100), nullable=True)
    status = Column(String(50), default="created")
    error_message = Column(Text, nullable=True)
    employee = relationship("Employee", foreign_keys=[employee_id])


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    requested_ip = Column(String(100), nullable=True)
    employee = relationship("Employee", foreign_keys=[employee_id])


class RaspberryClient(Base):
    __tablename__ = "raspberry_clients"
    id = Column(Integer, primary_key=True)
    hostname = Column(String(150), unique=True, nullable=False)
    ip_address = Column(String(100))
    agent_version = Column(String(50))
    app_version = Column(String(50))
    debian_version = Column(String(200))
    chromium_running = Column(Boolean, default=False)
    kiosk_url = Column(Text)
    fullscreen = Column(Boolean, default=False)
    wayland_display = Column(String(100))
    display_name = Column(String(100))
    cpu_percent = Column(Float, default=0.0)
    ram_percent = Column(Float, default=0.0)
    temperature = Column(String(50))
    uptime = Column(String(100))
    last_seen = Column(DateTime, default=datetime.now)
    last_screenshot_path = Column(Text)
    last_log = Column(Text)
    pending_command = Column(String(100))
    command_requested_at = Column(DateTime)
    command_result = Column(Text)
    command_finished_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
