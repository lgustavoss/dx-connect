import importlib.util
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.config import settings
from app.models.empresa_pdv import EmpresaPdv, PdvTipoAcessoRemoto
from app.models.rustdesk_peer import RustdeskPeer
from app.services import rustdesk_peers as svc


def _agente():
    caminho = Path(__file__).resolve().parents[2] / "scripts" / "rustdesk_hbbs_agent.py"
    spec = importlib.util.spec_from_file_location("rustdesk_hbbs_agent", caminho)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _agente_desligado(monkeypatch):
    """O .env local pode apontar para o hbbs real; a lista de teste não pode ser substituída por ele."""
    monkeypatch.setattr(settings, "RUSTDESK_AGENT_URL", None)
    monkeypatch.setattr(settings, "RUSTDESK_AGENT_TOKEN", None)
    monkeypatch.setattr(svc, "_ultimo_sync_mono", 0.0)


@pytest.fixture
def pdv_catalogo(db_session):
    from app.models.empresa_pdv import PdvRotulo

    rot = PdvRotulo(nome="Caixa", ativo=True, ordem_exibicao=1)
    tipo = PdvTipoAcessoRemoto(nome="AnyDesk", ativo=True, ordem_exibicao=1)
    db_session.add_all([rot, tipo])
    db_session.commit()
    return {"rotulo": rot, "tipo": tipo}


@pytest.fixture
def base(db_session, seed_base, pdv_catalogo):
    emp = seed_base["empresa"]
    tipo = PdvTipoAcessoRemoto(nome="RustDesk", ativo=True, ordem_exibicao=2)
    db_session.add(tipo)
    db_session.flush()
    agora = datetime.now(timezone.utc)
    db_session.add_all(
        [
            RustdeskPeer(rustdesk_id="123456789", ip="10.1.1.1", hostname="CAIXA-01", last_seen=agora),
            RustdeskPeer(
                rustdesk_id="999000111",
                ip="10.1.1.2",
                last_seen=agora - timedelta(hours=2),
            ),
            RustdeskPeer(rustdesk_id="555000555", ip="10.1.1.3", last_seen=agora),
            EmpresaPdv(
                empresa_id=emp.id,
                codigo="001",
                rotulo_id=pdv_catalogo["rotulo"].id,
                papel="principal",
                tipo_acesso_remoto_id=tipo.id,
                acesso_remoto_id="123 456 789",
                ativo=True,
            ),
            EmpresaPdv(
                empresa_id=emp.id,
                codigo="002",
                rotulo_id=pdv_catalogo["rotulo"].id,
                papel="auxiliar",
                tipo_acesso_remoto_id=tipo.id,
                acesso_remoto_id="123456789",
                ativo=True,
            ),
            EmpresaPdv(
                empresa_id=emp.id,
                codigo="003",
                rotulo_id=pdv_catalogo["rotulo"].id,
                papel="auxiliar",
                tipo_acesso_remoto_id=tipo.id,
                acesso_remoto_id="777",
                ativo=True,
            ),
            EmpresaPdv(
                empresa_id=emp.id,
                codigo="004",
                rotulo_id=pdv_catalogo["rotulo"].id,
                papel="auxiliar",
                tipo_acesso_remoto_id=pdv_catalogo["tipo"].id,
                acesso_remoto_id="888",
                ativo=True,
            ),
        ]
    )
    db_session.commit()
    return {"empresa": emp, "rotulo": pdv_catalogo["rotulo"]}


