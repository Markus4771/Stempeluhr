from __future__ import annotations

import ipaddress
from typing import Iterable

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import Setting

LOCAL_CIDRS = ["127.0.0.1/32", "::1/128"]


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    if not row or row.value is None:
        return default
    return str(row.value)


def _is_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "on", "ja", "yes", "aktiv"}


def parse_cidr_list(raw: str | None, include_localhost: bool = True) -> list[ipaddress._BaseNetwork]:
    """Parst kommagetrennte CIDR-Netze. Ungültige Einträge lösen ValueError aus."""
    items: list[str] = []
    if raw:
        for part in str(raw).replace("\n", ",").replace(";", ",").split(","):
            value = part.strip()
            if value:
                items.append(value)
    if include_localhost:
        for local in LOCAL_CIDRS:
            if local not in items:
                items.append(local)
    networks = []
    for item in items:
        networks.append(ipaddress.ip_network(item, strict=False))
    return networks


def client_ip(request: Request) -> str:
    """Ermittelt Client-IP. Bei Reverse Proxy X-Forwarded-For zuerst verwenden."""
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    real_ip = request.headers.get("x-real-ip") or ""
    if real_ip.strip():
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


def in_networks(ip_value: str, networks: Iterable[ipaddress._BaseNetwork]) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip_value)
    except ValueError:
        return False
    return any(ip_obj in net for net in networks)


def validate_cidr_text(raw: str | None) -> tuple[bool, str]:
    try:
        parse_cidr_list(raw, include_localhost=False)
        return True, ""
    except ValueError as exc:
        return False, str(exc)


def https_should_redirect(request: Request, db: Session) -> bool:
    if not _is_enabled(_get_setting(db, "security_force_https", "false")):
        return False
    if request.url.path.startswith("/health") or request.url.path.startswith("/static"):
        return False
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return str(proto).lower() != "https"


def access_allowed(request: Request, db: Session) -> tuple[bool, str]:
    """Prüft Web/API/Admin-Netzfilter. Gibt (erlaubt, Grund) zurück."""
    path = request.url.path or "/"
    ip = client_ip(request)

    # Healthcheck und lokale statische Dateien immer erlauben.
    if path.startswith("/health") or path.startswith("/static"):
        return True, "ok"

    # Allgemeiner Netzwerkfilter.
    if _is_enabled(_get_setting(db, "security_network_filter_enabled", "false")):
        raw = _get_setting(db, "security_allowed_networks", "")
        try:
            networks = parse_cidr_list(raw)
        except ValueError:
            return False, "Netzwerkfilter-Konfiguration ungültig"
        if not in_networks(ip, networks):
            return False, f"IP {ip} ist nicht in den erlaubten Netzwerken"

    # API separat einschränken.
    if path.startswith("/api") and _is_enabled(_get_setting(db, "security_api_network_filter_enabled", "false")):
        raw = _get_setting(db, "security_api_allowed_networks", "")
        try:
            networks = parse_cidr_list(raw)
        except ValueError:
            return False, "API-Netzwerkfilter-Konfiguration ungültig"
        if not in_networks(ip, networks):
            return False, f"API-Zugriff von {ip} nicht erlaubt"

    # Admin/Systembereiche separat einschränken.
    admin_paths = ("/admin", "/system", "/reports", "/corrections")
    if path.startswith(admin_paths) and _is_enabled(_get_setting(db, "security_admin_network_filter_enabled", "false")):
        raw = _get_setting(db, "security_admin_allowed_networks", "")
        try:
            networks = parse_cidr_list(raw)
        except ValueError:
            return False, "Admin-Netzwerkfilter-Konfiguration ungültig"
        if not in_networks(ip, networks):
            return False, f"Admin-Zugriff von {ip} nicht erlaubt"

    return True, "ok"
