"""Enums e tipos do motor de roteamento (#258)."""

from __future__ import annotations

import enum


class RoutingCampo(str, enum.Enum):
    email_from = "email_from"
    email_to = "email_to"
    assunto = "assunto"
    canal = "canal"


class RoutingOperador(str, enum.Enum):
    contains = "contains"
    equals = "equals"
    regex = "regex"


class RoutingCanal(str, enum.Enum):
    email = "email"
    manual = "manual"
