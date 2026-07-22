"""Dados fictícios para testar o portal do cliente (RBAC, tickets, chats).

Uso (dev local):

    docker compose exec backend python -m app.seed_portal_demo

Reexecutar é seguro: atualiza cadastros e recria tickets/chats marcados como demo.
"""

from __future__ import annotations

from sqlalchemy import func

from app.core.security import hash_senha
from app.core.ticket_prioridade import PrioridadeTicket
from app.database import SessionLocal
from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa
from app.models.rede import Rede
from app.models.setor import Setor
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket, TicketMensagem
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem
from app.services.funcionario_escopo import sincronizar_vinculos_empresas
from app.services.protocolo_mensal import gerar_protocolo_chat, gerar_protocolo_ticket

DEMO_TAG = "[Demo]"
DEMO_PASSWORD = "portal123"
TENANT_ID = 1

DEMO_EMPRESAS = (
    ("Posto Centro Demo", "centro"),
    ("Posto Norte Alpha", "norte"),
    ("Posto Sul Beta", "sul"),
)

DEMO_FUNCIONARIOS = (
    # email, nome, tipo, slugs empresas (colaborador=1, supervisor=N)
    ("ana.socio@example.com", "Ana Duplex (sócia)", "socio", ()),
    ("carlos.supervisor@example.com", "Carlos Supervisor", "supervisor", ("centro", "norte")),
    ("maria.colab@example.com", "Maria Colaboradora", "colaborador", ("centro",)),
    ("joao.colab@example.com", "João Colaborador", "colaborador", ("norte",)),
    ("pedro.colab@example.com", "Pedro Colaborador", "colaborador", ("sul",)),
)

DEMO_TICKETS = (
    # email autor, slug empresa, assunto, descricao
    ("maria.colab@example.com", "centro", "PDV travou no abastecimento", "O caixa 01 congela ao finalizar venda."),
    ("maria.colab@example.com", "centro", "Impressora fiscal sem papel", "Troquei o rolo mas continua pedindo papel."),
    ("joao.colab@example.com", "norte", "Bomba 3 não conecta na retaguarda", "Sincronização de preços falha desde ontem."),
    ("pedro.colab@example.com", "sul", "Cartão recusando no caixa", "Só débito; crédito retorna erro genérico."),
)

DEMO_CHATS = (
    # email funcionário, slug empresa, wa_id, mensagens (direcao, corpo)
    (
        "maria.colab@example.com",
        "centro",
        "5511999000001",
        (
            ("inbound", "Bom dia, o PDV do caixa 1 travou de novo."),
            ("outbound", "Olá Maria, estamos verificando. Pode reiniciar o terminal?"),
            ("inbound", "Reiniciei, voltou a funcionar por enquanto."),
        ),
    ),
    (
        "joao.colab@example.com",
        "norte",
        "5511999000002",
        (
            ("inbound", "A bomba 3 não atualiza preço."),
            ("outbound", "João, vamos checar o link com a retaguarda."),
        ),
    ),
    (
        "pedro.colab@example.com",
        "sul",
        "5511999000003",
        (
            ("inbound", "Clientes reclamando de cartão recusado."),
            ("inbound", "Acontece só no caixa 2."),
        ),
    ),
)


def _slug_key(slug: str) -> str:
    return slug.strip().lower()


def _ensure_rede(db) -> Rede:
    rede = db.query(Rede).order_by(Rede.id.asc()).first()
    if not rede:
        rede = Rede(tenant_id=TENANT_ID, nome="Rede Duplex Demo", ativo=True)
        db.add(rede)
        db.flush()
    else:
        rede.nome = "Rede Duplex Demo"
        rede.ativo = True
    return rede


def _ensure_empresas(db, rede: Rede) -> dict[str, Empresa]:
    out: dict[str, Empresa] = {}
    for nome, slug in DEMO_EMPRESAS:
        emp = (
            db.query(Empresa)
            .filter(Empresa.rede_id == rede.id, func.lower(Empresa.nome) == nome.lower())
            .first()
        )
        if not emp:
            emp = Empresa(tenant_id=TENANT_ID, rede_id=rede.id, nome=nome, ativo=True)
            db.add(emp)
            db.flush()
        else:
            emp.ativo = True
        out[_slug_key(slug)] = emp
    return out


