"""Grupos de permissão: catálogo, grupos padrão e perfil derivado (#S202609-0024)."""

from __future__ import annotations

import re
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.atendente import Atendente
from app.models.permissao_grupo import PermissaoGrupo, PermissaoGrupoItem

# módulo, código, nome, descrição, pacote (comercial ou operacional implicam o item).
# `admin` libera o catálogo inteiro.
CATALOGO: tuple[tuple[str, str, str, str, str], ...] = (
    ("Acesso", "admin", "Acesso total", "Libera todas as permissões da instância.", ""),
    ("Acesso", "comercial", "Pacote comercial", "CRM, propostas, contratos e simulação de custos.", ""),
    ("Acesso", "operacional", "Pacote de atendimento", "Tickets, chats, ponto próprio e consulta da ajuda, nos setores da pessoa.", ""),
    ("Atendimento", "tickets.ver", "Visualizar tickets", "Ver tickets dos próprios setores.", "operacional"),
    ("Atendimento", "tickets.criar", "Criar tickets", "Abrir tickets nos próprios setores.", "operacional"),
    ("Atendimento", "tickets.editar", "Editar tickets", "Alterar tickets dos próprios setores.", "operacional"),
    ("Atendimento", "atendimento.ver_todos", "Ver todos os setores", "Ver e mover tickets, chats e histórico fora dos setores da pessoa.", ""),
    ("Atendimento", "tickets.reabrir", "Reabrir ticket", "Alterar ou reabrir ticket já fechado.", ""),
    ("Chat", "chat.atender", "Atender chat", "Atender chats dos próprios setores.", "operacional"),
    ("Chat", "chat.historico", "Histórico", "Consultar o histórico dos próprios setores.", "operacional"),
    ("Chat", "chat.encerrar_sem_demanda", "Encerrar sem demanda", "Finalizar o chat sem registrar a demanda da sessão.", ""),
    ("Chat", "chat.avaliacoes", "Avaliações", "Ver as avaliações dos chats.", ""),
    ("WhatsApp", "whatsapp.atender", "Atender WhatsApp", "Usar a fila e os chats de WhatsApp dos próprios setores.", "operacional"),
    ("Ponto", "ponto.meu", "Meu ponto", "Registrar e consultar o próprio ponto.", "operacional"),
    ("Ponto", "ponto.equipe", "Ponto da equipe", "Ver e ajustar o ponto da equipe, competências e locais.", ""),
    ("Ponto", "presenca.ver", "Equipe online", "Ver quem está online.", ""),
    ("Dashboard", "dashboard.ver", "Dashboard", "Ver os painéis dos próprios setores.", "operacional"),
    ("Relatórios", "relatorios.ver", "Relatórios", "Ver relatórios de tickets e chats.", ""),
    ("CRM", "crm.ver", "Visualizar", "Ver leads e negociações.", "comercial"),
    ("CRM", "crm.criar", "Criar", "Cadastrar leads e negociações.", "comercial"),
    ("CRM", "crm.editar", "Editar", "Alterar leads, negociações e atividades.", "comercial"),
    ("CRM", "funil.ver", "Ver funil", "Ver os estágios do funil.", "comercial"),
    ("CRM", "funil.editar", "Editar funil", "Cadastrar e alterar estágios do funil.", ""),
    ("Propostas", "propostas.ver", "Visualizar", "Ver propostas e modelos ativos.", "comercial"),
    ("Propostas", "propostas.emitir", "Emitir", "Gerar proposta e marcar como enviada.", "comercial"),
    ("Propostas", "propostas.modelos", "Modelos", "Cadastrar e alterar modelos de proposta.", ""),
    ("Contratos", "contratos.ver", "Visualizar", "Ver contratos, modelos ativos e a política de reajuste.", "comercial"),
    ("Contratos", "contratos.ver_todos", "Ver todos", "Ver contratos de qualquer responsável.", ""),
    ("Contratos", "contratos.emitir", "Emitir", "Gerar contrato, enviar e marcar como assinado.", "comercial"),
    ("Contratos", "contratos.cancelar", "Cancelar", "Cancelar ou rescindir contrato.", "comercial"),
    ("Contratos", "contratos.modelos", "Modelos", "Cadastrar e alterar modelos de contrato.", ""),
    ("Contratos", "contratos.politica", "Política de reajuste", "Alterar o percentual e o rótulo padrão de reajuste.", ""),
    ("Custos", "custos.ver", "Visualizar catálogo", "Ver itens de custo e salário mínimo vigente.", "comercial"),
    ("Custos", "custos.simular", "Simular", "Simular custo na negociação.", "comercial"),
    ("Custos", "custos.editar", "Editar catálogo", "Cadastrar e alterar salário mínimo e itens de custo.", ""),
    ("Implantação", "implantacao.ver", "Visualizar checklist", "Ver o checklist de implantação.", "comercial"),
    ("Implantação", "implantacao.editar", "Editar checklist", "Cadastrar e alterar itens do checklist.", ""),
    ("Tipos de negócio", "tipos_negocio.ver", "Visualizar", "Ver tipos de negócio.", ""),
    ("Tipos de negócio", "tipos_negocio.criar", "Criar", "Cadastrar tipos de negócio.", ""),
    ("Tipos de negócio", "tipos_negocio.editar", "Editar", "Alterar tipos de negócio.", ""),
    ("Tipos de negócio", "tipos_negocio.excluir", "Excluir", "Excluir tipos de negócio.", ""),
    ("Faturamento", "faturamento.ver", "Visualizar", "Ver faturas e contratos elegíveis.", ""),
    ("Faturamento", "faturamento.gerar", "Gerar", "Gerar faturas.", ""),
    ("Faturamento", "faturamento.aprovar", "Aprovar", "Aprovar ou rejeitar faturas.", ""),
    ("Redes", "redes.ver", "Visualizar", "Ver o cadastro de redes.", ""),
    ("Redes", "redes.criar", "Criar", "Cadastrar redes.", ""),
    ("Redes", "redes.editar", "Editar", "Alterar redes.", ""),
    ("Redes", "redes.excluir", "Excluir", "Excluir redes.", ""),
    ("Empresas", "empresas.ver", "Visualizar", "Ver o cadastro completo de empresas.", ""),
    ("Empresas", "empresas.criar", "Criar", "Cadastrar empresas.", ""),
    ("Empresas", "empresas.editar", "Editar", "Alterar empresas e PDVs.", ""),
    ("Empresas", "empresas.excluir", "Excluir", "Excluir empresas.", ""),
    ("Funcionários da rede", "funcionarios.ver", "Visualizar", "Ver funcionários da rede.", ""),
    ("Funcionários da rede", "funcionarios.criar", "Criar", "Cadastrar funcionários da rede.", ""),
    ("Funcionários da rede", "funcionarios.editar", "Editar", "Alterar funcionários da rede.", ""),
    ("Funcionários da rede", "funcionarios.excluir", "Excluir", "Excluir funcionários da rede.", ""),
    ("Ajuda", "ajuda.consultar", "Consultar", "Consultar artigos publicados.", "operacional"),
    ("Ajuda", "ajuda.categorias.ver", "Ver categorias", "Ver o cadastro de categorias da ajuda.", ""),
    ("Ajuda", "ajuda.categorias.criar", "Criar categorias", "Cadastrar categorias da ajuda.", ""),
    ("Ajuda", "ajuda.categorias.editar", "Editar categorias", "Alterar e reordenar categorias da ajuda.", ""),
    ("Ajuda", "ajuda.categorias.excluir", "Excluir categorias", "Excluir categorias da ajuda.", ""),
    ("Ajuda", "ajuda.artigos.ver", "Ver artigos", "Ver o cadastro de artigos, versões e vínculos.", ""),
    ("Ajuda", "ajuda.artigos.criar", "Criar artigos", "Cadastrar artigos e enviar imagens.", ""),
    ("Ajuda", "ajuda.artigos.editar", "Editar artigos", "Alterar, publicar e arquivar artigos.", ""),
    ("Ajuda", "ajuda.artigos.excluir", "Excluir artigos", "Excluir artigos.", ""),
    ("Ajuda", "ajuda.portal", "Portal", "Personalizar o portal público da base de conhecimento.", ""),
    ("Setores", "setores.ver", "Visualizar", "Ver o cadastro de setores.", ""),
    ("Setores", "setores.criar", "Criar", "Cadastrar setores.", ""),
    ("Setores", "setores.editar", "Editar", "Alterar setores e a distribuição.", ""),
    ("Setores", "setores.excluir", "Excluir", "Excluir setores.", ""),
    ("Atendentes", "atendentes.ver", "Visualizar", "Ver o cadastro de atendentes.", ""),
    ("Atendentes", "atendentes.criar", "Criar", "Cadastrar atendentes.", ""),
    ("Atendentes", "atendentes.editar", "Editar", "Alterar atendentes.", ""),
    ("Atendentes", "atendentes.excluir", "Excluir", "Excluir atendentes.", ""),
    ("Grupos de permissão", "grupos.ver", "Visualizar", "Ver grupos de permissão.", ""),
    ("Grupos de permissão", "grupos.criar", "Criar", "Cadastrar grupos de permissão.", ""),
    ("Grupos de permissão", "grupos.editar", "Editar", "Alterar grupos de permissão.", ""),
    ("Grupos de permissão", "grupos.excluir", "Excluir", "Excluir grupos de permissão.", ""),
    ("Status de ticket", "status_ticket.ver", "Visualizar", "Ver o cadastro de status.", ""),
    ("Status de ticket", "status_ticket.criar", "Criar", "Cadastrar status.", ""),
    ("Status de ticket", "status_ticket.editar", "Editar", "Alterar status.", ""),
    ("Status de ticket", "status_ticket.excluir", "Excluir", "Excluir status.", ""),
    ("Natureza e motivo", "natureza.ver", "Visualizar", "Ver naturezas e motivos.", ""),
    ("Natureza e motivo", "natureza.criar", "Criar", "Cadastrar naturezas e motivos.", ""),
    ("Natureza e motivo", "natureza.editar", "Editar", "Alterar naturezas e motivos.", ""),
    ("Respostas prontas", "respostas.ver", "Visualizar", "Ver respostas prontas.", ""),
    ("Respostas prontas", "respostas.criar", "Criar", "Cadastrar respostas prontas.", ""),
    ("Respostas prontas", "respostas.editar", "Editar", "Alterar respostas prontas.", ""),
    ("Respostas prontas", "respostas.excluir", "Excluir", "Excluir respostas prontas.", ""),
    ("Roteamento", "roteamento.ver", "Visualizar", "Ver regras de roteamento.", ""),
    ("Roteamento", "roteamento.editar", "Editar", "Cadastrar, simular e excluir regras de roteamento.", ""),
    ("SLA", "sla.ver", "Visualizar", "Ver calendários e políticas de SLA.", ""),
    ("SLA", "sla.editar", "Editar", "Cadastrar e alterar calendários e políticas de SLA.", ""),
    ("Canais", "canais.whatsapp.ver", "Ver WhatsApp", "Ver a configuração do WhatsApp.", ""),
    ("Canais", "canais.whatsapp.editar", "Editar WhatsApp", "Alterar a conexão e as mensagens do WhatsApp.", ""),
    ("Canais", "canais.email.ver", "Ver e-mail", "Ver a configuração de e-mail e os endereços de entrada.", ""),
    ("Canais", "canais.email.editar", "Editar e-mail", "Alterar o e-mail e os endereços de entrada.", ""),
    ("Instalação", "instalacao.ver", "Visualizar", "Ver os dados da instalação.", ""),
    ("Instalação", "instalacao.editar", "Editar", "Alterar os dados e a logo da instalação.", ""),
    ("PDV", "pdv.ver", "Visualizar", "Ver os catálogos de PDV.", ""),
    ("PDV", "pdv.editar", "Editar", "Alterar os catálogos de PDV.", ""),
    ("PDV", "pdv.acessos.ver", "Ver acessos da empresa", "Ver os PDVs da empresa e o código de acesso remoto, sem o cadastro da empresa.", "operacional"),
    ("Auditoria", "auditoria.ver", "Visualizar", "Ver o histórico de alterações.", ""),
    ("Sugestões", "solicitacoes.ver", "Visualizar", "Ver sugestões enviadas pelos clientes.", ""),
    ("Sugestões", "solicitacoes.editar", "Editar", "Triar sugestões e sincronizar o acompanhamento.", ""),
)
CODIGOS_VALIDOS = {c[1] for c in CATALOGO}
PACOTE_OPERACIONAL = frozenset(c[1] for c in CATALOGO if c[4] == "operacional")
PACOTE_COMERCIAL = frozenset(c[1] for c in CATALOGO if c[4] == "comercial")
# Catálogo da primeira versão, só com os três perfis. Grupos padrão nessa forma recebem o modelo novo.
CODIGOS_ANTIGOS = {"admin", "comercial", "operacional"}

