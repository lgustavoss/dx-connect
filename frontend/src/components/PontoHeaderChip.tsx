import { useEffect, useId, useRef, useState } from 'react'
import { ponto, type Ponto } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from './ui/Toast'
import { Button } from './ui/Button'
import { acaoPrincipalPonto, baterProximoPonto } from '../lib/pontoBater'
import { PONTO_ESTADO_EVENT } from '../lib/pontoEstadoEvent'
import { formatarDuracaoChip } from '../lib/pontoFormat'

/** Fallback se a batida ocorrer noutro sítio (admin, outro separador). */
const POLL_MS = 60_000
const TICK_MS = 1000

type Snapshot = {
  estado: Ponto.EstadoMe
  fetchedAt: number
}

function segundosExibidos(snap: Snapshot, agora: number): number {
  const base = snap.estado.segundos_trabalhados_hoje ?? 0
  if (!snap.estado.em_jornada || snap.estado.em_pausa) return base
  return base + Math.max(0, Math.floor((agora - snap.fetchedAt) / 1000))
}

function rotuloChip(estado: Ponto.EstadoMe, segundos: number): string {
  if (estado.em_pausa) return 'Em pausa'
  if (estado.em_jornada) return `Trabalhando · ${formatarDuracaoChip(segundos)}`
  return 'Fora do ponto'
}

/** Chip persistente do ponto na barra superior — clique abre batida rápida. */
export function PontoHeaderChip() {
  const { user } = useAuth()
  const toast = useToast()
  const [snap, setSnap] = useState<Snapshot | null>(null)
  const [agora, setAgora] = useState(() => Date.now())
  const [aberto, setAberto] = useState(false)
  const [batendo, setBatendo] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const panelId = useId()

  const visivel = Boolean(user && !user.must_change_password && user.role !== 'saas_ops')

  useEffect(() => {
    if (!visivel) {
      setSnap(null)
      setAberto(false)
      return
    }
    let cancelled = false

    const aplicar = (estado: Ponto.EstadoMe) => {
      const now = Date.now()
      setSnap({ estado, fetchedAt: now })
      setAgora(now)
    }

    const carregar = () => {
      void ponto
        .me()
        .then((estado) => {
          if (cancelled) return
          aplicar(estado)
        })
        .catch(() => {
          /* silencioso — não bloquear o painel */
        })
    }

    const onEstado = (e: Event) => {
      const estado = (e as CustomEvent<Ponto.EstadoMe | undefined>).detail
      if (estado) {
        aplicar(estado)
        return
      }
      carregar()
    }

    const onFoco = () => {
      if (document.visibilityState === 'visible') carregar()
    }

    carregar()
    const poll = window.setInterval(carregar, POLL_MS)
    window.addEventListener(PONTO_ESTADO_EVENT, onEstado)
    window.addEventListener('focus', onFoco)
    document.addEventListener('visibilitychange', onFoco)
    return () => {
      cancelled = true
      window.clearInterval(poll)
      window.removeEventListener(PONTO_ESTADO_EVENT, onEstado)
      window.removeEventListener('focus', onFoco)
      document.removeEventListener('visibilitychange', onFoco)
    }
  }, [visivel, user?.id])

  useEffect(() => {
    if (!snap?.estado.em_jornada || snap.estado.em_pausa) return
    const id = window.setInterval(() => setAgora(Date.now()), TICK_MS)
    return () => window.clearInterval(id)
  }, [snap?.estado.em_jornada, snap?.estado.em_pausa])

  useEffect(() => {
    if (!aberto) return
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setAberto(false)
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

  if (!visivel || !snap) return null

  const segundos = segundosExibidos(snap, agora)
  const texto = rotuloChip(snap.estado, segundos)
  const emJornada = snap.estado.em_jornada && !snap.estado.em_pausa
  const acao = acaoPrincipalPonto(!!snap.estado.em_jornada, !!snap.estado.em_pausa)

  async function onBater() {
    setBatendo(true)
    try {
      const r = await baterProximoPonto({
        estado: snap!.estado,
        incluirLocalizacao: true,
        carregarSettingsSeFaltar: true,
        toast,
      })
      if (r.ok) {
        if (r.estadoOptimista) {
          setSnap({ estado: r.estadoOptimista, fetchedAt: Date.now() })
        } else {
          try {
            const me = await ponto.me()
            setSnap({ estado: me, fetchedAt: Date.now() })
          } catch {
            /* chip atualiza no próximo poll / evento */
          }
        }
        setAberto(false)
      }
    } finally {
      setBatendo(false)
    }
  }

  const chipCls = emJornada
    ? 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200/80 dark:bg-emerald-950/50 dark:text-emerald-100 dark:ring-emerald-800/70'
    : snap.estado.em_pausa
      ? 'bg-amber-50 text-amber-900 ring-1 ring-amber-200/80 dark:bg-amber-950/40 dark:text-amber-100 dark:ring-amber-800/70'
      : 'bg-slate-100 text-slate-600 ring-1 ring-slate-200/90 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700'

  return (
    <div ref={wrapRef} className="relative shrink-0">
      <button
        type="button"
        aria-expanded={aberto}
        aria-controls={panelId}
        title="Registrar ponto"
        onClick={() => setAberto((v) => !v)}
        className={`max-w-[11rem] truncate rounded-full px-2.5 py-1 text-[11px] font-semibold leading-tight sm:max-w-[14rem] sm:text-xs ${chipCls}`}
      >
        {texto}
      </button>
      {aberto ? (
        <div
          id={panelId}
          role="dialog"
          aria-label="Registrar ponto"
          className="absolute right-0 z-50 mt-2 w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Status
          </p>
          <p className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100">{texto}</p>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">{acao.dica}</p>
          <Button
            type="button"
            className="mt-3 w-full"
            disabled={batendo}
            onClick={() => void onBater()}
          >
            {batendo ? 'Registrando…' : acao.rotulo}
          </Button>
        </div>
      ) : null}
    </div>
  )
}
