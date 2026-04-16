import { useEffect, useState } from 'react'
import { notificacoes, type Notificacoes } from '../api/client'

const LS_KEY_SOUND = 'dxconnect.alerta_fila_sem_responsavel.som'
const LS_KEY_LAST_COUNT = 'dxconnect.alerta_fila_sem_responsavel.last_count'
const LS_KEY_LAST_TOTAL = 'dxconnect.notificacoes.last_total'
const LS_KEY_LAST_NAO_LIDAS = 'dxconnect.notificacoes.last_nao_lidas'
const DEFAULT_SOUND_ENABLED = true
const POLL_MS = 30_000

type ListenerFila = (state: { count: number }) => void
type ListenerResumo = (state: Notificacoes.Resumo) => void

let started = false
let inFlight = false
let currentCount = 0
let currentResumo: Notificacoes.Resumo = {
  sem_responsavel_count: 0,
  nao_lidas_count: 0,
  total_pendencias: 0,
}
let prevCount: number | null = null
let prevTotal: number | null = null
let prevNaoLidas: number | null = null
const listenersFila = new Set<ListenerFila>()
const listenersResumo = new Set<ListenerResumo>()

function getSoundEnabled(): boolean {
  try {
    const raw = localStorage.getItem(LS_KEY_SOUND)
    if (raw == null) return DEFAULT_SOUND_ENABLED
    return raw === '1'
  } catch {
    return DEFAULT_SOUND_ENABLED
  }
}

function setSoundEnabled(v: boolean) {
  try {
    localStorage.setItem(LS_KEY_SOUND, v ? '1' : '0')
  } catch {
    // ignore
  }
}

function getLastCount(): number | null {
  try {
    const raw = localStorage.getItem(LS_KEY_LAST_COUNT)
    if (raw == null) return null
    const n = Number(raw)
    return Number.isFinite(n) ? n : null
  } catch {
    return null
  }
}

function setLastCount(n: number) {
  try {
    localStorage.setItem(LS_KEY_LAST_COUNT, String(n))
  } catch {
    // ignore
  }
}

function getLastTotal(): number | null {
  try {
    const raw = localStorage.getItem(LS_KEY_LAST_TOTAL)
    if (raw == null) return null
    const n = Number(raw)
    return Number.isFinite(n) ? n : null
  } catch {
    return null
  }
}

function setLastTotal(n: number) {
  try {
    localStorage.setItem(LS_KEY_LAST_TOTAL, String(n))
  } catch {
    // ignore
  }
}

function getLastNaoLidas(): number | null {
  try {
    const raw = localStorage.getItem(LS_KEY_LAST_NAO_LIDAS)
    if (raw == null) return null
    const n = Number(raw)
    return Number.isFinite(n) ? n : null
  } catch {
    return null
  }
}

function setLastNaoLidas(n: number) {
  try {
    localStorage.setItem(LS_KEY_LAST_NAO_LIDAS, String(n))
  } catch {
    // ignore
  }
}

function playBeep() {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Ctx) return
    const ctx = new Ctx()
    const g = ctx.createGain()
    g.gain.value = 0.09
    g.connect(ctx.destination)

    const o1 = ctx.createOscillator()
    o1.type = 'sine'
    o1.frequency.value = 880
    o1.connect(g)

    const o2 = ctx.createOscillator()
    o2.type = 'sine'
    o2.frequency.value = 660
    o2.connect(g)

    o1.start()
    setTimeout(() => {
      o2.start()
    }, 140)

    setTimeout(() => {
      o1.stop()
      o2.stop()
      ctx.close().catch(() => {})
    }, 380)
  } catch {
    // ignore
  }
}

async function trySetAppBadge(count: number) {
  try {
    const nav = navigator as Navigator & { setAppBadge?: (n?: number) => Promise<void>; clearAppBadge?: () => Promise<void> }
    if (count > 0 && typeof nav.setAppBadge === 'function') {
      await nav.setAppBadge(count)
    } else if (count === 0 && typeof nav.clearAppBadge === 'function') {
      await nav.clearAppBadge()
    }
  } catch {
    // ignore
  }
}

function applyResumo(r: Notificacoes.Resumo, atualizarSom: boolean) {
  currentResumo = r
  const sem = r.sem_responsavel_count
  currentCount = sem
  for (const l of listenersFila) l({ count: sem })
  for (const l of listenersResumo) l(r)

  if (atualizarSom) {
    const prevSem = prevCount
    const prevT = prevTotal
    const prevNao = prevNaoLidas

    prevCount = sem
    prevTotal = r.total_pendencias
    prevNaoLidas = r.nao_lidas_count

    setLastCount(sem)
    setLastTotal(r.total_pendencias)
    setLastNaoLidas(r.nao_lidas_count)

    const hasIncrease =
      (prevT != null && r.total_pendencias > prevT) ||
      (prevNao != null && r.nao_lidas_count > prevNao) ||
      (prevSem != null && sem > prevSem)

    if (getSoundEnabled() && hasIncrease) {
      playBeep()
    }
  }

  const total = r.total_pendencias
  const base = (typeof document !== 'undefined' ? document.title : 'DX Connect').replace(/^\(\d+\)\s+/, '')
  if (typeof document !== 'undefined') {
    document.title = total > 0 ? `(${total}) ${base}` : base
  }
  void trySetAppBadge(total)
}

async function poll() {
  if (inFlight) return
  inFlight = true
  try {
    const r = await notificacoes.resumo()
    applyResumo(r, true)
  } catch {
    // ignore
  } finally {
    inFlight = false
  }
}

/** Atualiza contadores na UI (ex.: após marcar ticket como visto). Não dispara som de fila. */
export async function refetchPendenciasResumo() {
  if (inFlight) return
  inFlight = true
  try {
    const r = await notificacoes.resumo()
    applyResumo(r, false)
  } catch {
    // ignore
  } finally {
    inFlight = false
  }
}

function ensureStarted() {
  if (started) return
  started = true
  prevCount = getLastCount()
  prevTotal = getLastTotal()
  prevNaoLidas = getLastNaoLidas()

  void poll()
  window.setInterval(() => void poll(), POLL_MS)
}

export function usePendenciasResumo(enabled: boolean): Notificacoes.Resumo {
  const [resumo, setResumo] = useState<Notificacoes.Resumo>(currentResumo)

  useEffect(() => {
    if (!enabled) return
    ensureStarted()
    const listener: ListenerResumo = (r) => setResumo(r)
    listenersResumo.add(listener)
    setResumo(currentResumo)
    return () => {
      listenersResumo.delete(listener)
    }
  }, [enabled])

  return resumo
}

export function useAlertaFilaSemResponsavel(enabled: boolean) {
  const [count, setCount] = useState(0)
  const [soundEnabled, setSoundEnabledState] = useState(getSoundEnabled)

  useEffect(() => {
    setSoundEnabled(soundEnabled)
  }, [soundEnabled])

  useEffect(() => {
    if (!enabled) return
    ensureStarted()
    const listener: ListenerFila = ({ count: c }) => setCount(c)
    listenersFila.add(listener)
    setCount(currentCount)
    return () => {
      listenersFila.delete(listener)
    }
  }, [enabled])

  return {
    count,
    soundEnabled,
    setSoundEnabled: setSoundEnabledState,
  }
}