# slug, nome, códigos. O slug estável liga quem já existia pelo perfil antigo.
GRUPOS_SISTEMA: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("administrador", "Administrador", ("admin",)),
    ("comercial", "Comercial", ("comercial", "chat.encerrar_sem_demanda")),
    ("atendente", "Operação", ("operacional", "chat.encerrar_sem_demanda")),
)
SLUG_POR_ROLE = {
    "admin": "administrador",
    "comercial": "comercial",
    "atendente": "atendente",
}


def _recurso(codigo: str) -> str:
    if "." not in codigo:
        return ""
    return codigo.rsplit(".", 1)[0]


_VER_POR_RECURSO = {_recurso(c[1]): c[1] for c in CATALOGO if c[1].endswith(".ver")}


def completar_ver(codigos: list[str]) -> list[str]:
    """Criar, editar ou outra ação do mesmo recurso exige visualizar."""
    out = list(codigos)
    for codigo in list(out):
        ver = _VER_POR_RECURSO.get(_recurso(codigo))
        if ver and ver not in out:
            out.append(ver)
    return out


def role_de_codigos(codigos: set[str]) -> str:
    """O perfil mais amplo vence: administrador, depois comercial, depois operação.

    Uma ação comercial isolada não vira o perfil comercial. O conjunto inteiro do pacote, sim.
    """
    if "admin" in codigos:
        return "admin"
    if "comercial" in codigos or PACOTE_COMERCIAL <= codigos:
        return "comercial"
    return "atendente"


