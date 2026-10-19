"""Cada código do catálogo bloqueia a ação quando falta e libera quando está marcado."""

import pytest

# (código, método, caminho). Corpo vazio nas mutações: 422/404/400 provam que o portão abriu.
PROBES = [
    ("admin", "GET", "/v1/audit"),
    ("comercial", "GET", "/v1/crm/leads"),
    ("operacional", "GET", "/v1/tickets"),
    ("tickets.ver", "GET", "/v1/tickets"),
    ("tickets.criar", "POST", "/v1/tickets"),
    ("tickets.editar", "PATCH", "/v1/tickets/999999"),
    ("atendimento.ver_todos", "GET", "/v1/tickets?atendente_id=1"),
    ("tickets.reabrir", "POST", "/v1/tickets/999999/reabrir"),
    ("chat.atender", "GET", "/v1/whatsapp/chats/fila"),
    ("chat.historico", "GET", "/v1/whatsapp/chats/encerrados"),
    ("chat.avaliacoes", "GET", "/v1/whatsapp/chats/avaliacoes"),
    ("whatsapp.atender", "GET", "/v1/whatsapp/chats/fila"),
    ("ponto.meu", "GET", "/v1/ponto/me"),
    ("ponto.equipe", "GET", "/v1/ponto/batidas/export.csv"),
    ("presenca.ver", "GET", "/v1/presenca/online"),
    ("dashboard.ver", "GET", "/v1/dashboard"),
    ("relatorios.ver", "GET", "/v1/relatorios/tickets"),
    ("crm.ver", "GET", "/v1/crm/leads"),
    ("crm.criar", "POST", "/v1/crm/leads"),
    ("crm.editar", "PATCH", "/v1/crm/leads/999999"),
    ("funil.ver", "GET", "/v1/crm/funil-estagios"),
    ("funil.editar", "POST", "/v1/crm/funil-estagios"),
    ("propostas.ver", "GET", "/v1/comercial/proposta-templates"),
    ("propostas.emitir", "POST", "/v1/comercial/propostas"),
    ("propostas.modelos", "POST", "/v1/comercial/proposta-templates"),
    ("contratos.ver", "GET", "/v1/comercial/contratos"),
    ("contratos.ver_todos", "GET", "/v1/comercial/contratos?responsavel_id=999999"),
    ("contratos.emitir", "POST", "/v1/comercial/contratos"),
    ("contratos.cancelar", "POST", "/v1/comercial/contratos/999999/cancelar"),
    ("contratos.modelos", "POST", "/v1/comercial/contrato-templates"),
    ("contratos.politica", "PATCH", "/v1/comercial/contrato-politica"),
    ("custos.ver", "GET", "/v1/comercial/custos/itens"),
    ("custos.simular", "POST", "/v1/comercial/custos/simular"),
    ("custos.editar", "POST", "/v1/comercial/salario-minimo"),
    ("implantacao.ver", "GET", "/v1/comercial/implantacao-templates"),
    ("implantacao.editar", "POST", "/v1/comercial/implantacao-templates"),
    ("tipos_negocio.ver", "GET", "/v1/tipos-negocio/999999"),
    ("tipos_negocio.criar", "POST", "/v1/tipos-negocio"),
    ("tipos_negocio.editar", "PATCH", "/v1/tipos-negocio/999999"),
    ("tipos_negocio.excluir", "DELETE", "/v1/tipos-negocio/999999"),
    ("faturamento.ver", "GET", "/v1/faturamento/faturas"),
    ("faturamento.gerar", "POST", "/v1/faturamento/faturas"),
    ("faturamento.aprovar", "POST", "/v1/faturamento/faturas/999999/aprovar"),
    ("redes.ver", "GET", "/v1/redes"),
    ("redes.criar", "POST", "/v1/redes"),
    ("redes.editar", "PATCH", "/v1/redes/999999"),
    ("redes.excluir", "DELETE", "/v1/redes/999999"),
    ("empresas.ver", "GET", "/v1/empresas/999999"),
    ("empresas.criar", "POST", "/v1/empresas"),
    ("empresas.editar", "PATCH", "/v1/empresas/999999"),
    ("empresas.excluir", "DELETE", "/v1/empresas/999999"),
    ("funcionarios.ver", "GET", "/v1/funcionarios-rede"),
    ("funcionarios.criar", "POST", "/v1/funcionarios-rede"),
    ("funcionarios.editar", "PATCH", "/v1/funcionarios-rede/999999"),
    ("funcionarios.excluir", "DELETE", "/v1/funcionarios-rede/999999"),
    ("ajuda.consultar", "GET", "/v1/kb/articles/consulta"),
    ("ajuda.categorias.ver", "GET", "/v1/kb/categories"),
    ("ajuda.categorias.criar", "POST", "/v1/kb/categories"),
    ("ajuda.categorias.editar", "PATCH", "/v1/kb/categories/999999"),
    ("ajuda.categorias.excluir", "DELETE", "/v1/kb/categories/999999"),
    ("ajuda.artigos.ver", "GET", "/v1/kb/articles"),
    ("ajuda.artigos.criar", "POST", "/v1/kb/articles"),
    ("ajuda.artigos.editar", "PATCH", "/v1/kb/articles/999999"),
    ("ajuda.artigos.excluir", "POST", "/v1/kb/articles/excluir-lote"),
    ("ajuda.portal", "GET", "/v1/kb/portal-settings"),
    ("setores.ver", "GET", "/v1/setores/999999"),
    ("setores.criar", "POST", "/v1/setores"),
    ("setores.editar", "PATCH", "/v1/setores/999999"),
    ("setores.excluir", "DELETE", "/v1/setores/999999"),
    ("atendentes.ver", "GET", "/v1/atendentes"),
    ("atendentes.criar", "POST", "/v1/atendentes"),
    ("atendentes.editar", "PATCH", "/v1/atendentes/999999"),
    ("atendentes.excluir", "DELETE", "/v1/atendentes/999999"),
    ("grupos.ver", "GET", "/v1/permissao-grupos"),
    ("grupos.criar", "POST", "/v1/permissao-grupos"),
    ("grupos.editar", "PATCH", "/v1/permissao-grupos/999999"),
    ("grupos.excluir", "DELETE", "/v1/permissao-grupos/999999"),
    ("status_ticket.ver", "GET", "/v1/status-ticket/999999"),
    ("status_ticket.criar", "POST", "/v1/status-ticket"),
    ("status_ticket.editar", "PATCH", "/v1/status-ticket/999999"),
    ("status_ticket.excluir", "DELETE", "/v1/status-ticket/999999"),
    ("natureza.ver", "GET", "/v1/ticket-naturezas"),
    ("natureza.criar", "POST", "/v1/ticket-naturezas"),
    ("natureza.editar", "PATCH", "/v1/ticket-naturezas/999999"),
    ("respostas.ver", "GET", "/v1/respostas-prontas"),
    ("respostas.criar", "POST", "/v1/respostas-prontas"),
    ("respostas.editar", "PATCH", "/v1/respostas-prontas/999999"),
    ("respostas.excluir", "DELETE", "/v1/respostas-prontas/999999"),
    ("roteamento.ver", "GET", "/v1/routing/rules"),
    ("roteamento.editar", "POST", "/v1/routing/rules"),
    ("sla.ver", "GET", "/v1/sla/calendars"),
    ("sla.editar", "POST", "/v1/sla/calendars"),
    ("canais.whatsapp.ver", "GET", "/v1/settings/whatsapp"),
    ("canais.whatsapp.editar", "PATCH", "/v1/settings/whatsapp"),
    ("canais.email.ver", "GET", "/v1/settings/email"),
    ("canais.email.editar", "PUT", "/v1/settings/email"),
    ("instalacao.ver", "GET", "/v1/settings/empresa-sistema"),
    ("instalacao.editar", "PUT", "/v1/settings/empresa-sistema"),
    ("pdv.ver", "GET", "/v1/pdv-rotulos"),
    ("pdv.editar", "POST", "/v1/pdv-rotulos"),
    ("pdv.acessos.ver", "GET", "/v1/empresas/999999/pdvs"),
    ("rustdesk.monitorar", "GET", "/v1/rustdesk/peers"),
    ("auditoria.ver", "GET", "/v1/audit"),
    ("solicitacoes.ver", "GET", "/v1/solicitacoes-melhoria/admin"),
    ("solicitacoes.editar", "PATCH", "/v1/solicitacoes-melhoria/999999/status"),
]

