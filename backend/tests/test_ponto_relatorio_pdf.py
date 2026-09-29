"""Testes do relatório mensal de ponto (agregação por dia e formatação)."""

from datetime import date, datetime, timezone

from app.schemas.ponto import PontoIntervaloRead
from app.services.ponto_relatorio import _fmt_duracao, _rotulo_folga, agregar_dias, nome_feriado_br


def _it(
    *,
    data: date,
    entrada: str,
    saida: str | None,
    trab: int | None,
    pausa: int = 0,
    aberto: bool = False,
    eid: int = 1,
) -> PontoIntervaloRead:
    def _dt(s: str) -> datetime:
        h, m = map(int, s.split(":"))
        return datetime(data.year, data.month, data.day, h, m, tzinfo=timezone.utc)

    return PontoIntervaloRead(
        data=data,
        entrada_em=_dt(entrada),
        saida_em=_dt(saida) if saida else None,
        duracao_segundos=trab,
        segundos_pausa=pausa,
        aberto=aberto,
        entrada_batida_id=eid,
        saida_batida_id=eid + 1 if saida else None,
    )


def test_fmt_duracao_horas_legivel():
    assert _fmt_duracao(235 * 60) == "3h55"
    assert _fmt_duracao(8 * 3600) == "8h00"
    assert _fmt_duracao(45 * 60) == "45 min"
    assert _fmt_duracao(None, vazio=True) == "—"
    assert _fmt_duracao(0) == "—"


def test_agregar_dia_soma_pausa_entre_turnos():
    """Duas jornadas no mesmo dia (saída 12:05 → entrada 13:05) = 1h de pausa."""
    d = date(2026, 9, 1)
    manha = _it(data=d, entrada="08:10", saida="12:05", trab=235 * 60, eid=1)
    tarde = _it(data=d, entrada="13:05", saida="17:05", trab=240 * 60, eid=3)
    dias = agregar_dias([("Administrador", manha), ("Administrador", tarde)])
    assert len(dias) == 1
    dia = dias[0]
    assert dia.data == d
    assert dia.entrada_em.hour == 8 and dia.entrada_em.minute == 10
    assert dia.saida_em is not None
    assert dia.saida_em.hour == 17 and dia.saida_em.minute == 5
    assert dia.segundos_trabalhados == (235 + 240) * 60
    assert dia.segundos_pausa == 60 * 60
    assert dia.aberto is False
    assert _fmt_duracao(dia.segundos_trabalhados) == "7h55"
    assert _fmt_duracao(dia.segundos_pausa) == "1h00"


def test_agregar_inclui_pausa_explicita_no_bloco():
    d = date(2026, 9, 2)
    it = _it(data=d, entrada="08:00", saida="17:00", trab=8 * 3600 - 30 * 60, pausa=30 * 60, eid=10)
    dias = agregar_dias([("Ana", it)])
    assert dias[0].segundos_pausa == 30 * 60


def test_rotulo_folga_fim_de_semana():
    assert _rotulo_folga(date(2026, 9, 5), com_ponto=False) == "Folga (sábado)"  # sábado
    assert _rotulo_folga(date(2026, 9, 6), com_ponto=False) == "Folga (domingo)"
    assert _rotulo_folga(date(2026, 9, 6), com_ponto=True) == "Folga (domingo) — com ponto"


def test_nome_feriado_independencia():
    assert nome_feriado_br(date(2026, 9, 7)) == "Independência do Brasil"
