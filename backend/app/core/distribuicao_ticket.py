"""Enums e helpers de distribuição automática de tickets."""

from enum import Enum


class DistribuicaoModo(str, Enum):
    manual = "manual"
    auto_apos_timeout = "auto_apos_timeout"
    auto_imediato = "auto_imediato"


class DistribuicaoEstrategia(str, Enum):
    round_robin = "round_robin"
    menor_carga_abertos = "menor_carga_abertos"
    menor_carga_setor = "menor_carga_setor"
