"""Match de wa_id WhatsApp — variantes DDI / nono dígito BR e chat aberto."""

from __future__ import annotations

from app.services.whatsapp_contato_match import (
    canonical_wa_id_para_lock,
    variantes_wa_id,
)


def test_variantes_wa_id_ddi_e_nono_digito():
    v = variantes_wa_id("5511988776655")
    assert "5511988776655" in v
    assert "11988776655" in v
    assert "551188776655" in v
    assert "1188776655" in v

    v2 = variantes_wa_id("551188776655")
    assert "5511988776655" in v2
    assert "551188776655" in v2


def test_variantes_wa_id_sem_ddi():
    v = variantes_wa_id("11988776655")
    assert "5511988776655" in v
    assert "11988776655" in v


def test_canonical_lock_estavel_entre_variantes():
    a = canonical_wa_id_para_lock("11988776655")
    b = canonical_wa_id_para_lock("551188776655")
    c = canonical_wa_id_para_lock("5511988776655")
    assert a == b == c
