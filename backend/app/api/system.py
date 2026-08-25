"""Informações de versão e release notes (#401)."""

from fastapi import APIRouter, Depends

from app.core.auth import obter_atendente_atual
from app.models.atendente import Atendente
from app.schemas.system import ReleaseNotesRead, SystemInfoRead
from app.services.system_release import release_notes_payload, system_info_payload

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info", response_model=SystemInfoRead)
def obter_system_info(_: Atendente = Depends(obter_atendente_atual)):
    return SystemInfoRead(**system_info_payload())


@router.get("/release-notes", response_model=ReleaseNotesRead)
def obter_release_notes(_: Atendente = Depends(obter_atendente_atual)):
    """Notas de produto no painel da instância — exclui bullets DevOps (#920)."""
    return ReleaseNotesRead(**release_notes_payload(product="deskrudder"))
