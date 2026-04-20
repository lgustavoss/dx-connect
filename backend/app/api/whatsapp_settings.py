from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.whatsapp_chat import WhatsappSettings
from app.schemas.whatsapp_settings import (
    WhatsappProvisionEmbutidoResponse,
    WhatsappSettingsRead,
    WhatsappSettingsUpdate,
    WhatsappTesteConexaoResultado,
)
from app.core.auth import exigir_admin
from app.models.atendente import Atendente
from app.services import evolution_api
from app.services import evolution_embedded

router = APIRouter(prefix="/settings/whatsapp", tags=["settings-whatsapp"])


def _read_out(row: WhatsappSettings | None) -> WhatsappSettingsRead:
    emb = settings.evolution_embutida_disponivel
    if not row:
        return WhatsappSettingsRead(
            evolution_base_url=None,
            evolution_instance_name=None,
            has_api_key=False,
            has_webhook_secret=False,
            evolution_embutida_disponivel=emb,
        )
    return WhatsappSettingsRead(
        evolution_base_url=row.evolution_base_url,
        evolution_instance_name=row.evolution_instance_name,
        has_api_key=bool(row.evolution_api_key and row.evolution_api_key.strip()),
        has_webhook_secret=bool(row.webhook_secret and row.webhook_secret.strip()),
        evolution_embutida_disponivel=emb,
    )


def _get_row(db: Session) -> WhatsappSettings | None:
    return db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()


def _get_or_create(db: Session) -> WhatsappSettings:
    row = _get_row(db)
    if row:
        return row
    row = WhatsappSettings()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=WhatsappSettingsRead)
def obter(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    return _read_out(_get_row(db))


@router.patch("", response_model=WhatsappSettingsRead)
def atualizar(
    data: WhatsappSettingsUpdate,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_or_create(db)
    payload = data.model_dump(exclude_unset=True)
    if "evolution_base_url" in payload:
        row.evolution_base_url = payload["evolution_base_url"]
    if "evolution_instance_name" in payload:
        row.evolution_instance_name = payload["evolution_instance_name"]
    if "evolution_api_key" in payload:
        v = payload["evolution_api_key"]
        if v is not None and v.strip():
            row.evolution_api_key = v.strip()
        elif v is not None:
            row.evolution_api_key = None
    if "webhook_secret" in payload:
        v = payload["webhook_secret"]
        if v is not None and v.strip():
            row.webhook_secret = v.strip()
        elif v is not None:
            row.webhook_secret = None
    db.commit()
    db.refresh(row)
    return _read_out(row)


@router.post("/testar-conexao", response_model=WhatsappTesteConexaoResultado)
def testar_conexao(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_row(db)
    if not row or not row.evolution_base_url or not row.evolution_instance_name or not row.evolution_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preencha URL base, nome da instância e API key antes de testar.",
        )
    ok, err = evolution_api.evolution_connection_state(
        row.evolution_base_url,
        row.evolution_instance_name,
        row.evolution_api_key,
    )
    return WhatsappTesteConexaoResultado(ok=ok, detalhe=err)


@router.post("/provisao-embutida", response_model=WhatsappProvisionEmbutidoResponse)
def provisionar_embutido(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_or_create(db)
    out = evolution_embedded.provisionar_e_ligar_webhook(db, row)
    return WhatsappProvisionEmbutidoResponse(**out)


@router.get("/qr-code")
def obter_qr_code(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
) -> dict[str, Any]:
    row = _get_or_create(db)
    return evolution_embedded.obter_qrcode(db, row)


@router.get("/estado-embutido")
def estado_embutido(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
) -> dict[str, Any]:
    row = _get_row(db)
    if not row:
        return {"configurado": False, "state": None}
    return evolution_embedded.estado_conexao(db, row)


@router.post("/repor-embutido", status_code=status.HTTP_204_NO_CONTENT)
def repor_embutido(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = _get_or_create(db)
    evolution_embedded.repor_instancia(db, row)
    return None