def _upsert_funcionario(
    db,
    *,
    rede: Rede,
    empresas: dict[str, Empresa],
    email: str,
    nome: str,
    tipo: str,
    empresa_slugs: tuple[str, ...],
) -> FuncionarioRede:
    email_norm = email.strip().lower()
    f = db.query(FuncionarioRede).filter(func.lower(FuncionarioRede.email) == email_norm).first()
    if not f:
        f = FuncionarioRede(email=email_norm, rede_id=rede.id)
        db.add(f)
    f.nome = nome
    f.tipo = tipo
    f.ativo = True
    f.escopo_empresas = "all" if tipo == "socio" else "selected"
    f.senha_hash = hash_senha(DEMO_PASSWORD)
    f.must_change_password = False
    f.token_version = int(getattr(f, "token_version", 0) or 0)
    f.notificar_email_portal = True

    empresa_ids: list[int] = []
    if tipo == "colaborador" and empresa_slugs:
        empresa_ids = [empresas[_slug_key(empresa_slugs[0])].id]
        f.empresa_id = empresa_ids[0]
    elif tipo == "supervisor":
        empresa_ids = [empresas[_slug_key(s)].id for s in empresa_slugs]
        f.empresa_id = None
    else:
        f.empresa_id = None

    db.flush()
    if tipo != "socio":
        sincronizar_vinculos_empresas(
            db,
            f,
            escopo="selected",
            rede_id=int(rede.id),
            empresa_ids=empresa_ids,
        )
    return f


def _clear_demo_tickets_chats(db) -> None:
    demo_ticket_ids = [
        t.id
        for t in db.query(Ticket).filter(Ticket.assunto.like(f"{DEMO_TAG}%")).all()
    ]
    if demo_ticket_ids:
        db.query(TicketMensagem).filter(TicketMensagem.ticket_id.in_(demo_ticket_ids)).delete(
            synchronize_session=False
        )
        db.query(Ticket).filter(Ticket.id.in_(demo_ticket_ids)).delete(synchronize_session=False)

    demo_wa_ids = [f"5511999{_i:06d}" for _i in range(1, 20)]
    demo_chat_ids = [
        c.id
        for c in db.query(WhatsappChat).filter(WhatsappChat.wa_id.in_(demo_wa_ids)).all()
    ]
    if demo_chat_ids:
        db.query(WhatsappMensagem).filter(WhatsappMensagem.chat_id.in_(demo_chat_ids)).delete(
            synchronize_session=False
        )
        db.query(WhatsappChat).filter(WhatsappChat.id.in_(demo_chat_ids)).delete(synchronize_session=False)


def _criar_ticket_demo(
    db,
    *,
    rede: Rede,
    empresa: Empresa,
    setor_id: int,
    status_id: int,
    autor: FuncionarioRede | None,
    assunto: str,
    descricao: str,
) -> Ticket:
    t = Ticket(
        tenant_id=TENANT_ID,
        protocolo=gerar_protocolo_ticket(db),
        empresa_id=empresa.id,
        rede_id=rede.id,
        setor_id=setor_id,
        status_id=status_id,
        aberto_por_id=autor.id if autor else None,
        prioridade=PrioridadeTicket.normal.value,
        assunto=f"{DEMO_TAG} {assunto}",
        descricao=descricao,
    )
    db.add(t)
    db.flush()
    db.add(
        TicketMensagem(
            ticket_id=t.id,
            tipo="abertura",
            corpo=descricao,
            atendente_id=None,
        )
    )
    if autor:
        db.add(
            TicketMensagem(
                ticket_id=t.id,
                tipo="publico",
                corpo="Recebemos seu chamado. A equipe já está analisando.",
                atendente_id=None,
            )
        )
    return t