# O filtro por atendente só é alcançado depois de poder ver tickets.
PRE_REQUISITO = {
    "atendimento.ver_todos": ["tickets.ver"],
    "contratos.ver_todos": ["contratos.ver"],
}


def test_toda_permissao_do_catalogo_tem_prova():
    from app.services.permissao_grupos import CATALOGO

    cobertos = {codigo for codigo, _, _ in PROBES} | {"chat.encerrar_sem_demanda"}
    catalogo = {item[1] for item in CATALOGO}
    assert catalogo == cobertos


def _atribuir(client, auth_headers, seed_base, codigos, nome):
    criado = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={"nome": nome, "permissoes": codigos},
    )
    assert criado.status_code == 201, criado.text
    patch = client.patch(
        f"/v1/atendentes/{seed_base['a1'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [criado.json()["id"]]},
    )
    assert patch.status_code == 200, patch.text
    return auth_headers["a1"]


def _chamar(client, metodo, caminho, headers):
    kwargs = {"headers": headers}
    if metodo != "GET":
        kwargs["json"] = {}
    return client.request(metodo, caminho, **kwargs)


def _negados(codigo: str) -> list[str]:
    if codigo in PRE_REQUISITO:
        return list(PRE_REQUISITO[codigo])
    if codigo == "presenca.ver":
        return ["auditoria.ver"]
    return ["presenca.ver"]


