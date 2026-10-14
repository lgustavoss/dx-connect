"""Referências de cadastro (UF, municípios, CEP) via serviços externos — sempre pelo servidor."""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import obter_atendente_atual, exigir_permissao
from app.database import get_db
from app.models.atendente import Atendente
from app.models.ibge_municipio import IbgeMunicipio
from app.services.ibge_client import ibge_get_json, public_json_get
from app.services.ibge_municipios_sync import (
    municipios_nomes_uf_direto_ibge,
    sync_ibge_municipios_full,
)

router = APIRouter(prefix="/cadastro-aux", tags=["cadastro-aux"])

logger = logging.getLogger(__name__)

_PUBLIC_JSON_TIMEOUT_S = 20.0


@router.get("/ufs")
def listar_ufs(_: Atendente = Depends(obter_atendente_atual)):
    """Lista estados brasileiros (IBGE), ordenados por nome."""
    try:
        data = ibge_get_json(
            "https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome",
            _PUBLIC_JSON_TIMEOUT_S,
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível carregar as UFs. Tente novamente.",
        )
    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resposta inválida do IBGE.",
        )
    out: list[dict] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        sigla = row.get("sigla")
        nome = row.get("nome")
        rid = row.get("id")
        if not sigla or not nome or rid is None:
            continue
        try:
            ibge_id = int(rid)
        except (TypeError, ValueError):
            continue
        out.append({"sigla": str(sigla).upper(), "nome": str(nome), "ibge_id": ibge_id})
    if not out:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resposta vazia do IBGE.",
        )
    return out


@router.get("/municipios")
def listar_municipios(
    uf: str = Query(..., min_length=2, max_length=2, description="Sigla da UF (2 letras)"),
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    """Nomes oficiais de municípios da UF — lidos do cache local (sincronizado com o IBGE)."""
    sigla = uf.strip().upper()
    if len(sigla) != 2 or not sigla.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UF inválida.",
        )

    # Evita COUNT(*) em toda requisição (lento e pode disputar lock com a sync em background).
    tem_cache = db.query(IbgeMunicipio).first() is not None
    if not tem_cache:
        try:
            nomes = municipios_nomes_uf_direto_ibge(sigla)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível carregar os municípios. Tente novamente em instantes.",
            )
        return {"uf": sigla, "nomes": nomes}

    rows = (
        db.query(IbgeMunicipio.nome)
        .filter(IbgeMunicipio.uf_sigla == sigla)
        .order_by(IbgeMunicipio.nome.asc())
        .all()
    )
    nomes = [r[0] for r in rows]
    return {"uf": sigla, "nomes": nomes}


@router.post("/municipios/sincronizar")
def sincronizar_municipios_ibge(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_permissao("instalacao.editar")),
):
    """Força recarga completa dos municípios a partir do IBGE (apenas administrador)."""
    try:
        n = sync_ibge_municipios_full(db)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Falha ao sincronizar municípios com o IBGE")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível sincronizar os municípios com o IBGE.",
        )
    return {"ok": True, "total": n}


@router.get("/cep/{cep}")
def consultar_cep(
    cep: str,
    _: Atendente = Depends(obter_atendente_atual),
):
    """Endereço a partir do CEP (ViaCEP)."""
    digits = re.sub(r"\D", "", cep or "")
    if len(digits) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CEP deve ter 8 dígitos.",
        )
    url = f"https://viacep.com.br/ws/{digits}/json/"
    try:
        data = public_json_get(url, _PUBLIC_JSON_TIMEOUT_S)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível consultar o CEP. Tente novamente.",
        )
    if not isinstance(data, dict) or data.get("erro"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CEP não encontrado.",
        )
    loc = data.get("localidade")
    uff = data.get("uf")
    if not loc or not uff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CEP não encontrado.",
        )
    return {
        "cep": f"{digits[:5]}-{digits[5:]}",
        "logradouro": data.get("logradouro") or "",
        "complemento": data.get("complemento") or "",
        "bairro": data.get("bairro") or "",
        "localidade": str(loc),
        "uf": str(uff).upper()[:2],
    }
