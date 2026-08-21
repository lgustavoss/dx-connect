import { useMemo } from 'react'
import type { Ponto } from '../api/client'
import { Button } from './ui/Button'

const DIAS_SEMANA = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

function formatarDuracao(segundos: number | null | undefined): string {
  if (segundos == null || segundos < 0) return '—'
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  if (h <= 0) return `${m} min`
  return `${h} h ${String(m).padStart(2, '0')} min`
}

function classeCss(classe: Ponto.ClasseVisualDia | undefined): string {
  switch (classe) {
    case 'abaixo':
      return 'bg-red-100 text-red-900 ring-red-200 dark:bg-red-950/50 dark:text-red-100 dark:ring-red-900'
    case 'ok':
      return 'bg-emerald-100 text-emerald-900 ring-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-100 dark:ring-emerald-900'
    case 'he':
      return 'bg-sky-100 text-sky-900 ring-sky-200 dark:bg-sky-950/50 dark:text-sky-100 dark:ring-sky-900'
    case 'feriado':
      return 'bg-orange-100 text-orange-900 ring-orange-200 dark:bg-orange-950/50 dark:text-orange-100 dark:ring-orange-900'
    default:
      return 'bg-slate-50 text-slate-600 ring-slate-200 dark:bg-slate-800/40 dark:text-slate-300 dark:ring-slate-700'
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
    default:
      return 'Sem jornada'
  }
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
  const porData = useMemo(() => {
    const m = new Map<string, Ponto.DiaCalendario>()
    for (const d of calendario?.dias ?? []) m.set(d.data, d)
    return m
  }, [calendario])

  const celulas = useMemo(() => {
    if (!calendario) return []
    const primeiro = new Date(calendario.ano, calendario.mes - 1, 1)
    // JS: 0=Dom … 6=Sáb → deslocar para semana Seg–Dom
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
          ← Mês anterior
        </Button>
        <p className="text-sm font-semibold capitalize text-slate-900 dark:text-slate-100">{titulo}</p>
        <Button type="button" variant="secondary" onClick={onMesSeguinte} disabled={loading}>
          Mês seguinte →
        </Button>
      </div>

      {calendario?.jornada_diaria_minutos != null && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Meta diária: {formatarDuracao(calendario.jornada_diaria_minutos * 60)}
          {calendario.escala_rotulo ? ` · Escala ${calendario.escala_rotulo}` : null}
        </p>
      )}

      <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-slate-500 dark:text-slate-400">
        {DIAS_SEMANA.map((d) => (
          <div key={d} className="py-1">
            {d}
          </div>
        ))}
      </div>

      {loading && !calendario ? (
        <div className="h-48 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
      ) : (
        <div className="grid grid-cols-7 gap-1">
          {celulas.map((c, idx) => {
            if (!c.iso || c.diaNum == null) {
              return <div key={`e-${idx}`} className="min-h-12 rounded-lg" />
            }
            const info = porData.get(c.iso)
            const sel = diaSelecionado === c.iso
            const cv = info?.classe_visual ?? 'neutro'
            return (
              <button
                key={c.iso}
                type="button"
                title={`${c.iso}: ${rotuloClasse(cv)}`}
                aria-label={`${c.diaNum}: ${rotuloClasse(cv)}`}
                onClick={() => onSelecionarDia(c.iso!)}
                className={`min-h-12 rounded-lg px-1 py-1.5 text-sm ring-1 transition ${classeCss(cv)} ${
                  sel ? 'ring-2 ring-offset-1 ring-slate-900 dark:ring-slate-100 dark:ring-offset-slate-900' : ''
                }`}
              >
                <span className="font-semibold">{c.diaNum}</span>
                {info && (info.segundos_trabalhados ?? 0) > 0 && (
                  <span className="mt-0.5 block text-[10px] leading-tight opacity-80">
                    {formatarDuracao(info.segundos_trabalhados)}
                  </span>
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
            ['neutro', 'Sem jornada'],
          ] as const
        ).map(([k, label]) => (
          <li key={k} className="flex items-center gap-1.5">
            <span className={`inline-block h-3 w-3 rounded ring-1 ${classeCss(k)}`} aria-hidden />
            {label}
          </li>
        ))}
      </ul>

      {detalhe && (
        <div className="rounded-xl border border-slate-200 bg-white/60 p-3 text-sm dark:border-slate-700 dark:bg-slate-900/40">
          <p className="font-medium text-slate-900 dark:text-slate-100">
            {detalhe.data} — {rotuloClasse(detalhe.classe_visual)}
          </p>
          <p className="mt-1 text-slate-600 dark:text-slate-300">
            Trabalhado: <strong>{formatarDuracao(detalhe.segundos_trabalhados ?? 0)}</strong>
            {(detalhe.segundos_esperados ?? 0) > 0 && (
              <>
                {' '}
                · Meta: <strong>{formatarDuracao(detalhe.segundos_esperados)}</strong>
              </>
            )}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Entrada: {detalhe.tem_entrada ? 'sim' : 'não'} · Saída: {detalhe.tem_saida ? 'sim' : 'não'}
            {detalhe.atrasado ? ' · Atraso' : ''}
            {detalhe.feriado ? ' · Feriado' : ''}
          </p>
        </div>
      )}
    </div>
  )
}
