"""Guard de migrations: uma única cabeça (evita branch por numeração duplicada).

Duas PRs podem criar migrations com o mesmo número em ramos paralelos (foi o
que aconteceu entre `155_dispositivos_fcm` e `155_faturamento_anexos`). Sem
um merge revision o `alembic upgrade head` falha com "Multiple head revisions".
"""
from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BASE = Path(__file__).resolve().parents[1]


def _script_directory() -> ScriptDirectory:
    cfg = Config(str(BASE / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_alembic_tem_uma_unica_cabeca():
    heads = _script_directory().get_heads()
    assert len(heads) == 1, f"migrations com mais de uma cabeça: {heads}"
