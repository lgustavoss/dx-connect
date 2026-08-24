"""Token Cursor MCP pessoal (#915)."""

from __future__ import annotations

from app.core.security import criar_access_token, hash_senha
from app.models.atendente import Atendente


def _headers_ops(email: str) -> dict[str, str]:
    tok = criar_access_token({"sub": email, "tid": 1})
    return {"Authorization": f"Bearer {tok}", "X-Dx-Tenant-Id": "1"}


def _criar_ops2(db_session, seed_base) -> Atendente:
    row = Atendente(
        tenant_id=seed_base["tenant"].id,
        email="ops2@test.local",
        nome="Ops Dois",
        senha_hash=hash_senha("ops123456"),
        role="saas_ops",
        ativo=True,
        must_change_password=False,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_mcp_token_painel_404_sem_control_plane(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.get("/v1/saas/me/mcp-token", headers=auth_headers["ops"])
    assert r.status_code == 404


def test_mcp_token_gerar_lista_e_nao_e_o_primeiro_ops(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    ops2 = _criar_ops2(db_session, seed_base)
    h2 = _headers_ops(ops2.email)

    estado = client.get("/v1/saas/me/mcp-token", headers=h2)
    assert estado.status_code == 200, estado.text
    assert estado.json()["configurado"] is False

    gerado = client.post("/v1/saas/me/mcp-token", headers=h2)
    assert gerado.status_code == 200, gerado.text
    token = gerado.json()["token"]
    assert token.startswith("drmcp_")
    assert gerado.json()["configurado"] is True

    sid = client.post(
        "/v1/solicitacoes-melhoria",
        headers=auth_headers["a1"],
        json={
            "tipo": "sugestao",
            "titulo": "Token pessoal",
            "descricao": "Quem recusou tem de ser o ops dois.",
        },
    ).json()["id"]
    lista_ops = client.get("/v1/saas/solicitacoes", headers=auth_headers["ops"])
    saas_id = next(i["id"] for i in lista_ops.json()["items"] if i["origem_solicitacao_id"] == sid)

    mcp = {"Authorization": f"Bearer {token}"}
    listed = client.get("/v1/saas/solicitacoes", headers=mcp)
    assert listed.status_code == 200, listed.text

    comentario = client.post(
        f"/v1/saas/solicitacoes/{saas_id}/comentarios",
        headers=mcp,
        json={"corpo": "nota interna do ops dois", "publico_cliente": False},
    )
    assert comentario.status_code == 200, comentario.text
    ultimo = comentario.json()["comentarios"][-1]
    assert ultimo["autor_nome"] == "Ops Dois"


def test_mcp_token_regenerar_invalida_o_anterior(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    primeiro = client.post("/v1/saas/me/mcp-token", headers=auth_headers["ops"]).json()["token"]
    segundo = client.post("/v1/saas/me/mcp-token", headers=auth_headers["ops"]).json()["token"]
    assert primeiro != segundo
    antigo = client.get("/v1/saas/solicitacoes", headers={"Authorization": f"Bearer {primeiro}"})
    assert antigo.status_code == 401
    novo = client.get("/v1/saas/solicitacoes", headers={"Authorization": f"Bearer {segundo}"})
    assert novo.status_code == 200, novo.text


def test_mcp_token_revogar_e_conta_inactiva(client, seed_base, auth_headers, db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    token = client.post("/v1/saas/me/mcp-token", headers=auth_headers["ops"]).json()["token"]
    rev = client.delete("/v1/saas/me/mcp-token", headers=auth_headers["ops"])
    assert rev.status_code == 200
    assert rev.json()["configurado"] is False
    assert client.get("/v1/saas/solicitacoes", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    token2 = client.post("/v1/saas/me/mcp-token", headers=auth_headers["ops"]).json()["token"]
    seed_base["ops"].ativo = False
    db_session.commit()
    assert client.get("/v1/saas/solicitacoes", headers={"Authorization": f"Bearer {token2}"}).status_code == 401


def test_mcp_token_so_o_proprio_ops_jwt(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    assert client.get("/v1/saas/me/mcp-token", headers=auth_headers["admin"]).status_code == 403
    pessoal = client.post("/v1/saas/me/mcp-token", headers=auth_headers["ops"]).json()["token"]
    with_mcp = client.post("/v1/saas/me/mcp-token", headers={"Authorization": f"Bearer {pessoal}"})
    assert with_mcp.status_code == 401


def test_mcp_token_legado_env_ainda_lista(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_MCP_TOKEN", "mcp-legado-vps")
    listed = client.get("/v1/saas/solicitacoes", headers={"Authorization": "Bearer mcp-legado-vps"})
    assert listed.status_code == 200, listed.text
