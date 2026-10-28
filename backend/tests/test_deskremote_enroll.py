from app.config import settings
from app.models.audit_log import AuditLog
from app.models.empresa_pdv import PdvRotulo, PdvTipoAcessoRemoto
from app.models.rustdesk_peer import RustdeskPeer
from app.services import rustdesk_peers as rustdesk_svc


def _servidor(monkeypatch):
    monkeypatch.setattr(settings, "RUSTDESK_ID_SERVER", "203.0.113.10")
    monkeypatch.setattr(settings, "RUSTDESK_RELAY_SERVER", "203.0.113.10")
    monkeypatch.setattr(settings, "RUSTDESK_PUBLIC_KEY", "chave-publica-teste")
    monkeypatch.setattr(settings, "CLIENT_APP_HOST", "duplexsoft.deskrudder.com.br")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")


def _pdv_deskremote(client, auth_headers, seed_base, db_session, senha="senha-pdv"):
    rot = PdvRotulo(nome="SERVIDOR", ativo=True, ordem_exibicao=1)
    tipo = PdvTipoAcessoRemoto(nome="DeskRemote", ativo=True, ordem_exibicao=1)
    db_session.add_all([rot, tipo])
    db_session.commit()
    emp = seed_base["empresa"]
    r = client.post(
        f"/v1/empresas/{emp.id}/pdvs",
        headers=auth_headers["admin"],
        json={
            "codigo": "001",
            "rotulo_id": rot.id,
            "papel": "principal",
            "acessos": [
                {
                    "tipo_acesso_remoto_id": tipo.id,
                    "acesso_remoto_senha": senha,
                }
            ],
        },
    )
    assert r.status_code == 201, r.text
    return r.json(), emp.id, tipo.id


def test_gerar_token_e_resgatar(client, auth_headers, seed_base, db_session, monkeypatch):
    _servidor(monkeypatch)
    pdv, emp_id, _ = _pdv_deskremote(client, auth_headers, seed_base, db_session)
    r = client.post(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "senha" not in body
    assert body["url"].startswith("http://duplexsoft.deskrudder.com.br/deskremote/instalar/")
    token = body["url"].rsplit("/", 1)[-1]
    enroll = client.post("/v1/deskremote/enroll", json={"token": token, "rustdesk_id": "1998377577"})
    assert enroll.status_code == 200, enroll.text
    out = enroll.json()
    assert out["senha"] == "senha-pdv"
    assert out["servidor"]["servidor_id"] == "203.0.113.10"
    assert out["dispositivo_token"]
    assert out["rustdesk_id"] == "1998377577"
    lista = client.get(f"/v1/empresas/{emp_id}/pdvs", headers=auth_headers["admin"])
    assert lista.json()["items"][0]["acesso_remoto_id"] == "1998377577"
    de_novo = client.post("/v1/deskremote/enroll", json={"token": token})
    assert de_novo.status_code == 400


def test_gerar_token_403_sem_editar(client, auth_headers, seed_base, db_session, monkeypatch):
    _servidor(monkeypatch)
    pdv, emp_id, _ = _pdv_deskremote(client, auth_headers, seed_base, db_session)
    r = client.post(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}/deskremote/token",
        headers=auth_headers["a1"],
        json={},
    )
    assert r.status_code == 403


def test_gerar_token_sem_senha(client, auth_headers, seed_base, db_session, monkeypatch):
    _servidor(monkeypatch)
    rot = PdvRotulo(nome="PDV", ativo=True, ordem_exibicao=1)
    tipo = PdvTipoAcessoRemoto(nome="DeskRemote", ativo=True, ordem_exibicao=1)
    db_session.add_all([rot, tipo])
    db_session.commit()
    emp = seed_base["empresa"]
    criado = client.post(
        f"/v1/empresas/{emp.id}/pdvs",
        headers=auth_headers["admin"],
        json={
            "codigo": "002",
            "rotulo_id": rot.id,
            "papel": "principal",
            "acessos": [{"tipo_acesso_remoto_id": tipo.id}],
        },
    )
    assert criado.status_code == 201, criado.text
    r = client.post(
        f"/v1/empresas/{emp.id}/pdvs/{criado.json()['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={},
    )
    assert r.status_code == 400
    assert "senha" in r.json()["detail"].lower()


