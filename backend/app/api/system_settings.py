from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from app.config import settings as app_settings
from app.core.auth import exigir_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.models.email_settings import EmailSettings
from app.models.empresa_sistema import EmpresaSistema
from app.schemas.email_settings import EmailSettingsRead, EmailSettingsUpdate, EmailTestResult, TicketEmailGraceOpcao
from app.services.ticket_email_grace_config import (
    grace_opcoes_dict,
    resolver_grace_seconds,
    validar_grace_seconds,
)
from app.schemas.system_company import EmpresaSistemaRead, EmpresaSistemaUpdate
from app.services.email_send_sistema import enviar_mensagem_texto_sistema
from app.services.secret_box import encrypt_str
from app.services.system_email_config import get_singleton_email_settings, transactional_config_from_row
from app.services.system_logo_storage import apagar_logo, caminho_absoluto_logo, gravar_logo_bytes

router = APIRouter(prefix="/settings", tags=["settings-system"])


def _get_company_row(db: Session) -> EmpresaSistema | None:
    return db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()


def _get_or_create_company(db: Session) -> EmpresaSistema:
    row = _get_company_row(db)
    if row:
        return row
    row = EmpresaSistema()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _company_out(row: EmpresaSistema | None) -> EmpresaSistemaRead:
    if not row:
        return EmpresaSistemaRead()
    logo_url = None
    if row.logo_filename and str(row.logo_filename).strip():
        logo_url = "/v1/settings/empresa-sistema/logo"
    return EmpresaSistemaRead(
        cnpj=row.cnpj,
        nome=row.nome,
        razao_social=row.razao_social,
        nome_fantasia=row.nome_fantasia,
        email=row.email,
        telefone=row.telefone,
        endereco=row.endereco,
        numero=row.numero,
        complemento=row.complemento,
        bairro=row.bairro,
        cidade=row.cidade,
        estado=row.estado,
        cep=row.cep,
        logo_url=logo_url,
    )


def _get_or_create_email(db: Session) -> EmailSettings:
    row = get_singleton_email_settings(db)
    if row:
        return row
    row = EmailSettings()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _email_out(row: EmailSettings | None, db: Session) -> EmailSettingsRead:
    cfg = transactional_config_from_row(row)
    from_email = cfg.from_email if cfg else None
    from_name = cfg.from_name if cfg else None
    if not from_email and row and (row.transactional_from_email or "").strip():
        from_email = str(row.transactional_from_email).strip()
    if not from_name and row and (row.transactional_from_name or "").strip():
        from_name = str(row.transactional_from_name).strip()
    reply_to = cfg.reply_to if cfg else None
    if not reply_to:
        reply_to = (app_settings.SUPPORT_REPLY_TO_EMAIL or "").strip() or None

    return EmailSettingsRead(
        transactional_from_email=from_email,
        transactional_from_name=from_name,
        transactional_reply_to_email=reply_to,
        outbound_configured=bool(cfg),
        has_transactional_api_key=bool(row and row.transactional_api_key_enc and str(row.transactional_api_key_enc).strip()),
        ticket_mensagem_email_grace_seconds=resolver_grace_seconds(db),
        opcoes_ticket_mensagem_email_grace=[TicketEmailGraceOpcao(**o) for o in grace_opcoes_dict()],
    )


