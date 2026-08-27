"""Máquina de estados das solicitações (#953)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.solicitacao_melhoria_copy import (
    MSG_GITHUB_OBRIGATORIO,
    MSG_TRANSICAO_INVALIDA,
    STATUS_TRANSICOES,
    validar_transicao_status,
)


def test_grafo_completo_v1():
    assert STATUS_TRANSICOES["aberta"] == frozenset({"em_analise", "nao_sera_desenvolvida"})
    assert STATUS_TRANSICOES["em_analise"] == frozenset({"planejada", "nao_sera_desenvolvida"})
    assert STATUS_TRANSICOES["planejada"] == frozenset({"em_desenvolvimento", "nao_sera_desenvolvida"})
    assert STATUS_TRANSICOES["em_desenvolvimento"] == frozenset({"concluida", "nao_sera_desenvolvida"})
    assert STATUS_TRANSICOES["concluida"] == frozenset()
    assert STATUS_TRANSICOES["nao_sera_desenvolvida"] == frozenset()


@pytest.mark.parametrize(
    "de,para",
    [
        ("aberta", "planejada"),
        ("aberta", "em_desenvolvimento"),
        ("aberta", "concluida"),
        ("em_analise", "aberta"),
        ("em_analise", "em_desenvolvimento"),
        ("planejada", "aberta"),
        ("planejada", "em_analise"),
        ("concluida", "aberta"),
        ("nao_sera_desenvolvida", "em_analise"),
    ],
)
def test_saltos_ilegais(de, para):
    with pytest.raises(HTTPException) as ei:
        validar_transicao_status(de, para, tem_vinculo_github=True, motivo_nao_desenvolvimento="x")
    assert ei.value.status_code == 400
    assert MSG_TRANSICAO_INVALIDA in str(ei.value.detail)


def test_em_desenvolvimento_exige_github():
    with pytest.raises(HTTPException) as ei:
        validar_transicao_status("planejada", "em_desenvolvimento", tem_vinculo_github=False)
    assert ei.value.status_code == 400
    assert MSG_GITHUB_OBRIGATORIO in str(ei.value.detail)
    validar_transicao_status("planejada", "em_desenvolvimento", tem_vinculo_github=True)


def test_rejeicao_exige_motivo():
    with pytest.raises(HTTPException) as ei:
        validar_transicao_status("aberta", "nao_sera_desenvolvida", motivo_nao_desenvolvimento="  ")
    assert ei.value.status_code == 400
    validar_transicao_status("aberta", "nao_sera_desenvolvida", motivo_nao_desenvolvimento="Fora do escopo agora.")


def test_idempotente_mesmo_status():
    validar_transicao_status("em_analise", "em_analise")