def test_lista_cruza_pdv_e_marca_online(client, auth_headers, base):
    r = client.get("/v1/rustdesk/peers", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    body = r.json()
    por_id = {item["rustdesk_id"]: item for item in body["items"]}
    ligado = por_id["123456789"]
    assert ligado["online"] is True
    assert ligado["id_repetido"] is True
    assert {v["pdv_codigo"] for v in ligado["vinculos"]} == {"001", "002"}
    assert {v["rede_nome"] for v in ligado["vinculos"]} == {"Rede Teste"}
    assert {v["rotulo_nome"] for v in ligado["vinculos"]} == {"Caixa"}
    assert {v["empresa_nome"] for v in ligado["vinculos"]} == {"Empresa Teste"}
    assert por_id["999000111"]["online"] is False
    assert por_id["999000111"]["sem_vinculo"] is True
    assert por_id["555000555"]["sem_vinculo"] is True
    ausentes = {item["pdv_codigo"] for item in body["pdvs_nao_vistos"]}
    assert ausentes == {"003"}

    so_soltos = client.get("/v1/rustdesk/peers?filtro=sem_vinculo", headers=auth_headers["admin"])
    assert {item["rustdesk_id"] for item in so_soltos.json()["items"]} == {"999000111", "555000555"}


def test_selo_no_pdv(client, auth_headers, base):
    emp = base["empresa"]
    r = client.get(f"/v1/empresas/{emp.id}/pdvs", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    por_codigo = {item["codigo"]: item["rustdesk_online"] for item in r.json()["items"]}
    assert por_codigo["001"] is True
    assert por_codigo["004"] is None
    por_visto = {item["codigo"]: item["rustdesk_visto"] for item in r.json()["items"]}
    assert por_visto["001"] is True
    assert por_visto["003"] is False


def test_vincular_exige_editar_empresa_e_confirma_substituicao(client, auth_headers, seed_base, base):
    grupo = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={"nome": "Só monitora", "permissoes": ["rustdesk.monitorar"]},
    )
    assert grupo.status_code == 201, grupo.text
    patch = client.patch(
        f"/v1/atendentes/{seed_base['a1'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [grupo.json()["id"]]},
    )
    assert patch.status_code == 200, patch.text
    negado = client.post(
        "/v1/rustdesk/peers/555000555/vincular",
        headers=auth_headers["a1"],
        json={"pdv_id": 1},
    )
    assert negado.status_code == 403, negado.text

    pdv = (
        client.get(f"/v1/empresas/{base['empresa'].id}/pdvs", headers=auth_headers["admin"]).json()["items"]
    )
    alvo = next(item for item in pdv if item["codigo"] == "004")
    conflito = client.post(
        "/v1/rustdesk/peers/555000555/vincular",
        headers=auth_headers["admin"],
        json={"pdv_id": alvo["id"]},
    )
    assert conflito.status_code == 409, conflito.text

    ok = client.post(
        "/v1/rustdesk/peers/555000555/vincular",
        headers=auth_headers["admin"],
        json={"pdv_id": alvo["id"], "confirmar_substituicao": True},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["acesso_remoto_id"] == "555000555"
    assert ok.json()["tipo_acesso_remoto_nome"] == "RustDesk"


def test_sincronizar_substitui_cache(db_session, monkeypatch):
    monkeypatch.setattr(settings, "RUSTDESK_AGENT_URL", "http://agente")
    monkeypatch.setattr(settings, "RUSTDESK_AGENT_TOKEN", "segredo")
    svc._ultimo_sync_mono = 0
    visto = datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(
        svc,
        "obter_snapshot",
        lambda: {
            "observando_log": True,
            "peers": [
                {
                    "id": "111 222 333",
                    "ip": "10.0.0.8",
                    "hostname": "SRV",
                    "username": "caixa",
                    "os": "windows",
                    "last_seen": visto,
                }
            ],
        },
    )
    db_session.add(RustdeskPeer(rustdesk_id="999"))
    db_session.commit()
    svc.sincronizar(db_session, forcar=True)
    rows = db_session.query(RustdeskPeer).all()
    assert [row.rustdesk_id for row in rows] == ["111222333"]
    assert rows[0].sistema == "windows"
    assert rows[0].hostname == "SRV"
    assert svc.calcular_online(rows[0].last_seen) is True


def test_agente_le_sqlite_e_log(tmp_path):
    agente = _agente()
    db = tmp_path / "db_v2.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE peer (id varchar(100), info text)"
    )
    conn.execute(
        "INSERT INTO peer (id, info) VALUES (?, ?)",
        ("123 456 789", '{"ip":"192.168.0.10"}'),
    )
    conn.commit()
    conn.close()
    peers = agente.ler_peers(str(db))
    assert peers == [
        {
            "id": "123456789",
            "ip": "192.168.0.10",
            "hostname": None,
            "username": None,
            "os": None,
        }
    ]
    linha = "INFO update_pk 123456789 10.0.0.1:21116 b'uuid' b'pk'"
    assert agente.extrair_id_do_log(linha) == "123456789"
    assert agente.extrair_id_do_log("outra linha") is None
    assert agente.extrair_ids_keepalive("1071170798..") == ["1071170798"]
    assert agente.extrair_ids_keepalive(".94130886..") == ["94130886"]
    assert agente.extrair_ids_keepalive("eth0  In  IP 45.170.7.138.17288 > 31.97.160.79.21116: UDP") == []
    assert agente.excluir_peer(str(db), "123 456 789") is True
    assert agente.ler_peers(str(db)) == []
    assert agente.excluir_peer(str(db), "123456789") is False


def test_desvincular_e_excluir_offline(client, auth_headers, seed_base, base, monkeypatch):
    grupo = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={"nome": "Só monitora exclusão", "permissoes": ["rustdesk.monitorar"]},
    )
    assert grupo.status_code == 201, grupo.text
    patch = client.patch(
        f"/v1/atendentes/{seed_base['a1'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [grupo.json()["id"]]},
    )
    assert patch.status_code == 200, patch.text
    pdvs = client.get(f"/v1/empresas/{base['empresa'].id}/pdvs", headers=auth_headers["admin"]).json()["items"]
    pdv_001 = next(item for item in pdvs if item["codigo"] == "001")

    negado = client.post(
        "/v1/rustdesk/peers/123456789/desvincular",
        headers=auth_headers["a1"],
        json={"pdv_id": pdv_001["id"]},
    )
    assert negado.status_code == 403, negado.text

    ok = client.post(
        "/v1/rustdesk/peers/123456789/desvincular",
        headers=auth_headers["admin"],
        json={"pdv_id": pdv_001["id"]},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["acesso_remoto_id"] is None
    ainda = client.get("/v1/rustdesk/peers", headers=auth_headers["admin"]).json()
    ligado = next(item for item in ainda["items"] if item["rustdesk_id"] == "123456789")
    assert {v["pdv_codigo"] for v in ligado["vinculos"]} == {"002"}

    outro = client.post(
        "/v1/rustdesk/peers/999000111/desvincular",
        headers=auth_headers["admin"],
        json={"pdv_id": pdv_001["id"]},
    )
    assert outro.status_code == 409, outro.text

    online = client.post("/v1/rustdesk/peers/555000555/excluir", headers=auth_headers["admin"])
    assert online.status_code == 409, online.text

    com_vinculo = client.post("/v1/rustdesk/peers/123456789/excluir", headers=auth_headers["admin"])
    assert com_vinculo.status_code == 409, com_vinculo.text

    chamadas: list[str] = []

    def _falso(chave: str) -> None:
        chamadas.append(chave)

    monkeypatch.setattr(svc, "excluir_no_agente", _falso)
    removido = client.post("/v1/rustdesk/peers/999000111/excluir", headers=auth_headers["admin"])
    assert removido.status_code == 200, removido.text
    assert chamadas == ["999000111"]
    depois = client.get("/v1/rustdesk/peers", headers=auth_headers["admin"]).json()
    assert "999000111" not in {item["rustdesk_id"] for item in depois["items"]}
