import { formatarDuracao } from '../lib/pontoFormat'
import type { Ponto } from '../api/client'
import { PontoMetricCard } from './PontoMetricCard'

export type MetricasMesPonto = {
  diasNoMes: number
  diasTrabalhados: number
  diasATrabalhar: number
  faltas: number
  segundosNecessarios: number
  segundosTrabalhados: number
  segundosATrabalhar: number
  saldoMesAnteriorSeg: number
  saldoMesSeg: number
  saldoAtualSeg: number
  segundosHePagos: number
  segundosCreditoBanco: number
  segundosDebitoBanco: number
}

/** Agrega calendário + bancos (mês atual e anterior) no modelo dx-ponto. */
export function calcularMetricasMes(
  calendario: Ponto.Calendario | null,
  bancoMes: Ponto.BancoHoras | null,
  bancoMesAnterior: Ponto.BancoHoras | null,
  hojeIsoStr: string,
): MetricasMesPonto {
  const dias = calendario?.dias ?? []
  const esperados = dias.filter((d) => d.esperado)
  const diasNoMes = esperados.length
  const diasTrabalhados = esperados.filter((d) => d.tem_entrada).length
  const diasATrabalhar = esperados.filter((d) => d.data >= hojeIsoStr && !d.tem_entrada).length
  // Dias esperados já excluem folga (banco)/férias — faltas = p/ desconto em folha
  const faltas = esperados.filter((d) => d.data < hojeIsoStr && !d.tem_entrada).length

  const segundosNecessarios =
    bancoMes?.segundos_esperados ??
    esperados.reduce((acc, d) => acc + (d.segundos_esperados ?? 0), 0)
  const segundosTrabalhados =
    bancoMes?.segundos_realizados ??
    dias.reduce((acc, d) => acc + (d.segundos_trabalhados ?? 0), 0)
  const segundosATrabalhar = Math.max(0, segundosNecessarios - segundosTrabalhados)

  const saldoMesSeg = bancoMes?.saldo_segundos ?? 0
  const saldoMesAnteriorSeg = bancoMesAnterior?.saldo_segundos ?? 0
  const saldoAtualSeg = saldoMesAnteriorSeg + saldoMesSeg
  const segundosHePagos = bancoMes?.segundos_he_pagos ?? 0
  const segundosCreditoBanco = bancoMes?.segundos_credito_banco ?? 0
  const segundosDebitoBanco = bancoMes?.segundos_debito_banco ?? 0

  return {
    diasNoMes,
    diasTrabalhados,
    diasATrabalhar,
    faltas,
    segundosNecessarios,
    segundosTrabalhados,
    segundosATrabalhar,
    saldoMesAnteriorSeg,
    saldoMesSeg,
    saldoAtualSeg,
    segundosHePagos,
    segundosCreditoBanco,
    segundosDebitoBanco,
  }
}

function rotuloSaldo(seg: number): string {
  if (seg === 0) return '0'
  const sinal = seg > 0 ? '+' : '−'
  return `${sinal}${formatarDuracao(Math.abs(seg))}`
}

export function PontoMetricasMes({
  metricas,
  loading,
}: {
  metricas: MetricasMesPonto | null
  loading?: boolean
}) {
  if (loading && !metricas) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="h-[5.25rem] animate-pulse rounded-xl border border-slate-200 bg-slate-100/80 dark:border-slate-800 dark:bg-slate-900/40"
          />
        ))}
      </div>
    )
  }
  if (!metricas) return null

  const m = metricas
  return (
    <div className="space-y-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Resumo do mês
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <PontoMetricCard
          tone="info"
          label="Dias esperados"
          value={String(m.diasNoMes)}
          hint="Na escala do mês"
        />
        <PontoMetricCard
          tone="info"
          label="Dias trabalhados"
          value={String(m.diasTrabalhados)}
          hint={`${m.diasATrabalhar} ainda a trabalhar`}
        />
        <PontoMetricCard
          tone={m.faltas > 0 ? 'warn' : 'info'}
          label="Faltas (p/ desconto)"
          value={String(m.faltas)}
          hint="Sem entrada e sem folga (banco)"
        />
        <PontoMetricCard
          tone="good"
          label="Horas necessárias"
          value={formatarDuracao(m.segundosNecessarios)}
          hint="Jornada prevista no mês"
        />
        <PontoMetricCard
          tone="good"
          label="Horas trabalhadas"
          value={formatarDuracao(m.segundosTrabalhados)}
          hint={`de ${formatarDuracao(m.segundosNecessarios)}`}
        />
        <PontoMetricCard
          tone="good"
          label="Horas a trabalhar"
          value={formatarDuracao(m.segundosATrabalhar)}
          hint="Restantes no mês"
        />
        <PontoMetricCard
          tone="warn"
          label="Saldo inicial"
          value={rotuloSaldo(m.saldoMesAnteriorSeg)}
          hint="Banco no início do mês"
        />
        <PontoMetricCard
          tone="good"
          label="Crédito no banco"
          value={m.segundosCreditoBanco > 0 ? `+${formatarDuracao(m.segundosCreditoBanco)}` : '0'}
          hint="Horas geradas no mês"
        />
        <PontoMetricCard
          tone={m.segundosDebitoBanco > 0 ? 'warn' : 'info'}
          label="Débito no banco"
          value={
            m.segundosDebitoBanco > 0 ? `−${formatarDuracao(m.segundosDebitoBanco)}` : '0'
          }
          hint="Parcial + folga (banco)"
        />
        <PontoMetricCard
          tone="warn"
          label="Saldo do mês"
          value={rotuloSaldo(m.saldoMesSeg)}
          hint="Crédito − débito"
        />
        {m.segundosHePagos > 0 ? (
          <PontoMetricCard
            tone="warn"
            label="HE a pagar"
            value={formatarDuracao(m.segundosHePagos)}
            hint={`Saldo atual ${rotuloSaldo(m.saldoAtualSeg)}`}
          />
        ) : (
          <PontoMetricCard
            tone="warn"
            label="Saldo atual"
            value={rotuloSaldo(m.saldoAtualSeg)}
            hint="Inicial + mês"
          />
        )}
      </div>
    </div>
  )
}
