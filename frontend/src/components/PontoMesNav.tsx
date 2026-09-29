import { useEffect, useId, useRef, useState } from 'react'
import { Button } from './ui/Button'

type Props = {
  ano: number
  mes: number
  onChange: (ano: number, mes: number) => void
  disabled?: boolean
  /** `curto` = ← / → · `longo` = ← Anterior / Seguinte → */
  variante?: 'curto' | 'longo'
  className?: string
}

const MESES = [
  'Jan',
  'Fev',
  'Mar',
  'Abr',
  'Mai',
  'Jun',
  'Jul',
  'Ago',
  'Set',
  'Out',
  'Nov',
  'Dez',
] as const

export function PontoMesNav({
  ano,
  mes,
  onChange,
  disabled = false,
  variante = 'curto',
  className = '',
}: Props) {
  const [aberto, setAberto] = useState(false)
  const [anoPainel, setAnoPainel] = useState(ano)
  const rootRef = useRef<HTMLDivElement>(null)
  const painelId = useId()

  const rotulo = new Date(ano, mes - 1, 1).toLocaleDateString('pt-BR', {
    month: 'long',
    year: 'numeric',
  })

  useEffect(() => {
    if (!aberto) return
    setAnoPainel(ano)
  }, [aberto, ano])

  useEffect(() => {
    if (!aberto) return
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setAberto(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setAberto(false)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [aberto])

  function ir(delta: number) {
    const d = new Date(ano, mes - 1 + delta, 1)
    onChange(d.getFullYear(), d.getMonth() + 1)
  }

  function escolher(m: number) {
    onChange(anoPainel, m)
    setAberto(false)
  }

  return (
    <div
      ref={rootRef}
      className={`relative flex flex-wrap items-center gap-2 ${className}`.trim()}
    >
      <Button
        type="button"
        variant="secondary"
        disabled={disabled}
        aria-label="Mês anterior"
        onClick={() => ir(-1)}
      >
        {variante === 'longo' ? '← Anterior' : '←'}
      </Button>

      <button
        type="button"
        disabled={disabled}
        aria-haspopup="dialog"
        aria-expanded={aberto}
        aria-controls={painelId}
        title="Clique para escolher o mês"
        onClick={() => setAberto((v) => !v)}
        className="inline-flex min-w-[9rem] flex-1 items-center justify-center rounded-lg px-2 py-1.5 text-sm font-semibold capitalize text-slate-900 transition hover:bg-slate-100 disabled:opacity-60 dark:text-slate-100 dark:hover:bg-slate-800"
      >
        {rotulo}
      </button>

      <Button
        type="button"
        variant="secondary"
        disabled={disabled}
        aria-label="Próximo mês"
        onClick={() => ir(1)}
      >
        {variante === 'longo' ? 'Seguinte →' : '→'}
      </Button>

      {aberto ? (
        <div
          id={painelId}
          role="dialog"
          aria-label="Escolher mês"
          className="absolute left-1/2 top-full z-30 mt-2 w-64 -translate-x-1/2 rounded-xl border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          <div className="mb-3 flex items-center justify-between gap-2">
            <Button
              type="button"
              variant="secondary"
              aria-label="Ano anterior"
              onClick={() => setAnoPainel((y) => y - 1)}
            >
              ←
            </Button>
            <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">{anoPainel}</span>
            <Button
              type="button"
              variant="secondary"
              aria-label="Próximo ano"
              onClick={() => setAnoPainel((y) => y + 1)}
            >
              →
            </Button>
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            {MESES.map((nome, idx) => {
              const m = idx + 1
              const selecionado = anoPainel === ano && m === mes
              return (
                <button
                  key={nome}
                  type="button"
                  onClick={() => escolher(m)}
                  className={`rounded-lg px-2 py-2 text-sm font-medium transition ${
                    selecionado
                      ? 'bg-cyan-600 text-white dark:bg-cyan-500'
                      : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
                  }`}
                >
                  {nome}
                </button>
              )
            })}
          </div>
        </div>
      ) : null}
    </div>
  )
}