def test_gerar_token_tipo_rustdesk_oficial(client, auth_headers, seed_base, db_session, monkeypatch):
    _servidor(monkeypatch)
    rot = PdvRotulo(nome="PDV", ativo=True, ordem_exibicao=1)
    tipo = PdvTipoAcessoRemoto(nome="RustDesk", ativo=True, ordem_exibicao=1)
    db_session.add_all([rot, tipo])
    db_session.commit()
    emp = seed_base["empresa"]
    criado = client.post(
        f"/v1/empresas/{emp.id}/pdvs",
        headers=auth_headers["admin"],
        json={
            "codigo": "002-rd",
            "rotulo_id": rot.id,
            "papel": "principal",
            "acessos": [
                {
                    "tipo_acesso_remoto_id": tipo.id,
                    "acesso_remoto_id": "519442868",
                    "acesso_remoto_senha": "senha-rd",
                }
            ],
        },
    )
    assert criado.status_code == 201, criado.text
    r = client.post(
        f"/v1/empresas/{emp.id}/pdvs/{criado.json()['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={"acesso_id": criado.json()["acessos"][0]["id"]},
    )
    assert r.status_code == 400
    assert "deskremote" in r.json()["detail"].casefold()


def test_confirmar_id_depois_e_sync_senha(client, auth_headers, seed_base, db_session, monkeypatch):
    _servidor(monkeypatch)
    pdv, emp_id, tipo_id = _pdv_deskremote(client, auth_headers, seed_base, db_session)
    gerado = client.post(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={},
    )
    token = gerado.json()["url"].rsplit("/", 1)[-1]
    enroll = client.post("/v1/deskremote/enroll", json={"token": token})
    assert enroll.status_code == 200, enroll.text
    device = enroll.json()["dispositivo_token"]
    h = {"Authorization": f"Bearer {device}"}
    conf = client.post("/v1/deskremote/dispositivo/id", headers=h, json={"rustdesk_id": "111222333"})
    assert conf.status_code == 200, conf.text
    assert conf.json()["rustdesk_id"] == "111222333"
    selo = client.get(f"/v1/empresas/{emp_id}/pdvs", headers=auth_headers["admin"])
    assert selo.status_code == 200, selo.text
    ficha = selo.json()["items"][0]
    assert ficha["acesso_remoto_id"] == "111222333"
    assert ficha["rustdesk_visto"] is True
    assert ficha["rustdesk_online"] is True
    sync1 = client.get("/v1/deskremote/dispositivo/config", headers=h)
    assert sync1.status_code == 200
    assert sync1.json()["senha"] is None
    patch = client.patch(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}",
        headers=auth_headers["admin"],
        json={
            "acessos": [
                {
                    "id": pdv["acessos"][0]["id"],
                    "tipo_acesso_remoto_id": tipo_id,
                    "acesso_remoto_id": "111222333",
                    "acesso_remoto_senha": "senha-nova",
                }
            ]
        },
    )
    assert patch.status_code == 200, patch.text
    sync2 = client.get("/v1/deskremote/dispositivo/config", headers=h)
    assert sync2.status_code == 200, sync2.text
    assert sync2.json()["senha"] == "senha-nova"
    sync3 = client.get("/v1/deskremote/dispositivo/config", headers=h)
    assert sync3.json()["senha"] is None
    logs = db_session.query(AuditLog).filter(AuditLog.action == "deskremote_sync_senha").all()
    assert len(logs) == 1


def test_gerar_de_novo_invalida_token_anterior(client, auth_headers, seed_base, db_session, monkeypatch):
    _servidor(monkeypatch)
    pdv, emp_id, _ = _pdv_deskremote(client, auth_headers, seed_base, db_session)
    t1 = client.post(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={},
    )
    token_velho = t1.json()["url"].rsplit("/", 1)[-1]
    t2 = client.post(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={},
    )
    token_novo = t2.json()["url"].rsplit("/", 1)[-1]
    assert client.post("/v1/deskremote/enroll", json={"token": token_velho}).status_code == 400
    ok = client.post("/v1/deskremote/enroll", json={"token": token_novo, "rustdesk_id": "555"})
    assert ok.status_code == 200, ok.text


