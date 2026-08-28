import { useMemo } from 'react'
import type { Ponto } from '../api/client'
import { Button } from './ui/Button'

const DIAS_SEMANA = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

function formatarDuracao(segundos: number | null | undefined): string {
  if (segundos == null || segundos < 0) return '—'
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  if (h <= 0) return `${m} min`
  return `${h}h${m > 0 ? String(m).padStart(2, '0') : ''}`
}

function formatarDuracaoLonga(segundos: number | null | undefined): string {
  if (segundos == null || segundos < 0) return '—'
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  if (h <= 0) return `${m} min`
  return `${h} h ${String(m).padStart(2, '0')} min`
}

function classeCss(classe: Ponto.ClasseVisualDia | undefined): string {
  switch (classe) {
    case 'abaixo':
      return 'bg-red-100/90 text-red-900 ring-red-200/80 hover:bg-red-200/90 dark:bg-red-950/45 dark:text-red-100 dark:ring-red-900 dark:hover:bg-red-950/70'
    case 'ok':
      return 'bg-emerald-100/90 text-emerald-900 ring-emerald-200/80 hover:bg-emerald-200/90 dark:bg-emerald-950/45 dark:text-emerald-100 dark:ring-emerald-900 dark:hover:bg-emerald-950/70'
    case 'he':
      return 'bg-sky-100/90 text-sky-900 ring-sky-200/80 hover:bg-sky-200/90 dark:bg-sky-950/45 dark:text-sky-100 dark:ring-sky-900 dark:hover:bg-sky-950/70'
    case 'feriado':
      return 'bg-orange-100/90 text-orange-900 ring-orange-200/80 hover:bg-orange-200/90 dark:bg-orange-950/45 dark:text-orange-100 dark:ring-orange-900 dark:hover:bg-orange-950/70'
    case 'ausencia':
      return 'bg-violet-100/90 text-violet-900 ring-violet-200/80 hover:bg-violet-200/90 dark:bg-violet-950/45 dark:text-violet-100 dark:ring-violet-900 dark:hover:bg-violet-950/70'
    default:
      return 'bg-slate-50 text-slate-600 ring-slate-200/80 hover:bg-slate-100 dark:bg-slate-800/40 dark:text-slate-300 dark:ring-slate-700 dark:hover:bg-slate-800/70'
  }
}

function rotuloClasse(classe: Ponto.ClasseVisualDia | undefined): string {
  switch (classe) {
    case 'abaixo':
      return 'Abaixo da meta'
    case 'ok':
      return 'Dentro da meta'
    case 'he':
      return 'Hora extra'
    case 'feriado':
      return 'Feriado'
    case 'ausencia':
      return 'Férias / folga'
    default:
      return 'Sem jornada'
  }
}