def codigos_de(atendente: Atendente) -> set[str]:
    out: set[str] = set()
    for grupo in atendente.grupos_permissao or []:
        for item in grupo.itens or []:
            out.add(item.codigo)
    return out


def _legado_sem_grupo(atendente: Atendente, codigos: set[str]) -> bool:
    return not codigos and atendente.role in ("atendente", "comercial")


def tem_permissao(atendente: Atendente, codigo: str) -> bool:
    """Acesso total libera o catálogo. Pacotes e o perfil antigo cobrem quem ainda não foi detalhado."""
    if atendente.role == "saas_ops":
        return False
    codigos = codigos_de(atendente)
    if atendente.role == "admin" or "admin" in codigos:
        return True
    if codigo in codigos:
        return True
    comercial = "comercial" in codigos or (not codigos and atendente.role == "comercial")
    if comercial and (codigo == "comercial" or codigo in PACOTE_COMERCIAL):
        return True
    operacional = "operacional" in codigos or _legado_sem_grupo(atendente, codigos)
    if operacional and (codigo == "operacional" or codigo in PACOTE_OPERACIONAL):
        return True
    if codigo == "chat.encerrar_sem_demanda" and _legado_sem_grupo(atendente, codigos):
        return True
    return False


def codigos_efetivos(atendente: Atendente) -> list[str]:
    """Códigos que a pessoa realmente tem, já com pacotes e acesso total expandidos."""
    if atendente.role == "saas_ops":
        return []
    return [item[1] for item in CATALOGO if tem_permissao(atendente, item[1])]


