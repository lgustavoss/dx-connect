"""Release CalVer → conclusão de solicitações SaaS (#956)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.models.saas_solicitacao_produto import SaasSolicitacaoProduto
from app.services.saas_solicitacao_release import concluir_pedidos_release, extrair_referencias_release

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "concluir_solicitacoes_release.py"
_spec = importlib.util.spec_from_file_location("concluir_solicitacoes_release", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_release_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_release_script)
textos_da_versao = _release_script.textos_da_versao


def test_textos_da_versao_le_release_notes_sem_changelog():
    """Produção: a imagem não tem CHANGELOG nem scripts/prepare_release."""
    notes = {
        "current": {
            "version": "26.09.005",
            "changes": [
                {"text": "PDV (#1142 / #S202609-0029): olho na senha"},
                {"text": "Ponto (#1132): banco de horas"},
            ],
        },
        "releases": [
            {
                "version": "26.09.004",
                "changes": [{"text": "WhatsApp (#1102): correção antiga"}],
            }
        ],
    }
    textos = textos_da_versao("26.09.005", changelog=None, release_notes=notes)
    assert textos == [
        "PDV (#1142 / #S202609-0029): olho na senha",
        "Ponto (#1132): banco de horas",
    ]
    assert textos_da_versao("v26.09.004", changelog=None, release_notes=notes) == [
        "WhatsApp (#1102): correção antiga"
    ]
    assert textos_da_versao("26.09.099", changelog=None, release_notes=notes) == []


def test_textos_da_versao_prioriza_secao_publicada_do_changelog():
    changelog = """## [Unreleased]

- Rascunho (#S202609-0099): ainda não publicado

## [26.09.005] - 2026-09-29

- PDV (#S202609-0029): publicado
"""
    notes = {
        "current": {
            "version": "26.09.003",
            "changes": [{"text": "Versão antiga (#881): não usar"}],
        }
    }
    assert textos_da_versao("26.09.005", changelog=changelog, release_notes=notes) == [
        "PDV (#S202609-0029): publicado"
    ]


def test_textos_da_versao_unreleased_so_antes_de_publicar():
    changelog = """## [Unreleased]

- Chat (#S202609-0028): em preparação

## [26.09.004] - 2026-09-27

- WhatsApp (#1102): já publicado
"""
    assert textos_da_versao("26.09.005", changelog=changelog, release_notes=None) == [
        "Chat (#S202609-0028): em preparação"
    ]


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
    aviso = next(c for c in minhas["comentarios"] if "2026.08.99" in c["corpo"])
    assert aviso["autor_nome"] == "Desenvolvedor"
    db_session.expire_all()
    saas = db_session.get(SaasSolicitacaoProduto, saas_id)
    assert any(c.autor_nome == "Deploy" for c in saas.comentarios)
    assert any(h.canal == "release" and h.autor_nome == "Deploy" for h in saas.historico)

    stats2 = concluir_pedidos_release(db_session, versao="2026.08.99", textos_changelog=[texto])
    assert stats2["concluidos"] == 0
    assert stats2["ignorados"] >= 1
