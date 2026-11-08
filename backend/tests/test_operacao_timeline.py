"""Operação — timeline 360 e saúde do cliente da carteira (#912 / #914).

Fluxo coberto: lead → negociação (nota, mudança de etapa) → proposta gerada e
enviada → contrato gerado, enviado e assinado (com ticket de implantação e
checklist) → chamado de suporte aberto, fechado e reaberto. Os eventos são
derivados dessas tabelas existentes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import Ticket
from tests.test_comercial_contrato import _anexar_pdf_assinado, _negociacao_com_linha

_TIPOS_ESPERADOS = (
    "lead_criado",
    "negociacao_nota",
    "negociacao_mudanca_estagio",
    "proposta_gerada",
    "proposta_enviada",
    "contrato_gerado",
    "contrato_enviado",
    "contrato_assinado",
    "ticket_criado",
    "ticket_fechado",
    "ticket_reaberto",
    "implantacao_item_concluido",
)


def _criar_status_fechado(client, h_admin) -> int:
    r = client.post(
        "/v1/status-ticket",
        headers=h_admin,
        json={"nome": "Fechado", "slug": "fechado", "ordem": 90, "ativo": True},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _criar_chamado(client, h_admin, *, empresa_id: int, setor_id: int, assunto: str) -> dict:
    r = client.post(
        "/v1/tickets",
        headers=h_admin,
        json={
            "empresa_id": empresa_id,
            "setor_id": setor_id,
            "assunto": assunto,
            "descricao": "Aberto no teste da timeline operacional.",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _fechar_chamado_db(db_session, ticket_id: int, status_fechado_id: int) -> None:
    """Fecha o chamado direto no banco (a API exige motivo de encerramento).

    O evento derivado usa `fechado_em`, exatamente como a tela de tickets.
    """
    ticket = db_session.get(Ticket, ticket_id)
    assert ticket is not None
    ticket.status_id = status_fechado_id
    ticket.fechado_em = datetime.now(timezone.utc)
    db_session.commit()


def _envelhecer_implantacao(db_session, ticket_id: int, dias: int) -> None:
    """Leva o ticket de implantação e a última conclusão de checklist para o passado."""
    from app.models import TicketChecklistItem

    momento = datetime.now(timezone.utc) - timedelta(days=dias)
    ticket = db_session.get(Ticket, ticket_id)
    assert ticket is not None
    ticket.created_at = momento
    for item in db_session.query(TicketChecklistItem).filter(
        TicketChecklistItem.ticket_id == ticket_id,
        TicketChecklistItem.concluido.is_(True),
    ):
        item.concluido_em = momento
    db_session.commit()


def _fluxo_completo(
    client,
    auth_headers,
    seed_base,
    db_session,
    *,
    reabrir: bool = False,
) -> dict:
    """Executa a jornada inteira e devolve os ids usados pelas asserções."""
    h = auth_headers["comercial"]
    h_admin = auth_headers["admin"]

    neg_id, linha = _negociacao_com_linha(client, h)
    empresa_id = linha["empresa_id"]

    nota = client.post(
        f"/v1/crm/negociacoes/{neg_id}/atividades",
        headers=h,
        json={"tipo": "nota", "texto": "Cliente pediu revisão da proposta."},
    )
    assert nota.status_code == 201, nota.text

    mov = client.post(
        f"/v1/crm/negociacoes/{neg_id}/mover-estagio",
        headers=h,
        json={"estagio_slug": "em_negociacao"},
    )
    assert mov.status_code == 200, mov.text

    proposta = client.post(
        "/v1/comercial/propostas",
        headers=h,
        json={"negociacao_id": neg_id, "linha_ids": [linha["id"]]},
    )
    assert proposta.status_code == 201, proposta.text
    proposta_id = proposta.json()["id"]
    enviada = client.post(
        f"/v1/comercial/propostas/{proposta_id}/marcar-enviada",
        headers=h,
        json={"canal": "email", "avancar_funil": False},
    )
    assert enviada.status_code == 200, enviada.text

    contrato = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert contrato.status_code == 201, contrato.text
    contrato_id = contrato.json()["id"]
    marcado_enviado = client.post(
        f"/v1/comercial/contratos/{contrato_id}/marcar-enviado",
        headers=h,
        json={},
    )
    assert marcado_enviado.status_code == 200, marcado_enviado.text
    _anexar_pdf_assinado(client, h, contrato_id)
    assinado = client.post(
        f"/v1/comercial/contratos/{contrato_id}/marcar-assinado",
        headers=h,
        json={"abrir_ticket_implantacao": True},
    )
    assert assinado.status_code == 200, assinado.text
    ticket_impl_id = assinado.json()["implantacao_ticket_id"]
    assert ticket_impl_id

    checklist = client.get(f"/v1/tickets/{ticket_impl_id}/checklist", headers=h_admin)
    assert checklist.status_code == 200, checklist.text
    item = checklist.json()["itens"][0]
    concluido = client.patch(
        f"/v1/tickets/{ticket_impl_id}/checklist/itens/{item['id']}",
        headers=h_admin,
        json={"concluido": True},
    )
    assert concluido.status_code == 200, concluido.text

    status_fechado_id = _criar_status_fechado(client, h_admin)
    chamado = _criar_chamado(
        client,
        h_admin,
        empresa_id=empresa_id,
        setor_id=seed_base["setor1"].id,
        assunto="PDV sem comunicação",
    )

    ctx = {
        "neg_id": neg_id,
        "linha_id": linha["id"],
        "empresa_id": empresa_id,
        "proposta_id": proposta_id,
        "contrato_id": contrato_id,
        "ticket_implantacao_id": ticket_impl_id,
        "chamado_id": chamado["id"],
        "status_fechado_id": status_fechado_id,
    }

    if not reabrir:
        return ctx

    # Chamado que fica fechado (evento ticket_fechado) e chamado reaberto 2x
    # (eventos de reabertura via TicketHistorico).
    chamado_fechado = _criar_chamado(
        client,
        h_admin,
        empresa_id=empresa_id,
        setor_id=seed_base["setor1"].id,
        assunto="Impressora fiscal travada",
    )
    _fechar_chamado_db(db_session, chamado_fechado["id"], status_fechado_id)

    chamado_reaberto = _criar_chamado(
        client,
        h_admin,
        empresa_id=empresa_id,
        setor_id=seed_base["setor1"].id,
        assunto="Reincidência de queda de conexão",
    )
    _fechar_chamado_db(db_session, chamado_reaberto["id"], status_fechado_id)
    primeira = client.post(f"/v1/tickets/{chamado_reaberto['id']}/reabrir", headers=h_admin)
    assert primeira.status_code == 200, primeira.text
    _fechar_chamado_db(db_session, chamado_reaberto["id"], status_fechado_id)
    segunda = client.post(f"/v1/tickets/{chamado_reaberto['id']}/reabrir", headers=h_admin)
    assert segunda.status_code == 200, segunda.text

    ctx["chamado_fechado_id"] = chamado_fechado["id"]
    ctx["chamado_reaberto_id"] = chamado_reaberto["id"]
    return ctx


def _eventos(client, headers, empresa_id: int, **params) -> dict:
    r = client.get(
        "/v1/operacao/timeline",
        headers=headers,
        params={"empresa_id": empresa_id, "limit": 200, **params},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _saude(client, headers, empresa_id: int) -> dict:
    r = client.get(f"/v1/operacao/carteira/{empresa_id}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _criar_empresa_sem_historico(client, h_admin, seed_base, nome: str) -> int:
    r = client.post(
        "/v1/empresas",
        headers=h_admin,
        json={"rede_id": seed_base["rede"].id, "nome": nome},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _envelhecer_ticket(db_session, ticket_id: int, dias: int) -> None:
    ticket = db_session.get(Ticket, ticket_id)
    assert ticket is not None
    ticket.created_at = datetime.now(timezone.utc) - timedelta(days=dias)
    db_session.commit()


def _parse_em(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# #912 — timeline derivada
# ---------------------------------------------------------------------------


def test_timeline_derivada_completa_refs_e_ordem(client, auth_headers, seed_base, db_session):
    ctx = _fluxo_completo(client, auth_headers, seed_base, db_session, reabrir=True)
    h = auth_headers["comercial"]

    body = _eventos(client, h, ctx["empresa_id"])
    itens = body["items"]
    assert body["total"] == len(itens)
    assert body["total"] >= len(_TIPOS_ESPERADOS)

    tipos = {item["tipo"] for item in itens}
    for esperado in _TIPOS_ESPERADOS:
        assert esperado in tipos, f"evento {esperado} ausente da timeline"

    # ids estáveis e sem duplicidade (deduplicação)
    ids = [item["id"] for item in itens]
    assert len(ids) == len(set(ids))

    # categorias derivadas das três frentes
    categorias = {item["categoria"] for item in itens}
    assert categorias == {"crm", "implantacao", "suporte"}

    # todo evento navegável tem ref_tipo/ref_id; id do evento aponta para a origem
    for item in itens:
        assert item["titulo"].strip()
        assert item["ref_tipo"] in {
            "crm_negociacao",
            "comercial_proposta",
            "comercial_contrato",
            "ticket",
        }
        assert isinstance(item["ref_id"], int) and item["ref_id"] > 0

    # ordem padrão: mais recente primeiro
    ems = [_parse_em(item["em"]) for item in itens]
    assert ems == sorted(ems, reverse=True)

    # ordem crescente explícita
    asc = _eventos(client, h, ctx["empresa_id"], ordem="asc")
    ems_asc = [_parse_em(item["em"]) for item in asc["items"]]
    assert ems_asc == sorted(ems_asc)

    # referências de implantação e suporte apontam para os tickets certos
    refs_impl = {
        item["ref_id"]
        for item in itens
        if item["tipo"] == "implantacao_item_concluido"
    }
    assert refs_impl == {ctx["ticket_implantacao_id"]}
    reabertos = {item["ref_id"] for item in itens if item["tipo"] == "ticket_reaberto"}
    assert reabertos == {ctx["chamado_reaberto_id"]}
    chamados = {item["ref_id"] for item in itens if item["tipo"] == "ticket_criado"}
    assert chamados == {
        ctx["ticket_implantacao_id"],
        ctx["chamado_id"],
        ctx["chamado_fechado_id"],
        ctx["chamado_reaberto_id"],
    }
    contratos_ref = {
        item["ref_id"] for item in itens if item["ref_tipo"] == "comercial_contrato"
    }
    assert contratos_ref == {ctx["contrato_id"]}
    propostas_ref = {
        item["ref_id"] for item in itens if item["ref_tipo"] == "comercial_proposta"
    }
    assert propostas_ref == {ctx["proposta_id"]}


def test_timeline_filtros_categoria_periodo_e_validacao(client, auth_headers, seed_base, db_session):
    ctx = _fluxo_completo(client, auth_headers, seed_base, db_session, reabrir=True)
    h = auth_headers["comercial"]
    empresa_id = ctx["empresa_id"]
    completo = _eventos(client, h, empresa_id)

    # categoria única
    so_crm = _eventos(client, h, empresa_id, categorias="crm")
    assert so_crm["total"] < completo["total"]
    assert {item["categoria"] for item in so_crm["items"]} == {"crm"}

    # categorias repetidas (padrão FastAPI)
    r = client.get(
        "/v1/operacao/timeline",
        headers=h,
        params=[("empresa_id", empresa_id), ("categorias", "crm"), ("categorias", "suporte"), ("limit", 200)],
    )
    assert r.status_code == 200, r.text
    assert {item["categoria"] for item in r.json()["items"]} == {"crm", "suporte"}

    # categorias separadas por vírgula
    r2 = client.get(
        "/v1/operacao/timeline",
        headers=h,
        params={"empresa_id": empresa_id, "categorias": "crm,implantacao", "limit": 200},
    )
    assert r2.status_code == 200, r2.text
    assert {item["categoria"] for item in r2.json()["items"]} == {"crm", "implantacao"}

    # período: de/até recortam pela data do evento
    referencia = _parse_em(completo["items"][len(completo["items"]) // 2]["em"])
    de = referencia.isoformat()
    ate = referencia.isoformat()
    so_depois = _eventos(client, h, empresa_id, de=de)
    assert so_depois["total"] <= completo["total"]
    assert all(_parse_em(item["em"]) >= referencia for item in so_depois["items"])
    so_antes = _eventos(client, h, empresa_id, ate=ate)
    assert so_antes["total"] <= completo["total"]
    assert all(_parse_em(item["em"]) <= referencia for item in so_antes["items"])

    # período sem nenhum evento
    futuro = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    vazio = _eventos(client, h, empresa_id, de=futuro)
    assert vazio["total"] == 0 and vazio["items"] == []

    # categoria inválida
    invalida = client.get(
        "/v1/operacao/timeline",
        headers=h,
        params={"empresa_id": empresa_id, "categorias": "financeiro"},
    )
    assert invalida.status_code == 400
    assert "Categoria inválida" in invalida.json()["detail"]

    # empresa inexistente e empresa_id obrigatório
    assert client.get(
        "/v1/operacao/timeline", headers=h, params={"empresa_id": 999999}
    ).status_code == 404
    assert client.get("/v1/operacao/timeline", headers=h).status_code == 422


def test_timeline_paginacao(client, auth_headers, seed_base, db_session):
    ctx = _fluxo_completo(client, auth_headers, seed_base, db_session, reabrir=True)
    h = auth_headers["comercial"]
    empresa_id = ctx["empresa_id"]
    completo = _eventos(client, h, empresa_id)
    assert completo["total"] >= 6

    p1 = _eventos(client, h, empresa_id, limit=3, offset=0)
    p2 = _eventos(client, h, empresa_id, limit=3, offset=3)
    assert p1["total"] == completo["total"] == p2["total"]
    assert len(p1["items"]) == 3 and len(p2["items"]) == 3
    ids1 = {item["id"] for item in p1["items"]}
    ids2 = {item["id"] for item in p2["items"]}
    assert not (ids1 & ids2)
    assert ids1 | ids2 <= {item["id"] for item in completo["items"]}
    # paginação preserva a ordem global
    assert [i["id"] for i in completo["items"][:3]] == [i["id"] for i in p1["items"]]
    assert [i["id"] for i in completo["items"][3:6]] == [i["id"] for i in p2["items"]]

    # offset além do total devolve página vazia mantendo o total
    vazia = _eventos(client, h, empresa_id, limit=10, offset=500)
    assert vazia["items"] == [] and vazia["total"] == completo["total"]


def test_timeline_contrato_cancelado(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    _, linha = _negociacao_com_linha(client, h)
    contrato = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert contrato.status_code == 201, contrato.text
    contrato_id = contrato.json()["id"]

    cancelado = client.post(f"/v1/comercial/contratos/{contrato_id}/cancelar", headers=h)
    assert cancelado.status_code == 200, cancelado.text
    assert cancelado.json()["status"] == "cancelado"

    itens = _eventos(client, h, linha["empresa_id"])["items"]
    tipos = {item["tipo"] for item in itens}
    assert {"contrato_gerado", "contrato_cancelado", "negociacao_documento"} <= tipos
    evento = next(item for item in itens if item["tipo"] == "contrato_cancelado")
    assert evento["ref_tipo"] == "comercial_contrato"
    assert evento["ref_id"] == contrato_id


def test_timeline_rbac(client, auth_headers, seed_base, db_session):
    ctx = _fluxo_completo(client, auth_headers, seed_base, db_session)
    h_atendente = auth_headers["a1"]
    params = {"empresa_id": ctx["empresa_id"]}
    assert client.get("/v1/operacao/timeline", headers=h_atendente, params=params).status_code == 403
    assert client.get("/v1/operacao/carteira", headers=h_atendente).status_code == 403
    assert (
        client.get(
            f"/v1/operacao/carteira/{ctx['empresa_id']}", headers=h_atendente
        ).status_code
        == 403
    )
    assert client.get("/v1/operacao/timeline", params=params).status_code == 401


# ---------------------------------------------------------------------------
# #914 — saúde do cliente da carteira
# ---------------------------------------------------------------------------


def test_saude_saudavel_com_fluxo_recente(client, auth_headers, seed_base, db_session):
    ctx = _fluxo_completo(client, auth_headers, seed_base, db_session)
    h = auth_headers["comercial"]
    saude = _saude(client, h, ctx["empresa_id"])

    assert saude["status"] == "saudavel"
    assert saude["empresa_id"] == ctx["empresa_id"]
    assert saude["motivos"] == ["Nenhum sinal de atenção ou risco nas regras atuais."]

    sinais = {sinal["codigo"]: sinal for sinal in saude["sinais"]}
    assert {
        "dias_sem_movimento",
        "tickets_abertos",
        "reaberturas",
        "implantacao",
        "tempo_crm_assinatura",
    } <= set(sinais)
    assert sinais["dias_sem_movimento"]["nivel"] in {"saudavel", "atencao"}
    assert int(sinais["dias_sem_movimento"]["valor"].split()[0]) <= 1
    assert sinais["reaberturas"]["nivel"] == "saudavel"
    assert sinais["tempo_crm_assinatura"]["nivel"] == "info"
    assert "dia(s)" in sinais["tempo_crm_assinatura"]["valor"]


def test_saude_risco_por_reaberturas_repetidas(client, auth_headers, seed_base, db_session):
    ctx = _fluxo_completo(client, auth_headers, seed_base, db_session, reabrir=True)
    h = auth_headers["comercial"]
    saude = _saude(client, h, ctx["empresa_id"])

    assert saude["status"] == "risco"
    sinais = {sinal["codigo"]: sinal for sinal in saude["sinais"]}
    assert sinais["reaberturas"]["nivel"] == "risco"
    assert any("Reaberturas" in motivo for motivo in saude["motivos"])


def test_saude_atencao_e_risco_por_inatividade(client, auth_headers, seed_base, db_session):
    h_admin = auth_headers["admin"]
    h = auth_headers["comercial"]

    empresa_atencao = _criar_empresa_sem_historico(
        client, h_admin, seed_base, "Carteira Atenção 45d"
    )
    empresa_risco = _criar_empresa_sem_historico(
        client, h_admin, seed_base, "Carteira Risco 70d"
    )
    chamado_atencao = _criar_chamado(
        client,
        h_admin,
        empresa_id=empresa_atencao,
        setor_id=seed_base["setor1"].id,
        assunto="Sem retorno há 45 dias",
    )
    chamado_risco = _criar_chamado(
        client,
        h_admin,
        empresa_id=empresa_risco,
        setor_id=seed_base["setor1"].id,
        assunto="Sem retorno há 70 dias",
    )
    _envelhecer_ticket(db_session, chamado_atencao["id"], 45)
    _envelhecer_ticket(db_session, chamado_risco["id"], 70)

    saude_atencao = _saude(client, h, empresa_atencao)
    assert saude_atencao["status"] == "atencao"
    assert saude_atencao["dias_sem_movimento"] == 45
    sinais_atencao = {sinal["codigo"]: sinal for sinal in saude_atencao["sinais"]}
    assert sinais_atencao["dias_sem_movimento"]["nivel"] == "atencao"

    saude_risco = _saude(client, h, empresa_risco)
    assert saude_risco["status"] == "risco"
    assert saude_risco["dias_sem_movimento"] == 70
    sinais_risco = {sinal["codigo"]: sinal for sinal in saude_risco["sinais"]}
    assert sinais_risco["dias_sem_movimento"]["nivel"] == "risco"

    # filtro por status na listagem da carteira
    lista_risco = client.get(
        "/v1/operacao/carteira", headers=h, params={"status": "risco", "busca": "Carteira"}
    )
    assert lista_risco.status_code == 200, lista_risco.text
    corpo = lista_risco.json()
    assert corpo["total"] >= 1
    ids = {item["empresa_id"] for item in corpo["items"]}
    assert empresa_risco in ids
    assert empresa_atencao not in ids
    assert all(item["status"] == "risco" for item in corpo["items"])

    lista_atencao = client.get(
        "/v1/operacao/carteira", headers=h, params={"status": "atencao", "busca": "Carteira"}
    )
    assert lista_atencao.status_code == 200, lista_atencao.text
    ids_atencao = {item["empresa_id"] for item in lista_atencao.json()["items"]}
    assert empresa_atencao in ids_atencao
    assert empresa_risco not in ids_atencao


def test_saude_risco_por_implantacao_parada(client, auth_headers, seed_base, db_session):
    ctx = _fluxo_completo(client, auth_headers, seed_base, db_session)
    h = auth_headers["comercial"]
    # Ticket de implantação aberto e parado há 40 dias (itens obrigatórios pendentes).
    _envelhecer_implantacao(db_session, ctx["ticket_implantacao_id"], 40)
    db_session.expire_all()

    saude = _saude(client, h, ctx["empresa_id"])
    sinais = {sinal["codigo"]: sinal for sinal in saude["sinais"]}
    assert sinais["implantacao"]["nivel"] == "risco"
    assert "Implantação" in sinais["implantacao"]["rotulo"]
    assert saude["status"] == "risco"
    assert any("Implantação" in motivo for motivo in saude["motivos"])


def test_carteira_lista_sem_historico_e_busca(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    # seed_base cria "Empresa Teste" sem nenhum evento derivável.
    r = client.get("/v1/operacao/carteira", headers=h, params={"busca": "Empresa Teste"})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["total"] == 1
    item = corpo["items"][0]
    assert item["empresa_nome"] == "Empresa Teste"
    assert item["status"] == "atencao"
    sinais = {sinal["codigo"]: sinal for sinal in item["sinais"]}
    assert sinais["sem_historico"]["nivel"] == "atencao"
    assert item["ultimo_evento_em"] is None
    assert item["dias_sem_movimento"] is None
    assert item["motivos"]

    sem_resultado = client.get(
        "/v1/operacao/carteira", headers=h, params={"busca": "Não existe 999"}
    )
    assert sem_resultado.status_code == 200
    assert sem_resultado.json()["total"] == 0

    # paginação padrão da carteira
    pagina = client.get("/v1/operacao/carteira", headers=h, params={"limit": 1})
    assert pagina.status_code == 200
    assert len(pagina.json()["items"]) <= 1
    assert pagina.json()["total"] >= 1


def test_carteira_empresa_de_outro_tenant_nao_aparece(client, auth_headers, seed_base, db_session):
    from app.models import Empresa, Rede, Tenant

    outro_tenant = Tenant(nome="Outro", ativo=True)
    db_session.add(outro_tenant)
    db_session.flush()
    rede = Rede(tenant_id=outro_tenant.id, nome="Rede Outro", ativo=True)
    db_session.add(rede)
    db_session.flush()
    empresa = Empresa(tenant_id=outro_tenant.id, rede_id=rede.id, nome="Empresa Outro Tenant", ativo=True)
    db_session.add(empresa)
    db_session.commit()

    h = auth_headers["comercial"]
    assert client.get("/v1/operacao/carteira/999999", headers=h).status_code == 404
    assert (
        client.get(f"/v1/operacao/carteira/{empresa.id}", headers=h).status_code == 404
    )
    lista = client.get(
        "/v1/operacao/carteira", headers=h, params={"busca": "Empresa Outro Tenant"}
    )
    assert lista.status_code == 200
    assert lista.json()["total"] == 0
    assert (
        client.get(
            "/v1/operacao/timeline", headers=h, params={"empresa_id": empresa.id}
        ).status_code
        == 404
    )