def exigir_demanda_ou_permissao(db: Session, atendente: Atendente, *, chat_id: int, modelo) -> None:
    existe = db.query(modelo.id).filter(modelo.chat_id == chat_id).limit(1).first()
    if existe or tem_permissao(atendente, "chat.encerrar_sem_demanda"):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Sem permissão para encerrar o chat sem registrar demanda.",
    )


def sincronizar_role(atendente: Atendente) -> None:
    if atendente.role == "saas_ops":
        return
    codigos = codigos_de(atendente)
    if not codigos:
        return
    atendente.role = role_de_codigos(codigos)


def garantir_admin_ativo(db: Session, tenant_id: int) -> None:
    n = (
        db.query(Atendente)
        .filter(
            Atendente.tenant_id == tenant_id,
            Atendente.ativo.is_(True),
            Atendente.role == "admin",
        )
        .count()
    )
    if n < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A instância precisa de pelo menos um administrador ativo.",
        )


def _slugify(nome: str) -> str:
    texto = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")
    return (slug or "grupo")[:60]


def _validar_codigos(codigos: list[str]) -> list[str]:
    limpos: list[str] = []
    for bruto in codigos:
        codigo = (bruto or "").strip().lower()
        if not codigo:
            continue
        if codigo not in CODIGOS_VALIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permissão inválida.",
            )
        if codigo not in limpos:
            limpos.append(codigo)
    limpos = completar_ver(limpos)
    if not limpos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O grupo precisa de pelo menos uma permissão.",
        )
    return limpos


