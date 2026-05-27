"""Resolução de tenant/endereço inbound e subdomínio."""

from app.core.tenant_context import parse_tenant_id_from_host
from app.models.tenant_inbound_address import TenantInboundAddress
from app.services.tenant_inbound import (
    extract_local_part_from_email,
    format_inbound_address,
    resolve_routing_from_recipients,
)
from app.services.tenant_inbound_sync import local_part_for_setor, sync_inbound_addresses_for_tenant


def test_parse_tenant_id_from_host_subdominio(monkeypatch):
    monkeypatch.setattr("app.core.tenant_context.settings.CONNECT_APP_BASE_DOMAIN", "connect.example.com")
    assert parse_tenant_id_from_host("42.connect.example.com") == 42
    assert parse_tenant_id_from_host("connect.example.com") is None


def test_extract_local_part_from_email(db_session, seed_base, monkeypatch):
    monkeypatch.setattr("app.services.tenant_inbound.settings.INBOUND_EMAIL_DOMAIN", "inbound.dx.test")
    addr = TenantInboundAddress(
        tenant_id=1,
        local_part="suporte.t1",
        setor_id=seed_base["setor1"].id,
        ativo=True,
    )
    db_session.add(addr)
    db_session.commit()
    assert extract_local_part_from_email("suporte.t1@inbound.dx.test") == "suporte.t1"
    cfg, lp = resolve_routing_from_recipients(db_session, ["suporte.t1@inbound.dx.test"])
    assert lp == "suporte.t1"
    assert cfg is not None
    assert cfg.setor_id == seed_base["setor1"].id


def test_format_inbound_address(monkeypatch):
    monkeypatch.setattr("app.services.tenant_inbound.settings.INBOUND_EMAIL_DOMAIN", "inbound.dx.test")
    assert format_inbound_address("1_comercial") == "1_comercial@inbound.dx.test"


def test_local_part_for_setor():
    assert local_part_for_setor(1, "suporte") == "suporte.t1"


def test_sync_inbound_cria_um_por_setor_ativo(db_session, seed_base, monkeypatch):
    monkeypatch.setattr("app.services.tenant_inbound.settings.INBOUND_EMAIL_DOMAIN", "inbound.dx.test")
    rows = sync_inbound_addresses_for_tenant(db_session, seed_base["tenant"].id)
    assert len(rows) == 2
    by_setor = {r.setor_id: r for r in rows}
    assert by_setor[seed_base["setor1"].id].local_part == "suporte.t1"
    assert by_setor[seed_base["setor2"].id].local_part == "financeiro.t1"
    assert by_setor[seed_base["setor1"].id].label == "Suporte"
    assert format_inbound_address(by_setor[seed_base["setor1"].id].local_part) == "suporte.t1@inbound.dx.test"


def test_lookup_aceita_local_part_legado(db_session, seed_base, monkeypatch):
    from app.services.tenant_inbound import lookup_inbound_address

    monkeypatch.setattr("app.services.tenant_inbound.settings.INBOUND_EMAIL_DOMAIN", "inbound.dx.test")
    sync_inbound_addresses_for_tenant(db_session, seed_base["tenant"].id)
    row = lookup_inbound_address(db_session, local_part="1_suporte")
    assert row is not None
    assert row.setor_id == seed_base["setor1"].id


def test_sync_inbound_desativa_setor_inativo(db_session, seed_base, monkeypatch):
    monkeypatch.setattr("app.services.tenant_inbound.settings.INBOUND_EMAIL_DOMAIN", "inbound.dx.test")
    sync_inbound_addresses_for_tenant(db_session, seed_base["tenant"].id)
    seed_base["setor2"].ativo = False
    db_session.commit()
    rows = sync_inbound_addresses_for_tenant(db_session, seed_base["tenant"].id)
    assert len(rows) == 1
    inactive = (
        db_session.query(TenantInboundAddress)
        .filter(TenantInboundAddress.setor_id == seed_base["setor2"].id)
        .first()
    )
    assert inactive is not None
    assert inactive.ativo is False