@pytest.mark.parametrize("codigo,metodo,caminho", PROBES, ids=[p[0] for p in PROBES])
def test_sem_a_permissao_a_acao_e_bloqueada(client, auth_headers, seed_base, codigo, metodo, caminho):
    headers = _atribuir(client, auth_headers, seed_base, _negados(codigo), f"Sem {codigo}")
    resposta = _chamar(client, metodo, caminho, headers)
    assert resposta.status_code == 403, (codigo, resposta.status_code, resposta.text)


@pytest.mark.parametrize("codigo,metodo,caminho", PROBES, ids=[p[0] for p in PROBES])
def test_com_a_permissao_a_acao_passa_do_portao(client, auth_headers, seed_base, codigo, metodo, caminho):
    headers = _atribuir(
        client,
        auth_headers,
        seed_base,
        [codigo, *PRE_REQUISITO.get(codigo, [])],
        f"Com {codigo}",
    )
    resposta = _chamar(client, metodo, caminho, headers)
    assert resposta.status_code != 403, (codigo, resposta.status_code, resposta.text)


def test_encerrar_chat_sem_demanda_bloqueia_e_libera(client, auth_headers, seed_base, db_session):
    from app.models.whatsapp_chat import WhatsappChat

    chat = WhatsappChat(
        protocolo="WPP-CATALOGO-1",
        wa_id="5511977776666",
        cliente_nome="Cliente",
        estado="em_atendimento",
        atendente_id=seed_base["a1"].id,
    )
    db_session.add(chat)
    db_session.commit()
    caminho = f"/v1/whatsapp/chats/{chat.id}/encerrar"

    sem = _atribuir(client, auth_headers, seed_base, ["presenca.ver"], "Sem encerrar")
    bloqueado = client.post(caminho, headers=sem)
    assert bloqueado.status_code == 403, bloqueado.text

    com = _atribuir(client, auth_headers, seed_base, ["chat.encerrar_sem_demanda"], "Com encerrar")
    liberado = client.post(caminho, headers=com)
    assert liberado.status_code != 403, liberado.text