def _substituir_itens(grupo: PermissaoGrupo, codigos: list[str]) -> None:
    grupo.itens.clear()
    for codigo in codigos:
        grupo.itens.append(PermissaoGrupoItem(codigo=codigo))


def ensure_sistema(db: Session, tenant_id: int) -> bool:
    """Cria os grupos padrão e liga quem ainda não tem grupo (sem mexer em saas_ops).

    Só faz flush. Quem chamou confirma com commit — um GET que não gravou nada não commita.
    """
    slugs = {
        row[0]
        for row in db.query(PermissaoGrupo.slug)
        .filter(PermissaoGrupo.tenant_id == tenant_id, PermissaoGrupo.sistema.is_(True))
        .all()
    }
    faltam_grupos = [g for g in GRUPOS_SISTEMA if g[0] not in slugs]
    falta_pessoa = (
        db.query(Atendente.id)
        .filter(
            Atendente.tenant_id == tenant_id,
            Atendente.role != "saas_ops",
            ~Atendente.grupos_permissao.any(),
        )
        .first()
    )
    padrao_antigo = False
    if not faltam_grupos:
        atuais = (
            db.query(PermissaoGrupo)
            .options(selectinload(PermissaoGrupo.itens))
            .filter(PermissaoGrupo.tenant_id == tenant_id, PermissaoGrupo.sistema.is_(True))
            .all()
        )
        por_atual = {g.slug: {i.codigo for i in (g.itens or [])} for g in atuais}
        for slug, _, codigos in GRUPOS_SISTEMA:
            cod = por_atual.get(slug)
            if cod is not None and cod <= CODIGOS_ANTIGOS and set(codigos) != cod:
                padrao_antigo = True
                break
    if not faltam_grupos and not falta_pessoa and not padrao_antigo:
        return False

    por_slug: dict[str, PermissaoGrupo] = {
        g.slug: g
        for g in db.query(PermissaoGrupo)
        .options(joinedload(PermissaoGrupo.itens))
        .filter(PermissaoGrupo.tenant_id == tenant_id)
        .all()
    }
    for slug, nome, codigos in GRUPOS_SISTEMA:
        grupo = por_slug.get(slug)
        if grupo is None:
            grupo = PermissaoGrupo(tenant_id=tenant_id, nome=nome, slug=slug, sistema=True)
            _substituir_itens(grupo, list(codigos))
            db.add(grupo)
            db.flush()
            por_slug[slug] = grupo
        else:
            atuais = {i.codigo for i in (grupo.itens or [])}
            if grupo.sistema and atuais <= CODIGOS_ANTIGOS and set(codigos) != atuais:
                _substituir_itens(grupo, list(codigos))

    faltantes = (
        db.query(Atendente)
        .options(joinedload(Atendente.grupos_permissao))
        .filter(
            Atendente.tenant_id == tenant_id,
            Atendente.role != "saas_ops",
            ~Atendente.grupos_permissao.any(),
        )
        .all()
    )
    for pessoa in faltantes:
        slug = SLUG_POR_ROLE.get(pessoa.role or "", "atendente")
        grupo = por_slug.get(slug) or por_slug.get("atendente")
        if grupo is not None:
            pessoa.grupos_permissao.append(grupo)
    db.flush()
    return True


