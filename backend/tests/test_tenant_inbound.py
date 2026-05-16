"""Resolução de tenant/endereço inbound e subdomínio."""

from app.core.tenant_context import parse_tenant_id_from_host
from app.models.tenant_inbound_address import TenantInboundAddress
from app.services.tenant_inbound import (
    extract_local_part_from_email,
    format_inbound_address,
    resolve_routing_from_recipients,
)


def test_parse_tenant_id_from_host_subdominio(monkeypatch):
    monkeypatch.setattr("app.core.tenant_context.settings.CONNECT_APP_BASE_DOMAIN", "connect.example.com")
    assert parse_tenant_id_from_host("42.connect.example.com") == 42
    assert parse_tenant_id_from_host("connect.example.com") is None


def test_extract_local_part_from_email(db_session, seed_base, monkeypatch):
    monkeypatch.setattr("app.services.tenant_inbound.settings.INBOUND_EMAIL_DOMAIN", "inbound.dx.test")
    addr = TenantInboundAddress(
        tenant_id=1,
        local_part="1_suporte",
        setor_id=seed_base["setor1"].id,
        ativo=True,
    )
    db_session.add(addr)
    db_session.commit()
    assert extract_local_part_from_email("1_suporte@inbound.dx.test") == "1_suporte"
    cfg, lp = resolve_routing_from_recipients(db_session, ["1_suporte@inbound.dx.test"])
    assert lp == "1_suporte"
    assert cfg is not None
    assert cfg.setor_id == seed_base["setor1"].id


def test_format_inbound_address(monkeypatch):
    monkeypatch.setattr("app.services.tenant_inbound.settings.INBOUND_EMAIL_DOMAIN", "inbound.dx.test")
    assert format_inbound_address("1_comercial") == "1_comercial@inbound.dx.test"
