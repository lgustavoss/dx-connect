import { useEffect, useState } from 'react'
import { notificacoes, type Notificacoes } from '../api/client'

const LS_KEY_LAST_COUNT = 'dxconnect.alerta_fila_sem_responsavel.last_count'
const LS_KEY_LAST_WPP_FILA = 'dxconnect.notificacoes.last_wpp_fila'
const LS_KEY_LAST_WPP_RESP = 'dxconnect.notificacoes.last_wpp_resp'
const POLL_MS = 30_000

type ListenerFila = (state: { count: number }) => void
type ListenerResumo = (state: Notificacoes.Resumo) => void

let started = false
let inFlight = false
let currentCount = 0
let currentResumo: Notificacoes.Resumo = {
  sem_responsavel_count: 0,
  nao_lidas_count: 0,
  wpp_fila_count: 0,
  wpp_respostas_count: 0,
  total_pendencias: 0,
}
let prevCount: number | null = null
let prevWppResp: number | null = null
const listenersFila = new Set<ListenerFila>()
const listenersResumo = new Set<ListenerResumo>()

let wppBeepInterval: number | null = null

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

function getLastWppFila(): number | null {
  try {
    const raw = localStorage.getItem(LS_KEY_LAST_WPP_FILA)
    if (raw == null) return null
    const n = Number(raw)
    return Number.isFinite(n) ? n : null
  } catch {
    return null
  }
}

function setLastWppFila(n: number) {
  try {
    localStorage.setItem(LS_KEY_LAST_WPP_FILA, String(n))
  } catch {
    // ignore
  }
}

function getLastWppResp(): number | null {
  try {
    const raw = localStorage.getItem(LS_KEY_LAST_WPP_RESP)
    if (raw == null) return null
    const n = Number(raw)
    return Number.isFinite(n) ? n : null
  } catch {
    return null
  }
}

function setLastWppResp(n: number) {
  try {
    localStorage.setItem(LS_KEY_LAST_WPP_RESP, String(n))
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

function stopWppContinuousBeep() {
  if (wppBeepInterval != null) {
    window.clearInterval(wppBeepInterval)
    wppBeepInterval = null
  }
}

function ensureWppContinuousBeep() {
  if (wppBeepInterval != null) return
  // Beep curto e contínuo até a fila de WhatsApp zerar.
  wppBeepInterval = window.setInterval(() => {
    playBeep()
  }, 4500)
  // dispara um logo no início
  playBeep()
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
    const prevWR = prevWppResp

    prevCount = sem
    prevWppResp = r.wpp_respostas_count

    setLastCount(sem)
    setLastWppFila(r.wpp_fila_count)
    setLastWppResp(r.wpp_respostas_count)

    // Som: tickets na fila => 1 beep quando aumentar.
    if (prevSem != null && sem > prevSem) {
      playBeep()
    }

    // Som: chats na fila => beep contínuo enquanto houver chats na fila.
    if (r.wpp_fila_count > 0) {
      ensureWppContinuousBeep()
    } else {
      stopWppContinuousBeep()
    }

    // Resposta em chat do atendente => 1 beep quando aumentar.
    if (prevWR != null && r.wpp_respostas_count > prevWR) {
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
  // Só precisamos do "último valor" para evitar beep duplicado por refresh.
  // (wpp_fila é contínuo e não depende de delta)
  void getLastWppFila()
  prevWppResp = getLastWppResp()

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
  }
}