@router.get("/empresa-sistema", response_model=EmpresaSistemaRead)
def get_empresa_sistema(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    return _company_out(_get_company_row(db))


@router.put("/empresa-sistema", response_model=EmpresaSistemaRead)
def put_empresa_sistema(
    data: EmpresaSistemaUpdate,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_or_create_company(db)
    payload = data.model_dump(exclude_unset=True)

    if "cnpj" in payload:
        incoming = payload["cnpj"]
        if row.cnpj and str(row.cnpj).strip():
            # CNPJ imutável após a primeira gravação.
            if incoming is not None and str(incoming).strip() and str(incoming).strip() != str(row.cnpj).strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CNPJ não pode ser alterado.")
        else:
            row.cnpj = (incoming or None) if incoming is None else (str(incoming).strip() or None)

    for k in (
        "nome",
        "razao_social",
        "nome_fantasia",
        "email",
        "telefone",
        "endereco",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "cep",
    ):
        if k in payload:
            v = payload[k]
            setattr(row, k, (v.strip() if isinstance(v, str) else v) or None)
    if "estado" in payload:
        v = payload["estado"]
        if v is None:
            row.estado = None
        elif isinstance(v, str):
            u = v.strip().upper()[:2]
            row.estado = u or None
        else:
            row.estado = None

    db.commit()
    db.refresh(row)
    return _company_out(row)


@router.get("/empresa-sistema/logo")
def get_empresa_sistema_logo(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_company_row(db)
    if not row or not row.logo_filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo não definido.")
    p = caminho_absoluto_logo(row.logo_filename)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo não encontrado.")
    mt = (row.logo_mimetype or "").strip() or "application/octet-stream"
    return FileResponse(
        path=str(p),
        media_type=mt,
        filename=p.name,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/empresa-sistema/logo", response_model=EmpresaSistemaRead)
async def post_empresa_sistema_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_or_create_company(db)
    data = await file.read()
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower() or None
    if not content_type or not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envie um arquivo de imagem (PNG/JPG/WEBP).")
    saved = gravar_logo_bytes(data, content_type)
    if not saved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logo inválido (tipo ou tamanho).")
    new_name, new_mt = saved

    # remove anterior (best-effort)
    apagar_logo(row.logo_filename)
    row.logo_filename = new_name
    row.logo_mimetype = new_mt
    db.commit()
    db.refresh(row)
    return _company_out(row)


@router.delete("/empresa-sistema/logo", response_model=EmpresaSistemaRead)
def delete_empresa_sistema_logo(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_or_create_company(db)
    apagar_logo(row.logo_filename)
    row.logo_filename = None
    row.logo_mimetype = None
    db.commit()
    db.refresh(row)
    return _company_out(row)


@router.get("/email", response_model=EmailSettingsRead)
def get_email_settings(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    return _email_out(get_singleton_email_settings(db), db)


@router.put("/email", response_model=EmailSettingsRead)
def put_email_settings(
    data: EmailSettingsUpdate,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_or_create_email(db)
    payload = data.model_dump(exclude_unset=True)

    for k in ("transactional_from_email", "transactional_from_name"):
        if k in payload:
            v = payload[k]
            if v is None:
                setattr(row, k, None)
            else:
                s = str(v).strip()
                setattr(row, k, s or None)

    if "transactional_api_key" in payload:
        v = payload["transactional_api_key"]
        if v is None:
            pass
        elif str(v).strip() == "":
            row.transactional_api_key_enc = None
        else:
            row.transactional_api_key_enc = encrypt_str(str(v))

    if "ticket_mensagem_email_grace_seconds" in payload:
        v = payload["ticket_mensagem_email_grace_seconds"]
        if v is None:
            row.ticket_mensagem_email_grace_seconds = None
        else:
            try:
                row.ticket_mensagem_email_grace_seconds = validar_grace_seconds(int(v))
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    db.commit()
    db.refresh(row)
    return _email_out(row, db)


@router.post("/email/test-transactional", response_model=EmailTestResult)
def test_transactional_email(
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    dest = (admin.email or "").strip()
    if not dest:
        return EmailTestResult(ok=False, detail="E-mail do administrador em sessão inválido.")
    try:
        enviar_mensagem_texto_sistema(
            db,
            to_addr=dest,
            subject="DX Connect — teste de envio",
            body="Se recebeu esta mensagem, o envio transaccional da plataforma está configurado.",
        )
        return EmailTestResult(ok=True, detail="E-mail de teste enviado.")
    except ValueError as e:
        return EmailTestResult(ok=False, detail=str(e))
    except Exception as e:
        return EmailTestResult(ok=False, detail=str(e)[:500])

