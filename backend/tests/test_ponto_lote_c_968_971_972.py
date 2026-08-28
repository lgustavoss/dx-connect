"""Lote C ponto: lembretes tolerância (#968), resumo semanal (#972), ajustes (#971)."""

from datetime import date, datetime, timedelta, timezone

from app.services.escala import PONTO_TZ


def _freeze_ponto_agora(monkeypatch, when: datetime) -> None:
    """Evita flakiness quando o pytest roda perto da meia-noite (jornada semanal)."""
    when_utc = when.astimezone(timezone.utc)
    monkeypatch.setattr("app.services.ponto._agora_utc", lambda: when_utc)
    import app.services.escala as escala_mod
    import app.services.ponto as ponto_mod

    real_dt = ponto_mod.datetime

    class DatetimeComAgoraFixo(real_dt):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return when.astimezone(tz)
            return when.replace(tzinfo=None)

    monkeypatch.setattr(ponto_mod, "datetime", DatetimeComAgoraFixo)
    monkeypatch.setattr(escala_mod, "datetime", DatetimeComAgoraFixo)

    real_date = ponto_mod.date

    class DateComHojeFixo(real_date):
        @classmethod
        def today(cls):
            return when.date()

    monkeypatch.setattr(ponto_mod, "date", DateComHojeFixo)


def _patch_jornada_hoje(
    client,
    headers,
    atendente_id: int,
    *,
    ref: date | None = None,
    inicio="08:00",
    fim="18:00",
    tol=30,
):
    keys = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
    hoje_key = keys[(ref or date.today()).weekday()]
    hs = {k: {"ativo": False, "inicio": "08:00", "fim": "18:00"} for k in keys}
    hs[hoje_key] = {"ativo": True, "inicio": inicio, "fim": fim}
    return client.patch(
        f"/v1/atendentes/{atendente_id}",
        headers=headers,
        json={
            "modo_jornada": "semanal",
            "usa_escala": True,
            "horario_semana": hs,
            "tolerancia_atraso_minutos": tol,
        },
    )


def test_lembrete_entrada_na_janela_tolerancia(client, seed_base, auth_headers, monkeypatch):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    agora = datetime(2026, 6, 17, 10, 0, tzinfo=PONTO_TZ)
    _freeze_ponto_agora(monkeypatch, agora)
    # Coloca início da jornada 10 min no futuro e tol=30 → já estamos em inicio−tol
    inicio_dt = agora + timedelta(minutes=10)
    fim_dt = inicio_dt + timedelta(hours=8)
    inicio = inicio_dt.strftime("%H:%M")
    fim = fim_dt.strftime("%H:%M")
    assert _patch_jornada_hoje(
        client, admin, a1.id, ref=agora.date(), inicio=inicio, fim=fim, tol=30
    ).status_code == 200
    r = client.get("/v1/ponto/me/alertas", headers=user)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lembrete_entrada_tolerancia"] is True
    assert any("Janela de entrada" in m for m in body["mensagens"])


def test_lembrete_saida_antes_do_fim(client, seed_base, auth_headers, db_session, monkeypatch):
    from app.models.ponto_batida import PontoBatida

    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    agora = datetime(2026, 6, 17, 16, 50, tzinfo=PONTO_TZ)
    _freeze_ponto_agora(monkeypatch, agora)
    # fim daqui a 10 min, tol 30 → já na janela de saída
    fim_dt = agora + timedelta(minutes=10)
    inicio_dt = fim_dt - timedelta(hours=8)
    inicio = inicio_dt.strftime("%H:%M")
    fim = fim_dt.strftime("%H:%M")
    assert _patch_jornada_hoje(
        client, admin, a1.id, ref=agora.date(), inicio=inicio, fim=fim, tol=30
    ).status_code == 200
    db_session.add(
        PontoBatida(
            tenant_id=a1.tenant_id,
            atendente_id=a1.id,
            tipo="entrada",
            registrado_em=agora.astimezone(timezone.utc) - timedelta(hours=7),
            origem="app",
        )
    )
    db_session.commit()
    r = client.get("/v1/ponto/me/alertas", headers=user)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lembrete_saida_tolerancia"] is True
    assert any("saída" in m.lower() for m in body["mensagens"])


def test_modo_nenhum_sem_lembrete_tolerancia(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    assert client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=admin,
        json={"modo_jornada": "nenhum", "usa_escala": False},
    ).status_code == 200
    r = client.get("/v1/ponto/me/alertas", headers=user)
    assert r.status_code == 200
    body = r.json()
    assert body["lembrete_entrada_tolerancia"] is False
    assert body["lembrete_saida_tolerancia"] is False


def test_resumo_semana_proprio(client, seed_base, auth_headers):
    user = auth_headers["a1"]
    r = client.get("/v1/ponto/me/resumo-semana", headers=user)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "desde" in body and "ate" in body
    assert "atrasos" in body
    assert "he_minutos" in body
    assert "saldo_segundos" in body
    assert body["segundos_esperados"] >= 0


def test_ajuste_motivo_obrigatorio_strip(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1 = seed_base["a1"]
    r = client.post(
        "/v1/ponto/batidas",
        headers=admin,
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": datetime.now(timezone.utc).isoformat(),
            "motivo": "  ",
        },
    )
    assert r.status_code == 422
    r_ok = client.post(
        "/v1/ponto/batidas",
        headers=admin,
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": datetime.now(timezone.utc).isoformat(),
            "motivo": "Correção de esquecimento",
        },
    )
    assert r_ok.status_code == 201, r_ok.text
