"""Regression tests for legacy API disclosure and spoofed network headers."""
import hashlib
import os
from datetime import date, datetime, timedelta

os.environ.setdefault("DATABASE_TYPE", "sqlite")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.database import Base, get_db
from app.models import ApiToken, Employee, Setting
from app.routes.api import router
from app.services.network_security import access_allowed


@pytest.fixture
def api_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Employee(employee_number="E001", first_name="Test", last_name="Person", birth_date=date(1990, 1, 1)))
        db.add(Setting(key="api_enabled", value="true"))
        db.add(ApiToken(name="Test", token=hashlib.sha256(b"valid-key").hexdigest()))
        db.commit()
        app = FastAPI()
        app.include_router(router)

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        with TestClient(app) as client:
            yield client, db
    engine.dispose()


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
def test_legacy_employees_requires_valid_key(api_client, headers):
    client, _ = api_client
    response = client.get("/api/employees", headers=headers)
    assert response.status_code == 401
    assert "birth_date" not in response.text


def test_legacy_employees_respects_api_disabled(api_client):
    client, db = api_client
    db.query(Setting).filter_by(key="api_enabled").one().value = "false"
    db.commit()
    assert client.get("/api/employees", headers={"X-API-Key": "valid-key"}).status_code == 403


@pytest.mark.parametrize("header", ["X-API-Key", "Authorization"])
def test_legacy_employees_accepts_valid_key(api_client, header):
    client, _ = api_client
    value = "Bearer valid-key" if header == "Authorization" else "valid-key"
    response = client.get("/api/employees", headers={header: value})
    assert response.status_code == 200
    assert response.json()[0]["employee_number"] == "E001"


@pytest.mark.parametrize("kind", ["inactive", "expired", "restricted"])
def test_legacy_employees_enforces_token_restrictions(api_client, kind):
    client, db = api_client
    token = db.query(ApiToken).one()
    if kind == "inactive":
        token.active = False
    elif kind == "expired":
        token.expires_at = datetime.now() - timedelta(days=1)
    else:
        token.allowed_ips = "10.0.0.1"
    db.commit()
    assert client.get("/api/employees", headers={"X-API-Key": "valid-key"}).status_code in {401, 403}


@pytest.mark.parametrize("path,enabled,allowed", [
    ("/dashboard", "security_network_filter_enabled", "security_allowed_networks"),
    ("/api/employees", "security_api_network_filter_enabled", "security_api_allowed_networks"),
    ("/admin", "security_admin_network_filter_enabled", "security_admin_allowed_networks"),
])
@pytest.mark.parametrize("headers", [[], [(b"x-forwarded-for", b"127.0.0.1")], [(b"x-real-ip", b"127.0.0.1")]])
def test_network_filter_rejects_spoofed_headers(path, enabled, allowed, headers):
    request = Request({"type": "http", "path": path, "headers": headers, "client": ("203.0.113.10", 1234)})
    assert access_allowed(request, None, {enabled: "true", allowed: "10.0.0.0/8"})[0] is False


def test_network_filter_rejects_missing_client():
    request = Request({"type": "http", "path": "/admin", "headers": [], "client": None})
    assert access_allowed(request, None, {"security_network_filter_enabled": "true"})[0] is False


@pytest.mark.anyio
@pytest.mark.parametrize("peer,expected", [("10.1.0.2", True), ("203.0.113.10", False)])
async def test_only_trusted_proxy_can_forward_allowed_client(peer, expected):
    results = []

    async def endpoint(scope, receive, send):
        results.append(access_allowed(Request(scope), None, {
            "security_network_filter_enabled": "true", "security_allowed_networks": "192.168.1.0/24",
        })[0])

    app = ProxyHeadersMiddleware(endpoint, trusted_hosts=["10.1.0.2"])
    await app({"type": "http", "scheme": "http", "path": "/admin", "client": (peer, 1234),
               "headers": [(b"x-forwarded-for", b"192.168.1.50")]}, None, None)
    assert results == [expected]


@pytest.fixture
def anyio_backend():
    return "asyncio"
