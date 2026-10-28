"""Token de instalação do DeskRemote cliente e sync de senha (#1283)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings
from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.deskremote_enroll import DeskremoteDispositivo, DeskremoteInstallToken
from app.models.empresa import Empresa
from app.models.empresa_pdv import EmpresaPdv, EmpresaPdvAcessoRemoto
from app.services.empresa_pdv_acessos import (
    acessos_ordenados,
    garantir_filho_legado,
    sincronizar_colunas_pdv,
    tipo_permite_conectar,
)
from app.services.password_reset import _public_app_origin
from app.services.rustdesk_peers import garantir_tipo_rustdesk, marcar_visto_enroll, normalizar_id_remoto
from app.services.secret_box import decrypt_str

MSG_TOKEN_INVALIDO = "Este link de instalação não é válido ou já foi usado. Gere um novo no painel."
MSG_SEM_SENHA = "Cadastre a senha de acesso DeskRemote neste PDV antes de gerar o link."
MSG_SEM_ACESSO = "Cadastre um acesso DeskRemote neste PDV antes de gerar o link."
MSG_SERVIDOR = "O servidor de acesso remoto desta instância ainda não está configurado."
MSG_DISPOSITIVO = "Este computador não está vinculado. Instale de novo com um link novo."


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.strip().encode("utf-8")).hexdigest()


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def origem_api_publica() -> str:
    host = (settings.PUBLIC_API_HOST or "").strip()
    if host:
        host = host.removeprefix("https://").removeprefix("http://").split("/")[0]
        proto = "https" if settings.is_production else "http"
        return f"{proto}://{host}"
    app = (settings.CLIENT_APP_HOST or "").strip()
    app = app.removeprefix("https://").removeprefix("http://").split("/")[0]
    if app.endswith(".deskrudder.com.br") and not app.startswith("api-"):
        slug = app.split(".", 1)[0]
        proto = "https" if settings.is_production else "http"
        return f"{proto}://api-{slug}.deskrudder.com.br"
    if app:
        proto = "https" if settings.is_production else "http"
        return f"{proto}://{app}"
    if not settings.is_production:
        return "http://localhost:8000"
    return _public_app_origin()


def url_instalacao(raw_token: str) -> str:
    origin = _public_app_origin().rstrip("/")
    return f"{origin}/deskremote/instalar/{raw_token}"


def _carregar_pdv(db: Session, empresa_id: int, pdv_id: int) -> EmpresaPdv:
    row = (
        db.query(EmpresaPdv)
        .options(
            joinedload(EmpresaPdv.empresa).joinedload(Empresa.rede),
            joinedload(EmpresaPdv.rotulo),
            joinedload(EmpresaPdv.tipo_acesso_remoto),
            selectinload(EmpresaPdv.acessos_remotos).joinedload(EmpresaPdvAcessoRemoto.tipo_acesso_remoto),
        )
        .filter(EmpresaPdv.id == pdv_id, EmpresaPdv.empresa_id == empresa_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDV não encontrado")
    return row


def _rotulo_pdv(pdv: EmpresaPdv) -> str:
    rotulo = (pdv.rotulo.nome if pdv.rotulo else "") or "Equipamento"
    codigo = (pdv.codigo or "").strip()
    base = f"{rotulo} {codigo}".strip() if codigo else rotulo
    rede = ""
    if pdv.empresa and pdv.empresa.rede:
        rede = (pdv.empresa.rede.nome or "").strip()
    return f"{rede} · {base}" if rede else base


def _acesso_deskremote(pdv: EmpresaPdv, acesso_id: int | None) -> EmpresaPdvAcessoRemoto:
    rows = acessos_ordenados(pdv)
    if acesso_id is not None:
        alvo = next((a for a in rows if a.id == acesso_id), None)
        if not alvo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acesso remoto não encontrado")
        nome = alvo.tipo_acesso_remoto.nome if alvo.tipo_acesso_remoto else None
        if not tipo_permite_conectar(nome):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O link de instalação só vale para acesso DeskRemote.",
            )
        return alvo
    for acesso in rows:
        nome = acesso.tipo_acesso_remoto.nome if acesso.tipo_acesso_remoto else None
        if tipo_permite_conectar(nome):
            return acesso
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_SEM_ACESSO)


def _senha_do_acesso(acesso: EmpresaPdvAcessoRemoto) -> str:
    cifrada = (acesso.acesso_remoto_senha_cifrada or "").strip()
    if not cifrada:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_SEM_SENHA)
    try:
        senha = decrypt_str(cifrada)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível ler a senha cadastrada.",
        ) from exc
    if not senha.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_SEM_SENHA)
    return senha


def _servidor() -> dict:
    servidor_id = (settings.RUSTDESK_ID_SERVER or "").strip()
    relay = (settings.RUSTDESK_RELAY_SERVER or "").strip() or servidor_id
    chave = (settings.RUSTDESK_PUBLIC_KEY or "").strip()
    if not (servidor_id and chave):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=MSG_SERVIDOR)
    return {"servidor_id": servidor_id, "servidor_relay": relay, "chave": chave}


def _invalidar_tokens_abertos(db: Session, acesso_id: int) -> None:
    agora = _agora()
    abertos = (
        db.query(DeskremoteInstallToken)
        .filter(
            DeskremoteInstallToken.acesso_id == acesso_id,
            DeskremoteInstallToken.used_at.is_(None),
        )
        .all()
    )
    for row in abertos:
        if _aware(row.expires_at) > agora:
            row.used_at = agora


def gerar_token(
    db: Session,
    *,
    empresa_id: int,
    pdv_id: int,
    acesso_id: int | None,
    atendente: Atendente,
) -> dict:
    pdv = _carregar_pdv(db, empresa_id, pdv_id)
    garantir_filho_legado(db, pdv)
    acesso = _acesso_deskremote(pdv, acesso_id)
    _senha_do_acesso(acesso)
    _servidor()
    _invalidar_tokens_abertos(db, acesso.id)
    raw = secrets.token_urlsafe(24)
    horas = max(1, int(settings.DESKREMOTE_INSTALL_TOKEN_EXPIRE_HOURS or 72))
    row = DeskremoteInstallToken(
        pdv_id=pdv.id,
        acesso_id=acesso.id,
        token_hash=hash_token(raw),
        expires_at=_agora() + timedelta(hours=horas),
        created_by_id=atendente.id,
    )
    db.add(row)
    registrar_audit(
        db,
        "empresa_pdv",
        pdv.id,
        "deskremote_token",
        atendente.id,
        payload={"empresa_id": empresa_id, "acesso_id": acesso.id},
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "url": url_instalacao(raw),
        "expira_em": row.expires_at,
        "pdv_id": pdv.id,
        "acesso_id": acesso.id,
        "rotulo": _rotulo_pdv(pdv),
    }


def status_token(db: Session, empresa_id: int, pdv_id: int, token_id: int) -> dict:
    pdv = _carregar_pdv(db, empresa_id, pdv_id)
    row = (
        db.query(DeskremoteInstallToken)
        .filter(DeskremoteInstallToken.id == token_id, DeskremoteInstallToken.pdv_id == pdv.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link de instalação não encontrado")
    usado = row.used_at is not None
    expirado = (not usado) and _aware(row.expires_at) <= _agora()
    rustdesk_id = None
    if usado:
        disp = (
            db.query(DeskremoteDispositivo)
            .filter(
                DeskremoteDispositivo.acesso_id == row.acesso_id,
                DeskremoteDispositivo.revoked_at.is_(None),
            )
            .order_by(DeskremoteDispositivo.id.desc())
            .first()
        )
        if disp and disp.rustdesk_id:
            rustdesk_id = disp.rustdesk_id
    return {
        "id": row.id,
        "usado": usado,
        "vinculado": bool(rustdesk_id),
        "rustdesk_id": rustdesk_id,
        "expirado": expirado,
    }


def _token_aberto(db: Session, raw: str) -> DeskremoteInstallToken:
    digest = hash_token(raw)
    row = db.query(DeskremoteInstallToken).filter(DeskremoteInstallToken.token_hash == digest).first()
    if not row or row.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_TOKEN_INVALIDO)
    if _aware(row.expires_at) <= _agora():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_TOKEN_INVALIDO)
    return row


def _revogar_dispositivos(db: Session, acesso_id: int) -> None:
    agora = _agora()
    ativos = (
        db.query(DeskremoteDispositivo)
        .filter(
            DeskremoteDispositivo.acesso_id == acesso_id,
            DeskremoteDispositivo.revoked_at.is_(None),
        )
        .all()
    )
    for row in ativos:
        row.revoked_at = agora


def _gravar_id(db: Session, pdv: EmpresaPdv, acesso: EmpresaPdvAcessoRemoto, rustdesk_id: str) -> str:
    chave = normalizar_id_remoto(rustdesk_id)
    if not chave:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o ID do DeskRemote.")
    tipo = garantir_tipo_rustdesk(db)
    acesso.acesso_remoto_id = chave
    acesso.tipo_acesso_remoto_id = tipo.id
    sincronizar_colunas_pdv(pdv)
    return chave


def resgatar(db: Session, raw_token: str, rustdesk_id: str | None) -> dict:
    token = _token_aberto(db, raw_token)
    pdv = (
        db.query(EmpresaPdv)
        .options(
            joinedload(EmpresaPdv.empresa).joinedload(Empresa.rede),
            joinedload(EmpresaPdv.rotulo),
            selectinload(EmpresaPdv.acessos_remotos).joinedload(EmpresaPdvAcessoRemoto.tipo_acesso_remoto),
        )
        .filter(EmpresaPdv.id == token.pdv_id)
        .first()
    )
    acesso = db.query(EmpresaPdvAcessoRemoto).filter(EmpresaPdvAcessoRemoto.id == token.acesso_id).first()
    if not pdv or not acesso:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_TOKEN_INVALIDO)
    senha = _senha_do_acesso(acesso)
    servidor = _servidor()
    _revogar_dispositivos(db, acesso.id)
    device_raw = secrets.token_urlsafe(32)
    dispositivo = DeskremoteDispositivo(
        pdv_id=pdv.id,
        acesso_id=acesso.id,
        token_hash=hash_token(device_raw),
        senha_versao_aplicada=int(acesso.senha_versao or 1),
        last_seen_at=_agora(),
    )
    id_gravado = None
    if rustdesk_id and rustdesk_id.strip():
        id_gravado = _gravar_id(db, pdv, acesso, rustdesk_id)
        dispositivo.rustdesk_id = id_gravado
        marcar_visto_enroll(db, id_gravado, dispositivo.last_seen_at)
    db.add(dispositivo)
    token.used_at = _agora()
    registrar_audit(
        db,
        "empresa_pdv",
        pdv.id,
        "deskremote_enroll",
        None,
        payload={"acesso_id": acesso.id, "com_id": bool(id_gravado)},
    )
    db.commit()
    return {
        "dispositivo_token": device_raw,
        "senha": senha,
        "senha_versao": int(acesso.senha_versao or 1),
        "rustdesk_id": id_gravado,
        "rotulo": _rotulo_pdv(pdv),
        "pdv_id": pdv.id,
        "acesso_id": acesso.id,
        "servidor": servidor,
    }


def _dispositivo_ativo(db: Session, raw: str) -> DeskremoteDispositivo:
    digest = hash_token(raw)
    row = (
        db.query(DeskremoteDispositivo)
        .filter(
            DeskremoteDispositivo.token_hash == digest,
            DeskremoteDispositivo.revoked_at.is_(None),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_DISPOSITIVO)
    return row


def confirmar_id(db: Session, raw_device: str, rustdesk_id: str) -> dict:
    dispositivo = _dispositivo_ativo(db, raw_device)
    pdv = (
        db.query(EmpresaPdv)
        .options(
            joinedload(EmpresaPdv.empresa).joinedload(Empresa.rede),
            joinedload(EmpresaPdv.rotulo),
            selectinload(EmpresaPdv.acessos_remotos),
        )
        .filter(EmpresaPdv.id == dispositivo.pdv_id)
        .first()
    )
    acesso = db.query(EmpresaPdvAcessoRemoto).filter(EmpresaPdvAcessoRemoto.id == dispositivo.acesso_id).first()
    if not pdv or not acesso:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_DISPOSITIVO)
    chave = _gravar_id(db, pdv, acesso, rustdesk_id)
    dispositivo.rustdesk_id = chave
    dispositivo.last_seen_at = _agora()
    marcar_visto_enroll(db, chave, dispositivo.last_seen_at)
    registrar_audit(
        db,
        "empresa_pdv",
        pdv.id,
        "deskremote_id",
        None,
        payload={"acesso_id": acesso.id},
    )
    db.commit()
    return {"rustdesk_id": chave, "rotulo": _rotulo_pdv(pdv), "pdv_id": pdv.id}


def sync_config(db: Session, raw_device: str) -> dict:
    dispositivo = _dispositivo_ativo(db, raw_device)
    pdv = (
        db.query(EmpresaPdv)
        .options(
            joinedload(EmpresaPdv.empresa).joinedload(Empresa.rede),
            joinedload(EmpresaPdv.rotulo),
        )
        .filter(EmpresaPdv.id == dispositivo.pdv_id)
        .first()
    )
    acesso = db.query(EmpresaPdvAcessoRemoto).filter(EmpresaPdvAcessoRemoto.id == dispositivo.acesso_id).first()
    if not pdv or not acesso:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_DISPOSITIVO)
    servidor = _servidor()
    versao = int(acesso.senha_versao or 1)
    senha = None
    if versao != int(dispositivo.senha_versao_aplicada or 0):
        senha = _senha_do_acesso(acesso)
        dispositivo.senha_versao_aplicada = versao
        registrar_audit(
            db,
            "empresa_pdv",
            pdv.id,
            "deskremote_sync_senha",
            None,
            payload={"acesso_id": acesso.id, "senha_versao": versao},
        )
    dispositivo.last_seen_at = _agora()
    if dispositivo.rustdesk_id:
        marcar_visto_enroll(db, dispositivo.rustdesk_id, dispositivo.last_seen_at)
    db.commit()
    return {
        "senha_versao": versao,
        "senha": senha,
        "rotulo": _rotulo_pdv(pdv),
        "rustdesk_id": dispositivo.rustdesk_id,
        "servidor": servidor,
    }
