from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from app.core.auth import exigir_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.models.email_settings import EmailSettings
from app.models.empresa_sistema import EmpresaSistema
from app.schemas.email_settings import EmailSettingsRead, EmailSettingsUpdate, EmailTestResult
from app.schemas.system_company import EmpresaSistemaRead, EmpresaSistemaUpdate
from app.services import email_probe
from app.services.secret_box import encrypt_str
from app.services.system_email_config import (
    get_singleton_email_settings,
    imap_runtime_from_row,
    smtp_runtime_from_row,
)
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
        logo_url=logo_url,
        ativo=bool(row.ativo),
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


def _email_out(row: EmailSettings | None) -> EmailSettingsRead:
    if not row:
        return EmailSettingsRead()
    return EmailSettingsRead(
        smtp_host=row.smtp_host,
        smtp_port=row.smtp_port,
        smtp_user=row.smtp_user,
        has_smtp_password=bool(row.smtp_password_enc and row.smtp_password_enc.strip()),
        smtp_use_starttls=bool(row.smtp_use_starttls),
        smtp_from_email=row.smtp_from_email,
        smtp_from_name=row.smtp_from_name,
        imap_host=row.imap_host,
        imap_port=row.imap_port,
        imap_user=row.imap_user,
        has_imap_password=bool(row.imap_password_enc and row.imap_password_enc.strip()),
        imap_use_ssl=bool(row.imap_use_ssl),
        imap_folder=row.imap_folder,
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

    for k in ("nome", "razao_social", "nome_fantasia", "email", "telefone", "endereco"):
        if k in payload:
            v = payload[k]
            setattr(row, k, (v.strip() if isinstance(v, str) else v) or None)
    if "ativo" in payload and payload["ativo"] is not None:
        row.ativo = bool(payload["ativo"])

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
    return _email_out(get_singleton_email_settings(db))


@router.put("/email", response_model=EmailSettingsRead)
def put_email_settings(
    data: EmailSettingsUpdate,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_or_create_email(db)
    payload = data.model_dump(exclude_unset=True)

    for k in (
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_use_starttls",
        "smtp_from_email",
        "smtp_from_name",
        "imap_host",
        "imap_port",
        "imap_user",
        "imap_use_ssl",
        "imap_folder",
    ):
        if k in payload:
            v = payload[k]
            if isinstance(v, str):
                v2 = v.strip()
                setattr(row, k, v2 or None)
            else:
                setattr(row, k, v)

    if "smtp_password" in payload:
        v = payload["smtp_password"]
        if v is None:
            pass
        elif str(v).strip() == "":
            row.smtp_password_enc = None
        else:
            row.smtp_password_enc = encrypt_str(str(v))

    if "imap_password" in payload:
        v = payload["imap_password"]
        if v is None:
            pass
        elif str(v).strip() == "":
            row.imap_password_enc = None
        else:
            row.imap_password_enc = encrypt_str(str(v))

    db.commit()
    db.refresh(row)
    return _email_out(row)


@router.post("/email/test-smtp", response_model=EmailTestResult)
def test_smtp(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = get_singleton_email_settings(db)
    cfg = smtp_runtime_from_row(row)
    if not cfg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Configurações de e-mail não definidas.")
    try:
        email_probe.testar_smtp(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            use_starttls=cfg.use_starttls,
        )
        return EmailTestResult(ok=True, detail="SMTP OK")
    except Exception as e:
        return EmailTestResult(ok=False, detail=str(e) or "Falha SMTP")


@router.post("/email/test-imap", response_model=EmailTestResult)
def test_imap(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = get_singleton_email_settings(db)
    cfg = imap_runtime_from_row(row)
    if not cfg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Configurações de e-mail não definidas.")
    try:
        email_probe.testar_imap(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            use_ssl=cfg.use_ssl,
            folder=cfg.folder,
        )
        return EmailTestResult(ok=True, detail="IMAP OK")
    except Exception as e:
        return EmailTestResult(ok=False, detail=str(e) or "Falha IMAP")

