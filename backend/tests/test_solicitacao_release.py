"""Release CalVer → conclusão de solicitações SaaS (#956)."""

from __future__ import annotations

from app.models.saas_solicitacao_produto import SaasSolicitacaoProduto
from app.services.saas_solicitacao_release import concluir_pedidos_release, extrair_referencias_release


def test_extrair_referencias_protocolo_e_issue():
    texto = "Chat (#941 / #S202608-0008): modal membros · Closes #952"
    protocolos, issues = extrair_referencias_release([texto])
    assert "#S202608-0008" in protocolos
    assert 941 in issues
    assert 952 in issues


def test_concluir_pedidos_release_idempotente(client, seed_base, auth_headers, monkeypatch, db_session):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    sid = client.post(
        "/v1/solicitacoes-melhoria",
        headers=auth_headers["a1"],
        json={
            "tipo": "sugestao",
            "titulo": "Release hook",
            "descricao": "Teste conclusão automática no deploy.",
        },
    ).json()["id"]
    h = auth_headers["ops"]
    lista = client.get("/v1/saas/solicitacoes", headers=h).json()["items"]
    row = next(i for i in lista if i["origem_solicitacao_id"] == sid)
    saas_id = row["id"]
    protocolo = row["protocolo"]
    assert protocolo

    for st in ("em_analise", "planejada"):
        client.patch(
            f"/v1/saas/solicitacoes/{saas_id}/status",
            headers=h,
            json={"status": st},
        )
    client.post(
        f"/v1/saas/solicitacoes/{saas_id}/implementar",
        headers=h,
        json={"github_issue_url": "https://github.com/lgustavoss/dx-connect/issues/9560"},
    )

    texto = f"Melhoria ({protocolo}): conclusão automática (#9560)"
    stats = concluir_pedidos_release(db_session, versao="2026.08.99", textos_changelog=[texto])
    assert stats["concluidos"] >= 1

    db_session.expire_all()
    saas = db_session.get(SaasSolicitacaoProduto, saas_id)
    assert saas.status == "concluida"
    assert saas.versao_alvo == "2026.08.99"

    minhas = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"]).json()
    assert minhas["status"] == "concluida"
    assert minhas["versao_alvo"] == "2026.08.99"
    assert minhas["versao_alvo_rotulo"] == "Disponível a partir da versão 2026.08.99 (ou superior)"

    stats2 = concluir_pedidos_release(db_session, versao="2026.08.99", textos_changelog=[texto])
    assert stats2["concluidos"] == 0
    assert stats2["ignorados"] >= 1
