"""Limites de período de calendário do dashboard (#599)."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.ticket_dashboard_filters import (
    bounds_esta_semana,
    bounds_este_mes,
    bounds_for_preset,
    bounds_hoje,
    bounds_mes_passado,
    period_days_inclusive,
)


def test_bounds_hoje():
    assert bounds_hoje(date(2026, 7, 19)) == (date(2026, 7, 19), date(2026, 7, 19))


def test_bounds_esta_semana_meio_da_semana():
    # quarta 15/07/2026 → seg 13/07 até quarta 15/07
    assert bounds_esta_semana(date(2026, 7, 15)) == (date(2026, 7, 13), date(2026, 7, 15))


def test_bounds_esta_semana_domingo_completo():
    # domingo 19/07/2026 → seg 13/07 até dom 19/07
    assert bounds_esta_semana(date(2026, 7, 19)) == (date(2026, 7, 13), date(2026, 7, 19))


def test_bounds_esta_semana_segunda():
    assert bounds_esta_semana(date(2026, 7, 13)) == (date(2026, 7, 13), date(2026, 7, 13))


def test_bounds_este_mes():
    assert bounds_este_mes(date(2026, 7, 19)) == (date(2026, 7, 1), date(2026, 7, 19))


def test_bounds_mes_passado():
    assert bounds_mes_passado(date(2026, 7, 19)) == (date(2026, 6, 1), date(2026, 6, 30))


def test_bounds_mes_passado_em_janeiro():
    assert bounds_mes_passado(date(2026, 1, 5)) == (date(2025, 12, 1), date(2025, 12, 31))


def test_bounds_for_preset_aliases():
    ref = date(2026, 8, 2)
    assert bounds_for_preset("hoje", ref) == bounds_hoje(ref)
    assert bounds_for_preset("esta_semana", ref) == bounds_esta_semana(ref)
    assert bounds_for_preset("este_mes", ref) == bounds_este_mes(ref)
    assert bounds_for_preset("mes_passado", ref) == bounds_mes_passado(ref)


def test_bounds_for_preset_invalido():
    with pytest.raises(ValueError, match="preset"):
        bounds_for_preset("7dias")


def test_period_days_inclusive():
    assert period_days_inclusive(date(2026, 7, 1), date(2026, 7, 1)) == 1
    assert period_days_inclusive(date(2026, 7, 1), date(2026, 7, 7)) == 7