def test_token_expirado_recusa(client, auth_headers, seed_base, db_session, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.models.deskremote_enroll import DeskremoteInstallToken
    from app.services.deskremote_enroll import hash_token

    _servidor(monkeypatch)
    pdv, emp_id, _ = _pdv_deskremote(client, auth_headers, seed_base, db_session)
    gerado = client.post(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={},
    )
    token = gerado.json()["url"].rsplit("/", 1)[-1]
    db_session.expire_all()
    row = (
        db_session.query(DeskremoteInstallToken)
        .filter(DeskremoteInstallToken.token_hash == hash_token(token))
        .one()
    )
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    r = client.post("/v1/deskremote/enroll", json={"token": token})
    assert r.status_code == 400
    assert "válido" in r.json()["detail"].lower() or "usado" in r.json()["detail"].lower()


def test_origem_api_publica_mapeia_slug(monkeypatch):
    from app.services.deskremote_enroll import origem_api_publica

    monkeypatch.setattr(settings, "CLIENT_APP_HOST", "duplexsoft.deskrudder.com.br")
    monkeypatch.setattr(settings, "PUBLIC_API_HOST", None)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert origem_api_publica() == "https://api-duplexsoft.deskrudder.com.br"


def test_enroll_sem_token_401(client, monkeypatch):
    _servidor(monkeypatch)
    r = client.get("/v1/deskremote/dispositivo/config")
    assert r.status_code == 401
    r2 = client.get("/v1/deskremote/dispositivo/config", headers={"Authorization": "Bearer x"})
    assert r2.status_code == 401


def test_dispositivo_revogado_nao_sincroniza(client, auth_headers, seed_base, db_session, monkeypatch):
    _servidor(monkeypatch)
    pdv, emp_id, _ = _pdv_deskremote(client, auth_headers, seed_base, db_session)
    t1 = client.post(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={},
    )
    e1 = client.post("/v1/deskremote/enroll", json={"token": t1.json()["url"].rsplit("/", 1)[-1], "rustdesk_id": "1"})
    device_antigo = e1.json()["dispositivo_token"]
    t2 = client.post(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={},
    )
    e2 = client.post("/v1/deskremote/enroll", json={"token": t2.json()["url"].rsplit("/", 1)[-1], "rustdesk_id": "2"})
    assert e2.status_code == 200
    r = client.get(
        "/v1/deskremote/dispositivo/config",
        headers={"Authorization": f"Bearer {device_antigo}"},
    )
    assert r.status_code == 401
    lista = client.get(f"/v1/empresas/{emp_id}/pdvs", headers=auth_headers["admin"])
    assert lista.json()["items"][0]["acesso_remoto_id"] == "2"


def test_sync_hbbs_nao_apaga_id_do_enroll(client, auth_headers, seed_base, db_session, monkeypatch):
    _servidor(monkeypatch)
    pdv, emp_id, _ = _pdv_deskremote(client, auth_headers, seed_base, db_session)
    gerado = client.post(
        f"/v1/empresas/{emp_id}/pdvs/{pdv['id']}/deskremote/token",
        headers=auth_headers["admin"],
        json={},
    )
    token = gerado.json()["url"].rsplit("/", 1)[-1]
    assert client.post("/v1/deskremote/enroll", json={"token": token, "rustdesk_id": "1998377577"}).status_code == 200
    assert db_session.query(RustdeskPeer).filter_by(rustdesk_id="1998377577").one_or_none() is not None
    monkeypatch.setattr(settings, "RUSTDESK_AGENT_URL", "http://agente")
    monkeypatch.setattr(settings, "RUSTDESK_AGENT_TOKEN", "segredo")
    rustdesk_svc._ultimo_sync_mono = 0
    monkeypatch.setattr(rustdesk_svc, "obter_snapshot", lambda: {"observando_log": True, "peers": []})
    rustdesk_svc.sincronizar(db_session, forcar=True)
    assert db_session.query(RustdeskPeer).filter_by(rustdesk_id="1998377577").one_or_none() is not None
    selo = client.get(f"/v1/empresas/{emp_id}/pdvs", headers=auth_headers["admin"])
    ficha = selo.json()["items"][0]
    assert ficha["rustdesk_visto"] is True
    assert ficha["rustdesk_online"] is True
