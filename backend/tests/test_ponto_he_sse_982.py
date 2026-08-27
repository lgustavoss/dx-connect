"""SSE ponto.he_atualizada (#982) — destinatários admin + colaborador."""

from unittest.mock import MagicMock, patch

from app.models.atendente import Atendente
from app.services.realtime_emit import emit_ponto_he_atualizada


def test_emit_ponto_he_atualizada_admins_e_colaborador():
    db = MagicMock()
    admin = Atendente(id=1, tenant_id=10, role="admin", ativo=True, nome="Admin", email="a@x")
    outro = Atendente(id=2, tenant_id=10, role="atendente", ativo=True, nome="X", email="x@x")
    db.query.return_value.filter.return_value.all.return_value = [admin]

    with (
        patch("app.services.realtime_emit._publish_to_atendentes") as pub,
        patch("app.services.realtime_emit.emit_notificacao_contagem") as cont,
    ):
        emit_ponto_he_atualizada(
            db,
            tenant_id=10,
            he_id=99,
            atendente_id=7,
            estado="pendente",
            origem="solicitacao",
        )
        pub.assert_called_once()
        ids, event, payload = pub.call_args[0]
        assert event == "ponto.he_atualizada"
        assert 1 in ids
        assert 7 in ids
        assert 2 not in ids
        assert payload["he_id"] == 99
        assert payload["estado"] == "pendente"
        cont.assert_called_once()
        _ = outro