function hojeIsoLocal(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

type Props = {
  calendario: Ponto.Calendario | null
  loading?: boolean
  diaSelecionado: string | null
  onSelecionarDia: (iso: string) => void
  onMesAnterior: () => void
  onMesSeguinte: () => void
}

export function PontoCalendarioMes({
  calendario,
  loading,
  diaSelecionado,
  onSelecionarDia,
  onMesAnterior,
  onMesSeguinte,
}: Props) {
  const hoje = hojeIsoLocal()
  const porData = useMemo(() => {
    const m = new Map<string, Ponto.DiaCalendario>()
    for (const d of calendario?.dias ?? []) m.set(d.data, d)
    return m
  }, [calendario])

  const celulas = useMemo(() => {
    if (!calendario) return []
    const primeiro = new Date(calendario.ano, calendario.mes - 1, 1)
    const offset = (primeiro.getDay() + 6) % 7
    const diasNoMes = new Date(calendario.ano, calendario.mes, 0).getDate()
    const cells: Array<{ iso: string | null; diaNum: number | null }> = []
    for (let i = 0; i < offset; i++) cells.push({ iso: null, diaNum: null })
    for (let d = 1; d <= diasNoMes; d++) {
      const iso = `${calendario.ano}-${String(calendario.mes).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      cells.push({ iso, diaNum: d })
    }
    while (cells.length % 7 !== 0) cells.push({ iso: null, diaNum: null })
    return cells
  }, [calendario])

  const titulo = calendario
    ? new Date(calendario.ano, calendario.mes - 1, 1).toLocaleDateString('pt-BR', {
        month: 'long',
        year: 'numeric',
      })
    : '…'

  const detalhe = diaSelecionado ? porData.get(diaSelecionado) : null

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button type="button" variant="secondary" onClick={onMesAnterior} disabled={loading}>
          ← Anterior
        </Button>
        <p className="text-sm font-semibold capitalize text-slate-900 dark:text-slate-100">{titulo}</p>
        <Button type="button" variant="secondary" onClick={onMesSeguinte} disabled={loading}>
          Seguinte →
        </Button>
      </div>

      {calendario?.jornada_diaria_minutos != null && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Meta diária: {formatarDuracaoLonga(calendario.jornada_diaria_minutos * 60)}
          {calendario.escala_rotulo ? ` · Escala ${calendario.escala_rotulo}` : null}
        </p>
      )}

      <div className="grid grid-cols-7 gap-1.5 text-center text-xs font-medium text-slate-500 dark:text-slate-400">
        {DIAS_SEMANA.map((d) => (
          <div key={d} className="py-1">
            {d}
          </div>
        ))}
      </div>

      {loading && !calendario ? (
        <div className="h-56 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
      ) : (
        <div className="grid grid-cols-7 gap-1.5">
          {celulas.map((c, idx) => {
            if (!c.iso || c.diaNum == null) {
              return <div key={`e-${idx}`} className="min-h-14 rounded-xl" />
            }
            const info = porData.get(c.iso)
            const sel = diaSelecionado === c.iso
            const isHoje = c.iso === hoje
            const cv = info?.classe_visual ?? 'neutro'
            return (
              <button
                key={c.iso}
                type="button"
                title={`${c.iso}: ${rotuloClasse(cv)}`}
                aria-label={`${c.diaNum}: ${rotuloClasse(cv)}${isHoje ? ' (hoje)' : ''}`}
                aria-current={isHoje ? 'date' : undefined}
                onClick={() => onSelecionarDia(c.iso!)}
                className={`min-h-14 rounded-xl px-1 py-1.5 text-sm ring-1 transition duration-200 hover:scale-[1.03] hover:shadow-sm ${classeCss(cv)} ${
                  sel
                    ? 'ring-2 ring-cyan-500 ring-offset-1 ring-offset-white dark:ring-cyan-400 dark:ring-offset-slate-900'
                    : ''
                } ${isHoje && !sel ? 'ring-2 ring-slate-400/70 dark:ring-slate-500' : ''}`}
              >
                <span className={`font-semibold ${isHoje ? 'underline decoration-2 underline-offset-2' : ''}`}>
                  {c.diaNum}
                </span>
                {info && (info.segundos_trabalhados ?? 0) > 0 ? (
                  <span className="mt-0.5 block text-[10px] font-medium leading-tight opacity-90">
                    {formatarDuracao(info.segundos_trabalhados)}
                  </span>
                ) : (
                  <span className="mt-0.5 block text-[10px] leading-tight opacity-40">·</span>
                )}
              </button>
            )
          })}
        </div>
      )}

      <ul className="flex flex-wrap gap-3 text-xs text-slate-600 dark:text-slate-300" aria-label="Legenda">
        {(
          [
            ['abaixo', 'Abaixo da meta'],
            ['ok', 'Dentro da meta'],
            ['he', 'Hora extra'],
            ['feriado', 'Feriado'],
            ['ausencia', 'Férias / folga'],
            ['neutro', 'Sem jornada'],
          ] as const
        ).map(([k, label]) => (
          <li key={k} className="flex items-center gap-1.5">
            <span className={`inline-block h-3 w-3 rounded-sm ring-1 ${classeCss(k)}`} aria-hidden />
            {label}
          </li>
        ))}
      </ul>

      {detalhe ? (
        <div className="rounded-xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-4 text-sm shadow-sm dark:border-slate-700 dark:from-slate-900 dark:to-slate-950">
          <p className="font-semibold text-slate-900 dark:text-slate-100">
            {new Date(detalhe.data + 'T12:00:00').toLocaleDateString('pt-BR', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            })}
          </p>
          <p className="mt-1 text-slate-600 dark:text-slate-300">
            <span className="font-medium">{rotuloClasse(detalhe.classe_visual)}</span>
            {' · '}
            Trabalhado <strong>{formatarDuracaoLonga(detalhe.segundos_trabalhados ?? 0)}</strong>
            {(detalhe.segundos_esperados ?? 0) > 0 ? (
              <>
                {' '}
                · Meta <strong>{formatarDuracaoLonga(detalhe.segundos_esperados)}</strong>
              </>
            ) : null}
          </p>
          <p className="mt-2 text-xs text-slate-500">
            Entrada: {detalhe.tem_entrada ? 'sim' : 'não'} · Saída: {detalhe.tem_saida ? 'sim' : 'não'}
            {detalhe.atrasado ? ' · Atraso' : ''}
            {detalhe.feriado ? ' · Feriado' : ''}
            {detalhe.ausencia_tipo === 'ferias'
              ? ' · Férias'
              : detalhe.ausencia_tipo === 'folga_programada'
                ? ' · Folga programada'
                : ''}
            {detalhe.pausa_abaixo_minimo ? ' · Pausa abaixo do mínimo' : ''}
          </p>
          <p className="mt-2 text-xs text-cyan-700 dark:text-cyan-300">
            O histórico ao lado filtra este dia automaticamente.
          </p>
        </div>
      ) : null}
    </div>
  )
}