def _criar_chat_demo(
    db,
    *,
    empresa: Empresa,
    funcionario: FuncionarioRede,
    setor_id: int,
    atendente_id: int | None,
    wa_id: str,
    mensagens: tuple[tuple[str, str], ...],
) -> WhatsappChat:
    chat = WhatsappChat(
        protocolo=gerar_protocolo_chat(db),
        wa_id=wa_id,
        cliente_nome=funcionario.nome,
        estado="em_atendimento",
        setor_id=setor_id,
        atendente_id=atendente_id,
        funcionario_rede_id=funcionario.id,
        empresa_id=empresa.id,
    )
    db.add(chat)
    db.flush()
    seq = 0
    for direcao, corpo in mensagens:
        seq += 1
        db.add(
            WhatsappMensagem(
                chat_id=chat.id,
                direcao=direcao,
                corpo=corpo,
                wa_message_id=f"demo-{wa_id}-{seq}",
                atendente_id=atendente_id if direcao == "outbound" else None,
                status_entrega="entregue" if direcao == "outbound" else None,
            )
        )
    # Comentário interno (não deve aparecer no portal)
    db.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="nota interna: cliente já reportou isso na semana passada",
            evento_sistema="comentario_interno",
            wa_message_id=f"demo-{wa_id}-interno",
            atendente_id=atendente_id,
        )
    )
    return chat


def run_seed_portal_demo() -> None:
    db = SessionLocal()
    try:
        rede = _ensure_rede(db)
        empresas = _ensure_empresas(db, rede)

        setor = db.query(Setor).filter(Setor.ativo.is_(True)).order_by(Setor.id.asc()).first()
        if not setor:
            raise RuntimeError("Nenhum setor ativo. Rode python -m app.seed antes.")
        status = (
            db.query(StatusTicket)
            .filter(StatusTicket.slug == "aguardando_atendimento", StatusTicket.ativo.is_(True))
            .first()
        )
        if not status:
            status = db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).first()
        if not status:
            raise RuntimeError("Nenhum status de ticket. Rode python -m app.seed antes.")

        atendente = db.query(Atendente).filter(Atendente.ativo.is_(True)).order_by(Atendente.id.asc()).first()

        funcionarios: dict[str, FuncionarioRede] = {}
        for email, nome, tipo, slugs in DEMO_FUNCIONARIOS:
            f = _upsert_funcionario(
                db,
                rede=rede,
                empresas=empresas,
                email=email,
                nome=nome,
                tipo=tipo,
                empresa_slugs=slugs,
            )
            funcionarios[email] = f

        _clear_demo_tickets_chats(db)

        for email, slug, assunto, descricao in DEMO_TICKETS:
            autor = funcionarios[email]
            _criar_ticket_demo(
                db,
                rede=rede,
                empresa=empresas[_slug_key(slug)],
                setor_id=setor.id,
                status_id=status.id,
                autor=autor,
                assunto=assunto,
                descricao=descricao,
            )

        # Ticket aberto pela equipe interna (sem autor portal) — só supervisor/sócio veem
        _criar_ticket_demo(
            db,
            rede=rede,
            empresa=empresas["centro"],
            setor_id=setor.id,
            status_id=status.id,
            autor=None,
            assunto="Manutenção programada no servidor",
            descricao="Chamado interno da equipe de suporte (não aparece para colaborador no portal).",
        )

        for email, slug, wa_id, mensagens in DEMO_CHATS:
            _criar_chat_demo(
                db,
                empresa=empresas[_slug_key(slug)],
                funcionario=funcionarios[email],
                setor_id=setor.id,
                atendente_id=atendente.id if atendente else None,
                wa_id=wa_id,
                mensagens=mensagens,
            )

        db.commit()

        print("\n=== Portal demo — dados fictícios criados ===\n")
        print(f"Rede: {rede.nome} (id={rede.id})")
        print("Empresas:")
        for slug, emp in empresas.items():
            print(f"  - {emp.nome} ({slug})")
        print(f"\nSenha de todos os usuários abaixo: {DEMO_PASSWORD}\n")
        print("| Papel        | E-mail                      | O que deve ver no portal |")
        print("|--------------|-----------------------------|---------------------------|")
        print("| Sócio        | ana.socio@example.com       | Toda a rede (tickets/chats) |")
        print("| Supervisor   | carlos.supervisor@example.com | Centro + Norte          |")
        print("| Colaborador  | maria.colab@example.com     | Só os próprios (Centro)   |")
        print("| Colaborador  | joao.colab@example.com      | Só os próprios (Norte)    |")
        print("| Colaborador  | pedro.colab@example.com     | Só os próprios (Sul)      |")
        print("\nTickets e chats marcados com prefixo «[Demo]» no assunto / protocolo WhatsApp.")
        print("Login: http://localhost:5173/portal/login\n")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed_portal_demo()
