"""Presença online de atendentes (#546)."""

from __future__ import annotations

import asyncio

from app.services.realtime_hub import RealtimeHub, channel_atendente, hub


def test_hub_presenca_multi_aba_e_offline():
    async def _run() -> None:
        h = RealtimeHub()
        ch = channel_atendente(42)
        q1 = await h.subscribe(ch)
        online = await h.list_online()
        assert len(online) == 1
        assert online[0][0] == 42
        desde = online[0][1]

        q2 = await h.subscribe(ch)
        online2 = await h.list_online()
        assert len(online2) == 1
        assert online2[0][1] == desde

        await h.unsubscribe(ch, q1)
        assert len(await h.list_online()) == 1

        await h.unsubscribe(ch, q2)
        assert await h.list_online() == []

    asyncio.run(_run())


def test_presenca_online_403_atendente(client, seed_base, auth_headers):
    r = client.get("/v1/presenca/online", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_presenca_online_admin_lista_vazia(client, seed_base, auth_headers):
    r = client.get("/v1/presenca/online", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert r.json() == {"itens": []}


def test_presenca_online_admin_ve_atendente_conectado(client, seed_base, auth_headers):
    async def _connect() -> None:
        await hub.subscribe(channel_atendente(seed_base["a1"].id))

    asyncio.run(_connect())
    try:
        r = client.get("/v1/presenca/online", headers=auth_headers["admin"])
        assert r.status_code == 200
        body = r.json()
        ids = {item["atendente_id"] for item in body["itens"]}
        assert seed_base["a1"].id in ids
        item = next(i for i in body["itens"] if i["atendente_id"] == seed_base["a1"].id)
        assert item["nome"] == seed_base["a1"].nome
        assert item["email"] == seed_base["a1"].email
        assert item["online_desde"]
        assert isinstance(item["setores"], list)
    finally:
        async def _cleanup() -> None:
            # limpa presença do hub global (todas as filas do canal)
            ch = channel_atendente(seed_base["a1"].id)
            async with hub._lock:
                hub._queues.pop(ch, None)
                hub._presence.pop(seed_base["a1"].id, None)

        asyncio.run(_cleanup())


def test_presenca_ignora_inativo(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    a1.ativo = False
    db_session.add(a1)
    db_session.commit()

    async def _connect() -> None:
        await hub.subscribe(channel_atendente(a1.id))

    asyncio.run(_connect())
    try:
        r = client.get("/v1/presenca/online", headers=auth_headers["admin"])
        assert r.status_code == 200
        ids = {item["atendente_id"] for item in r.json()["itens"]}
        assert a1.id not in ids
    finally:
        async def _cleanup() -> None:
            ch = channel_atendente(a1.id)
            async with hub._lock:
                hub._queues.pop(ch, None)
                hub._presence.pop(a1.id, None)

        asyncio.run(_cleanup())
        a1.ativo = True
        db_session.add(a1)
        db_session.commit()