def listar(db: Session, tenant_id: int) -> tuple[list[PermissaoGrupo], bool]:
    mudou = ensure_sistema(db, tenant_id)
    rows = (
        db.query(PermissaoGrupo)
        .options(selectinload(PermissaoGrupo.itens), selectinload(PermissaoGrupo.atendentes))
        .filter(PermissaoGrupo.tenant_id == tenant_id)
        .order_by(PermissaoGrupo.sistema.desc(), PermissaoGrupo.nome.asc(), PermissaoGrupo.id.asc())
        .all()
    )
    return rows, mudou


def obter(db: Session, tenant_id: int, grupo_id: int) -> PermissaoGrupo:
    grupo = (
        db.query(PermissaoGrupo)
        .options(selectinload(PermissaoGrupo.itens), selectinload(PermissaoGrupo.atendentes))
        .filter(PermissaoGrupo.tenant_id == tenant_id, PermissaoGrupo.id == grupo_id)
        .first()
    )
    if not grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo não encontrado")
    return grupo


def _slug_livre(db: Session, tenant_id: int, base: str) -> str:
    slug = base
    n = 2
    while (
        db.query(PermissaoGrupo.id)
        .filter(PermissaoGrupo.tenant_id == tenant_id, PermissaoGrupo.slug == slug)
        .first()
    ):
        slug = f"{base[:56]}-{n}"
        n += 1
    return slug


def criar(db: Session, tenant_id: int, nome: str, permissoes: list[str]) -> PermissaoGrupo:
    ensure_sistema(db, tenant_id)
    codigos = _validar_codigos(permissoes)
    titulo = nome.strip()
    if len(titulo) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome do grupo.")
    grupo = PermissaoGrupo(
        tenant_id=tenant_id,
        nome=titulo,
        slug=_slug_livre(db, tenant_id, _slugify(titulo)),
        sistema=False,
    )
    _substituir_itens(grupo, codigos)
    db.add(grupo)
    db.flush()
    return grupo


def atualizar(
    db: Session,
    grupo: PermissaoGrupo,
    *,
    nome: str | None,
    permissoes: list[str] | None,
) -> None:
    if nome is not None:
        titulo = nome.strip()
        if len(titulo) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome do grupo.")
        grupo.nome = titulo
    if permissoes is not None:
        _substituir_itens(grupo, _validar_codigos(permissoes))
        db.flush()
        for pessoa in list(grupo.atendentes):
            sincronizar_role(pessoa)
        db.flush()
        garantir_admin_ativo(db, grupo.tenant_id)


