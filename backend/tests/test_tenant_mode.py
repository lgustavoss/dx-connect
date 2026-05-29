"""Modo single-tenant vs multi-tenant (issue #191 Fase 2)."""

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.config import Settings
from app.core.tenant_context import (
    assert_token_tenant_matches_request,
    is_multi_tenant_mode,
    resolve_tenant_id,
)


def _request(host: str | None = None, tenant_header: str | None = None) -> Request:
    headers = []
    if host:
        headers.append((b"host", host.encode()))
    if tenant_header is not None:
        headers.append((b"x-dx-tenant-id", tenant_header.encode()))
    scope = {"type": "http", "headers": headers, "method": "GET", "path": "/v1/tickets"}
    return Request(scope)


def test_single_tenant_ignora_host_e_header(monkeypatch):
    monkeypatch.setattr("app.core.tenant_context.settings.DX_CONNECT_MULTI_TENANT", False)
    monkeypatch.setattr("app.core.tenant_context.settings.DEFAULT_TENANT_ID", 1)
    req = _request(host="99.connect.example.com", tenant_header="99")
    assert resolve_tenant_id(req) == 1
    assert not is_multi_tenant_mode()


def test_multi_tenant_resolve_por_subdominio(monkeypatch):
    monkeypatch.setattr("app.core.tenant_context.settings.DX_CONNECT_MULTI_TENANT", True)
    monkeypatch.setattr("app.core.tenant_context.settings.CONNECT_APP_BASE_DOMAIN", "connect.example.com")
    monkeypatch.setattr("app.core.tenant_context.settings.DEFAULT_TENANT_ID", 1)
    req = _request(host="42.connect.example.com")
    assert resolve_tenant_id(req) == 42


def test_assert_token_tenant_ignorado_em_single_tenant(monkeypatch):
    monkeypatch.setattr("app.core.tenant_context.settings.DX_CONNECT_MULTI_TENANT", False)
    req = _request(host="1.connect.example.com")
    assert_token_tenant_matches_request(req, 99)  # não levanta


def test_producao_rejeita_multi_tenant():
    with pytest.raises(ValidationError) as exc:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            DATABASE_URL="postgresql://u:p@db.example.com:5432/x?sslmode=require",
            SECRET_KEY="x" * 32,
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            CORS_ORIGINS="https://app.example.com",
            ALLOWED_HOSTS="api.example.com,127.0.0.1",
            DX_CONNECT_MULTI_TENANT=True,
        )
    assert "DX_CONNECT_MULTI_TENANT" in str(exc.value)


def test_login_single_tenant_sem_header(client, seed_base, monkeypatch):
    monkeypatch.setattr("app.core.tenant_context.settings.DX_CONNECT_MULTI_TENANT", False)
    admin = seed_base["admin"]
    res = client.post(
        "/v1/auth/login",
        json={"email": admin.email, "senha": "admin123"},
    )
    assert res.status_code == 200, res.text
    assert res.json().get("access_token")
