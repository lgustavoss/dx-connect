import { useEffect, useState } from 'react'
import { notificacoes, type Notificacoes } from '../api/client'

const LS_KEY_LAST_NAO_LIDAS = 'dxconnect.notificacoes.last_nao_lidas'
const LS_KEY_LAST_WPP_FILA = 'dxconnect.notificacoes.last_wpp_fila'
const LS_KEY_LAST_WPP_RESP = 'dxconnect.notificacoes.last_wpp_resp'
const POLL_MS = 30_000
const SOUND_NOTIFICATION = '/sons/notification.mp3'
const SOUND_OPEN_TICKET_ALERT = '/sons/alerta.mp3'

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
let prevNaoLidas: number | null = null
let prevWppResp: number | null = null
let prevWppFila: number | null = null
const listenersFila = new Set<ListenerFila>()
const listenersResumo = new Set<ListenerResumo>()

let wppBeepInterval: number | null = null

function getStoredNumber(key: string): number | null {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null) return null
    const n = Number(raw)
    return Number.isFinite(n) ? n : null
  } catch {
    return null
  }
}

function setStoredNumber(key: string, n: number) {
  try {
    localStorage.setItem(key, String(n))
  } catch {
    // ignore
  }
}

const audioBySrc = new Map<string, HTMLAudioElement>()

function playAudio(src: string, volume = 0.45) {
  try {
    let audio = audioBySrc.get(src)
    if (!audio) {
      audio = new Audio(src)
      audio.preload = 'auto'
      audioBySrc.set(src, audio)
    }
    audio.currentTime = 0
    audio.volume = volume
    audio.play().catch(() => {
      playSynthBeep()
    })
  } catch {
    playSynthBeep()
  }
}

function playSystemNotification() {
  playAudio(SOUND_NOTIFICATION, 0.42)
}

function playOpenTicketAlert() {
  playAudio(SOUND_OPEN_TICKET_ALERT, 0.45)
}

function playSynthBeep() {
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
    playSystemNotification()
  }, 4500)
  // dispara um logo no início
  playSystemNotification()
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
    const prevNao = prevNaoLidas
    const prevWR = prevWppResp
    const prevWppFilaValue = prevWppFila

    prevNaoLidas = r.nao_lidas_count
    prevWppResp = r.wpp_respostas_count
    prevWppFila = r.wpp_fila_count

    setStoredNumber(LS_KEY_LAST_NAO_LIDAS, r.nao_lidas_count)
    setStoredNumber(LS_KEY_LAST_WPP_FILA, r.wpp_fila_count)
    setStoredNumber(LS_KEY_LAST_WPP_RESP, r.wpp_respostas_count)

    // Som: chats na fila de WhatsApp => 1 beep quando a fila aumentar.
    const wppFilaIncreased = prevWppFilaValue != null ? r.wpp_fila_count > prevWppFilaValue : false
    if (wppFilaIncreased) {
      playOpenTicketAlert()
    }

    // Som padrao do sistema: novas mensagens/novidades em tickets ja atribuidos.
    if (prevNao != null && r.nao_lidas_count > prevNao) {
      playSystemNotification()
    }

    // Som: chats na fila => beep contínuo enquanto houver chats na fila.
    if (r.wpp_fila_count > 0) {
      ensureWppContinuousBeep()
    } else {
      stopWppContinuousBeep()
    }

    // Resposta em chat do atendente => 1 beep quando aumentar.
    if (prevWR != null && r.wpp_respostas_count > prevWR) {
      playSystemNotification()
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
  prevNaoLidas = getStoredNumber(LS_KEY_LAST_NAO_LIDAS)
  // Carregamos o último valor conhecido da fila de WPP para detectar aumentos originados
  // por chats (para tocar `alerta.mp3` apenas nesses casos).
  prevWppFila = getStoredNumber(LS_KEY_LAST_WPP_FILA)
  prevWppResp = getStoredNumber(LS_KEY_LAST_WPP_RESP)

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
