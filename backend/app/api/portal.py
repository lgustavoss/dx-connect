"""API do portal do cliente — funcionários da rede (#263 / #300–#303)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.kb_public_rate_limit import check_kb_public_rate_limit
from app.core.login_protection import check_login_rate_limit, delay_on_auth_failure
from app.core.portal_auth import claims_portal, exigir_socio_portal, obter_funcionario_portal
from app.core.portal_scope import assert_empresa_no_escopo, empresa_ids_visiveis, tenant_id_do_funcionario
from app.core.security import (
    criar_access_token,
    criar_refresh_token,
    decodificar_refresh_token,
    hash_senha,
    verificar_senha,
)
from app.core.tenant_context import (
    TenantIdDep,
    assert_token_tenant_matches_request,
    resolve_tenant_id,
)
from app.database import get_db
from app.models.empresa import Empresa
from app.models.empresa_pdv import EmpresaPdv
from app.models.funcionario_rede import FuncionarioRede
from app.models.setor import Setor
from app.models.ticket_anexo import TicketAnexo
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.portal import (
    PortalAnexoRead,
    PortalEmpresaRead,
    PortalLogin,
    PortalMe,
    PortalMensagemRead,
    PortalPdvRead,
    PortalPreferenciasUpdate,
    PortalRefreshRequest,
    PortalSetorRead,
    PortalTicketCreate,
    PortalTicketDetail,
    PortalTicketListItem,
    PortalTicketMensagemCreate,
    PortalToken,
    PortalTrocarSenha,
    PortalWhatsappChatDetail,
    PortalWhatsappChatListItem,
    PortalWhatsappMensagemRead,
    PortalEquipeFuncionarioCreate,
    PortalEquipeFuncionarioRead,
    PortalEquipeFuncionarioUpdate,
    PortalPublicBrandingRead,
)
from app.services import portal_tickets as portal_svc
from app.services import portal_whatsapp as portal_wpp_svc
from app.services import portal_equipe as portal_equipe_svc
from app.services.instancia_branding import branding_portal_cliente
from app.services import ticket_anexo_storage
from app.services.funcionario_escopo import rede_id_efetiva
from app.services.ticket_csat import criar_convite_csat
from app.services.whatsapp_media_storage import caminho_absoluto_arquivo

router = APIRouter(prefix="/portal", tags=["portal-cliente"])

_MAX_PAGE = 50
_DEFAULT_PAGE = 20


def _buscar_funcionario_login(db: Session, email: str) -> FuncionarioRede | None:
    return (
        db.query(FuncionarioRede)
        .filter(
            func.lower(FuncionarioRede.email) == email,
            FuncionarioRede.ativo.is_(True),
        )
        .first()
    )


def _emitir_tokens(db: Session, funcionario: FuncionarioRede) -> PortalToken:
    tid = tenant_id_do_funcionario(db, funcionario)
    claims = claims_portal(funcionario, tenant_id=tid)
    return PortalToken(
        access_token=criar_access_token(data=claims),
        refresh_token=criar_refresh_token(data=claims),
        must_change_password=bool(getattr(funcionario, "must_change_password", False)),
    )


def _me_read(db: Session, funcionario: FuncionarioRede) -> PortalMe:
    ids = sorted(empresa_ids_visiveis(db, funcionario))
    empresas: list[PortalEmpresaRead] = []
    if ids:
        rows = db.query(Empresa).filter(Empresa.id.in_(ids)).order_by(Empresa.nome.asc()).all()
        empresas = [
            PortalEmpresaRead(id=e.id, nome=e.nome, rede_id=int(e.rede_id)) for e in rows
        ]
    return PortalMe(
        id=funcionario.id,
        nome=funcionario.nome,
        email=str(funcionario.email or ""),
        tipo=funcionario.tipo,
        rede_id=rede_id_efetiva(db, funcionario),
        empresas=empresas,
        must_change_password=bool(getattr(funcionario, "must_change_password", False)),
        notificar_email_portal=bool(getattr(funcionario, "notificar_email_portal", True)),
    )


@router.post("/auth/login", response_model=PortalToken)
async def portal_login(request: Request, data: PortalLogin, db: Session = Depends(get_db)):
    check_login_rate_limit(request)
    email = data.email.strip().lower()
    resolve_tenant_id(request)  # valida host multi-tenant
    funcionario = _buscar_funcionario_login(db, email)
    if not funcionario or not (funcionario.senha_hash or "").strip():
        await delay_on_auth_failure()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos")
    if not verificar_senha(data.senha, funcionario.senha_hash):
        await delay_on_auth_failure()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos")
    if not funcionario.ativo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta inativa")
    return _emitir_tokens(db, funcionario)


@router.post("/auth/refresh", response_model=PortalToken)
async def portal_refresh(
    request: Request,
    data: PortalRefreshRequest,
    db: Session = Depends(get_db),
):
    payload = decodificar_refresh_token(data.refresh_token)
    if not payload or "sub" not in payload or payload.get("aud") != "portal":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido ou expirado")
    email = str(payload["sub"]).strip().lower()
    token_tid = payload.get("tid")
    assert_token_tenant_matches_request(request, token_tid)
    funcionario = _buscar_funcionario_login(db, email)
    if not funcionario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado ou inativo")
    fid = payload.get("fid")
    if fid is not None and int(fid) != int(funcionario.id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado ou inativo")
    token_ver = int(payload.get("ver") or 0)
    atual_ver = int(getattr(funcionario, "token_version", 0) or 0)
    if token_ver != atual_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada. Faça login novamente.",
        )
    return _emitir_tokens(db, funcionario)


@router.get("/me", response_model=PortalMe)
def portal_me(
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    return _me_read(db, funcionario)


@router.post("/me/trocar-senha", response_model=PortalToken)
def portal_trocar_senha(
    data: PortalTrocarSenha,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    if not verificar_senha(data.senha_atual, funcionario.senha_hash or ""):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")
    if len(data.senha_nova.strip()) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A nova senha deve ter ao menos 8 caracteres")
    if verificar_senha(data.senha_nova, funcionario.senha_hash or ""):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A nova senha deve ser diferente da atual")
    funcionario.senha_hash = hash_senha(data.senha_nova.strip())
    funcionario.must_change_password = False
    funcionario.token_version = int(getattr(funcionario, "token_version", 0) or 0) + 1
    db.commit()
    db.refresh(funcionario)
    return _emitir_tokens(db, funcionario)


@router.patch("/me/preferencias", response_model=PortalMe)
def portal_preferencias(
    data: PortalPreferenciasUpdate,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    if data.notificar_email_portal is not None:
        funcionario.notificar_email_portal = bool(data.notificar_email_portal)
        db.commit()
        db.refresh(funcionario)
    return _me_read(db, funcionario)


@router.get("/catalogos/setores", response_model=list[PortalSetorRead])
def portal_setores(
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    tid = tenant_id_do_funcionario(db, funcionario)
    rows = (
        db.query(Setor)
        .filter(Setor.tenant_id == tid, Setor.ativo.is_(True))
        .order_by(Setor.nome.asc())
        .all()
    )
    return [PortalSetorRead(id=s.id, nome=s.nome, slug=s.slug) for s in rows]


@router.get("/empresas/{empresa_id}/pdvs", response_model=list[PortalPdvRead])
def portal_pdvs_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        assert_empresa_no_escopo(db, funcionario, empresa_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    rows = (
        db.query(EmpresaPdv)
        .filter(EmpresaPdv.empresa_id == empresa_id, EmpresaPdv.ativo.is_(True))
        .order_by(EmpresaPdv.codigo.asc())
        .all()
    )
    return [
        PortalPdvRead(id=p.id, codigo=p.codigo, papel=getattr(p, "papel", None), ativo=bool(p.ativo))
        for p in rows
    ]


@router.get("/tickets", response_model=ListaPaginada[PortalTicketListItem])
def portal_listar_tickets(
    situacao: str = Query("abertos", description="abertos | fechados | todos"),
    busca: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    rows, total = portal_svc.listar_tickets(
        db,
        funcionario,
        situacao=situacao,
        busca=busca,
        offset=offset,
        limit=limit,
    )
    return ListaPaginada(items=[portal_svc.ticket_para_list_item(t) for t in rows], total=total)


@router.post("/tickets", response_model=PortalTicketDetail, status_code=201)
def portal_criar_ticket(
    data: PortalTicketCreate,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        ticket = portal_svc.criar_ticket(db, funcionario, data)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return portal_svc.ticket_para_detail(db, ticket)


@router.get("/tickets/{ticket_id}", response_model=PortalTicketDetail)
def portal_obter_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        ticket = portal_svc.obter_ticket_escopo(db, funcionario, ticket_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return portal_svc.ticket_para_detail(db, ticket)


@router.get("/tickets/{ticket_id}/mensagens", response_model=list[PortalMensagemRead])
def portal_listar_mensagens(
    ticket_id: int,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        ticket = portal_svc.obter_ticket_escopo(db, funcionario, ticket_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return portal_svc.listar_mensagens_publicas(db, funcionario, ticket)


@router.post("/tickets/{ticket_id}/mensagens", response_model=PortalMensagemRead, status_code=201)
def portal_criar_mensagem(
    ticket_id: int,
    data: PortalTicketMensagemCreate,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        ticket = portal_svc.obter_ticket_escopo(db, funcionario, ticket_id)
        m = portal_svc.criar_mensagem_portal(db, funcionario, ticket, data.corpo)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return portal_svc.mensagem_para_read(db, funcionario, m)


@router.get("/tickets/{ticket_id}/anexos", response_model=list[PortalAnexoRead])
def portal_listar_anexos(
    ticket_id: int,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        ticket = portal_svc.obter_ticket_escopo(db, funcionario, ticket_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return portal_svc.listar_anexos_publicos(db, ticket)


@router.post("/tickets/{ticket_id}/anexos", response_model=PortalAnexoRead, status_code=201)
async def portal_upload_anexo(
    ticket_id: int,
    file: UploadFile = File(...),
    mensagem_id: int | None = Form(None),
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        ticket = portal_svc.obter_ticket_escopo(db, funcionario, ticket_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    if ticket.fechado_em is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chamado encerrado. Abra um novo chamado para enviar anexos.",
        )
    raw = await file.read()
    try:
        nome_original, mime = ticket_anexo_storage.validar_upload(file.filename, file.content_type, len(raw))
        storage_key = ticket_anexo_storage.gravar_bytes_em_disco(raw, mimetype=mime, nome_original=nome_original)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except OSError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao gravar arquivo") from e

    msg_id = None
    if mensagem_id is not None:
        from app.models.ticket import TicketMensagem

        msg = (
            db.query(TicketMensagem)
            .filter(
                TicketMensagem.id == mensagem_id,
                TicketMensagem.ticket_id == ticket.id,
                TicketMensagem.tipo.in_(list(portal_svc.TIPOS_PUBLICOS_PORTAL)),
            )
            .first()
        )
        if not msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem não encontrada")
        msg_id = msg.id

    a = TicketAnexo(
        ticket_id=ticket.id,
        mensagem_id=msg_id,
        atendente_id=None,
        visibilidade="publico",
        nome_original=nome_original,
        content_type=mime,
        tamanho_bytes=len(raw),
        storage_key=storage_key,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return PortalAnexoRead(
        id=a.id,
        nome_original=a.nome_original,
        content_type=a.content_type,
        tamanho_bytes=int(a.tamanho_bytes or 0),
        mensagem_id=a.mensagem_id,
        created_at=a.created_at,
        download_url=f"/v1/portal/tickets/{ticket.id}/anexos/{a.id}/download",
    )


@router.get("/tickets/{ticket_id}/anexos/{anexo_id}/download")
def portal_download_anexo(
    ticket_id: int,
    anexo_id: int,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        ticket = portal_svc.obter_ticket_escopo(db, funcionario, ticket_id)
        a = portal_svc.obter_anexo_publico(db, ticket, anexo_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    path = ticket_anexo_storage.caminho_absoluto_arquivo(a.storage_key)
    if path is None or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado no armazenamento")
    return FileResponse(
        path=str(path),
        filename=a.nome_original,
        media_type=a.content_type or "application/octet-stream",
    )


@router.get("/chats", response_model=ListaPaginada[PortalWhatsappChatListItem])
def portal_listar_chats(
    situacao: str = Query("abertos", description="abertos | encerrados | todos"),
    busca: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    rows, total = portal_wpp_svc.listar_chats(
        db,
        funcionario,
        situacao=situacao,
        busca=busca,
        offset=offset,
        limit=limit,
    )
    return ListaPaginada(
        items=[portal_wpp_svc.chat_para_list_item(db, c) for c in rows],
        total=total,
    )


@router.get("/chats/{chat_id}", response_model=PortalWhatsappChatDetail)
def portal_obter_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        chat = portal_wpp_svc.obter_chat_escopo(db, funcionario, chat_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return portal_wpp_svc.chat_para_detail(db, chat)


@router.get("/chats/{chat_id}/mensagens", response_model=list[PortalWhatsappMensagemRead])
def portal_listar_mensagens_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        chat = portal_wpp_svc.obter_chat_escopo(db, funcionario, chat_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return portal_wpp_svc.listar_mensagens_visiveis(db, chat)


@router.get("/chats/{chat_id}/mensagens/{mensagem_id}/midia")
def portal_download_midia_chat(
    chat_id: int,
    mensagem_id: int,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        chat = portal_wpp_svc.obter_chat_escopo(db, funcionario, chat_id)
        m = portal_wpp_svc.obter_mensagem_midia(db, chat, mensagem_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    path = caminho_absoluto_arquivo(m.midia_nome_arquivo)
    if path is None or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficheiro não encontrado")
    media_type = m.mimetype or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/equipe/funcionarios", response_model=ListaPaginada[PortalEquipeFuncionarioRead])
def portal_equipe_listar(
    incluir_inativos: bool = Query(False),
    busca: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    socio: FuncionarioRede = Depends(exigir_socio_portal),
):
    rows, total = portal_equipe_svc.listar_funcionarios(
        db,
        socio,
        incluir_inativos=incluir_inativos,
        busca=busca,
        offset=offset,
        limit=limit,
    )
    return ListaPaginada(
        items=[portal_equipe_svc._para_read(f, socio_id=socio.id) for f in rows],
        total=total,
    )


@router.get("/equipe/empresas", response_model=list[PortalEmpresaRead])
def portal_equipe_empresas(
    db: Session = Depends(get_db),
    socio: FuncionarioRede = Depends(exigir_socio_portal),
):
    rows = portal_equipe_svc.empresas_da_rede(db, socio)
    return [PortalEmpresaRead(id=e.id, nome=e.nome, rede_id=int(e.rede_id)) for e in rows]


@router.get("/equipe/funcionarios/{funcionario_id}", response_model=PortalEquipeFuncionarioRead)
def portal_equipe_obter(
    funcionario_id: int,
    db: Session = Depends(get_db),
    socio: FuncionarioRede = Depends(exigir_socio_portal),
):
    try:
        f = portal_equipe_svc._obter_na_rede(db, socio, funcionario_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return portal_equipe_svc._para_read(f, socio_id=socio.id)


@router.post("/equipe/funcionarios", response_model=PortalEquipeFuncionarioRead, status_code=201)
def portal_equipe_criar(
    data: PortalEquipeFuncionarioCreate,
    db: Session = Depends(get_db),
    socio: FuncionarioRede = Depends(exigir_socio_portal),
):
    f = portal_equipe_svc.criar_funcionario(db, socio, data)
    return portal_equipe_svc._para_read(f, socio_id=socio.id)


@router.patch("/equipe/funcionarios/{funcionario_id}", response_model=PortalEquipeFuncionarioRead)
def portal_equipe_atualizar(
    funcionario_id: int,
    data: PortalEquipeFuncionarioUpdate,
    db: Session = Depends(get_db),
    socio: FuncionarioRede = Depends(exigir_socio_portal),
):
    try:
        f = portal_equipe_svc.atualizar_funcionario(db, socio, funcionario_id, data)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return portal_equipe_svc._para_read(f, socio_id=socio.id)


@router.post("/tickets/{ticket_id}/csat-link")
def portal_csat_link(
    ticket_id: int,
    db: Session = Depends(get_db),
    funcionario: FuncionarioRede = Depends(obter_funcionario_portal),
):
    try:
        ticket = portal_svc.obter_ticket_escopo(db, funcionario, ticket_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    if ticket.fechado_em is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avaliação disponível após o encerramento.")
    result = criar_convite_csat(db, ticket.id, enviar_email=False, exigir_email_cliente=False)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avaliação já registrada ou indisponível.")
    return {"link": result["link"], "expires_at": result["expires_at"]}


def _public_cache_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "public, max-age=60"


@router.get("/public/branding", response_model=PortalPublicBrandingRead)
def portal_public_branding(
    request: Request,
    response: Response,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    _ = tenant_id
    out = branding_portal_cliente(db, tenant_id)
    _public_cache_headers(response)
    return out