def excluir(db: Session, grupo: PermissaoGrupo) -> None:
    if grupo.sistema:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grupos padrão não podem ser excluídos.",
        )
    if grupo.atendentes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Remova as pessoas deste grupo antes de excluir.",
        )
    db.delete(grupo)


def _pessoa_do_grupo(db: Session, grupo: PermissaoGrupo, atendente_id: int) -> Atendente:
    pessoa = (
        db.query(Atendente)
        .options(selectinload(Atendente.grupos_permissao))
        .filter(
            Atendente.tenant_id == grupo.tenant_id,
            Atendente.id == atendente_id,
            Atendente.role != "saas_ops",
        )
        .first()
    )
    if pessoa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pessoa não encontrada.")
    return pessoa


def listar_membros(grupo: PermissaoGrupo) -> list[Atendente]:
    return sorted(grupo.atendentes or [], key=lambda pessoa: ((pessoa.nome or "").lower(), pessoa.id))


def listar_candidatos(db: Session, grupo: PermissaoGrupo) -> list[Atendente]:
    membros = {pessoa.id for pessoa in (grupo.atendentes or [])}
    rows = (
        db.query(Atendente)
        .filter(
            Atendente.tenant_id == grupo.tenant_id,
            Atendente.role != "saas_ops",
            Atendente.ativo.is_(True),
        )
        .order_by(Atendente.nome.asc(), Atendente.id.asc())
        .all()
    )
    return [pessoa for pessoa in rows if pessoa.id not in membros]


def vincular_membro(db: Session, grupo: PermissaoGrupo, atendente_id: int) -> Atendente:
    pessoa = _pessoa_do_grupo(db, grupo, atendente_id)
    ids = [item.id for item in (pessoa.grupos_permissao or [])]
    if grupo.id not in ids:
        ids.append(grupo.id)
    aplicar_grupos(db, pessoa, ids)
    return pessoa


def desvincular_membro(db: Session, grupo: PermissaoGrupo, atendente_id: int) -> None:
    pessoa = _pessoa_do_grupo(db, grupo, atendente_id)
    ids = [item.id for item in (pessoa.grupos_permissao or []) if item.id != grupo.id]
    if len(ids) == len(pessoa.grupos_permissao or []):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Esta pessoa não está no grupo.")
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pessoa precisa permanecer em pelo menos um grupo.",
        )
    aplicar_grupos(db, pessoa, ids)


def aplicar_grupos(db: Session, atendente: Atendente, grupo_ids: list[int]) -> None:
    if atendente.role == "saas_ops":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este usuário não usa grupos da instância.")
    ids = []
    for bruto in grupo_ids:
        if bruto not in ids:
            ids.append(bruto)
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Escolha pelo menos um grupo de permissão.",
        )
    grupos = (
        db.query(PermissaoGrupo)
        .options(joinedload(PermissaoGrupo.itens))
        .filter(PermissaoGrupo.tenant_id == atendente.tenant_id, PermissaoGrupo.id.in_(ids))
        .all()
    )
    por_id = {g.id: g for g in grupos}
    if len(por_id) != len(ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grupo de permissão inválido.")
    atendente.grupos_permissao = [por_id[i] for i in ids]
    sincronizar_role(atendente)
    db.flush()
    garantir_admin_ativo(db, atendente.tenant_id)


def aplicar_role_legado(db: Session, atendente: Atendente, role: str) -> None:
    """Cliente antigo manda só o perfil: vira o grupo padrão correspondente."""
    ensure_sistema(db, atendente.tenant_id)
    slug = SLUG_POR_ROLE.get(role, "atendente")
    grupo = (
        db.query(PermissaoGrupo)
        .filter(
            PermissaoGrupo.tenant_id == atendente.tenant_id,
            PermissaoGrupo.slug == slug,
            PermissaoGrupo.sistema.is_(True),
        )
        .first()
    )
    if grupo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grupo padrão não encontrado.")
    aplicar_grupos(db, atendente, [grupo.id])
