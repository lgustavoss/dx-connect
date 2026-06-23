import { useEffect, useState } from 'react'
import { notificacoes, type Notificacoes } from '../api/client'
import { useEventStream } from '../contexts/EventStreamContext'

const LS_KEY_LAST_SEM_RESP = 'dxconnect.notificacoes.last_sem_responsavel'
const LS_KEY_LAST_NAO_LIDAS = 'dxconnect.notificacoes.last_nao_lidas'
const LS_KEY_LAST_WPP_FILA = 'dxconnect.notificacoes.last_wpp_fila'
const LS_KEY_LAST_WPP_RESP = 'dxconnect.notificacoes.last_wpp_resp'
const POLL_MS = 10_000
/** Fallback de segurança quando SSE está ativo (#266). */
const POLL_SSE_SAFETY_MS = 60_000
/** Evita som duplicado quando poll retorna contagem obsoleta após SSE (#406). */
const POLL_STALE_GUARD_MS = 3000
/** Dedup de transição idêntica (SSE duplicado / múltiplos listeners). */
const ALERT_DEDUP_MS = 2000

/** Tickets na fila sem responsável */
const SOUND_TICKET_FILA = '/sons/alerta.mp3'
/** Nova mensagem em ticket já atribuído */
const SOUND_TICKET_MENSAGEM = '/sons/ticket-mensagem.mp3'
const SOUND_TICKET_MENSAGEM_FALLBACK = '/sons/notification.mp3'
/** Cliente aguardando na fila WhatsApp (alerta contínuo) */
const SOUND_WPP_FILA = '/sons/wpp-fila.mp3'
/** Nova mensagem do cliente em chat WhatsApp em atendimento */
const SOUND_WPP_MENSAGEM = '/sons/wpp-mensagem.mp3'

type AlertKind = 'ticket_fila' | 'ticket_mensagem' | 'wpp_fila_pulse' | 'wpp_mensagem'

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
let prevSemResponsavel: number | null = null
let prevNaoLidas: number | null = null
let prevWppResp: number | null = null
let prevWppFila: number | null = null
const listenersFila = new Set<ListenerFila>()
const listenersResumo = new Set<ListenerResumo>()

let wppFilaLoopInterval: number | null = null
let wppFilaLoopAudio: HTMLAudioElement | null = null
let pollTimerId: number | null = null
let sseSlowPollMode = false
let sseListenerCount = 0
let sseUnsubscribe: (() => void) | null = null
let lastSemIncreaseAt = 0
const recentAlertKeys = new Map<string, number>()

const audioByKey = new Map<string, HTMLAudioElement>()
const alertQueue: AlertKind[] = []
let drainingAlerts = false
let oneShotPlaying = false

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

function audioKey(kind: AlertKind | 'wpp_fila_loop', src: string) {
  return `${kind}:${src}`
}

function getAudioElement(key: string, src: string): HTMLAudioElement {
  let audio = audioByKey.get(key)
  if (!audio) {
    audio = new Audio(src)
    audio.preload = 'auto'
    audioByKey.set(key, audio)
  }
  return audio
}

function srcForKind(kind: AlertKind): string {
  switch (kind) {
    case 'ticket_fila':
      return SOUND_TICKET_FILA
    case 'ticket_mensagem':
      return SOUND_TICKET_MENSAGEM
    case 'wpp_fila_pulse':
      return SOUND_WPP_FILA
    case 'wpp_mensagem':
      return SOUND_WPP_MENSAGEM
  }
}

function playSynthPattern(notes: Array<{ freq: number; ms: number; gap?: number }>) {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Ctx) return
    const ctx = new Ctx()
    const g = ctx.createGain()
    g.gain.value = 0.09
    g.connect(ctx.destination)

    let t = ctx.currentTime
    const oscillators: OscillatorNode[] = []
    for (const note of notes) {
      const o = ctx.createOscillator()
      o.type = 'sine'
      o.frequency.value = note.freq
      o.connect(g)
      o.start(t)
      o.stop(t + note.ms / 1000)
      oscillators.push(o)
      t += note.ms / 1000 + (note.gap ?? 0.05)
    }

    window.setTimeout(() => {
      ctx.close().catch(() => {})
    }, Math.ceil((t - ctx.currentTime) * 1000) + 40)
  } catch {
    // ignore
  }
}

function synthForKind(kind: AlertKind) {
  switch (kind) {
    case 'ticket_fila':
      playSynthPattern([
        { freq: 520, ms: 180 },
        { freq: 660, ms: 220 },
      ])
      break
    case 'ticket_mensagem':
      playSynthPattern([{ freq: 740, ms: 300 }])
      break
    case 'wpp_fila_pulse':
      playSynthPattern([
        { freq: 980, ms: 110, gap: 0.04 },
        { freq: 880, ms: 110, gap: 0.04 },
        { freq: 980, ms: 130 },
      ])
      break
    case 'wpp_mensagem':
      playSynthPattern([
        { freq: 620, ms: 160 },
        { freq: 780, ms: 200 },
      ])
      break
  }
}

function playSrcOnce(src: string, key: string, volume: number): Promise<void> {
  return new Promise((resolve) => {
    const audio = getAudioElement(key, src)
    let settled = false
    const finish = () => {
      if (settled) return
      settled = true
      audio.removeEventListener('ended', onEnded)
      audio.removeEventListener('error', onError)
      resolve()
    }
    const onEnded = () => finish()
    const onError = () => {
      if (key.startsWith('ticket_mensagem:') && src === SOUND_TICKET_MENSAGEM) {
        void playSrcOnce(SOUND_TICKET_MENSAGEM_FALLBACK, `${key}:fallback`, volume).then(finish)
        return
      }
      const kind = key.split(':')[0] as AlertKind
      synthForKind(kind)
      finish()
    }

    audio.addEventListener('ended', onEnded)
    audio.addEventListener('error', onError, { once: true })
    audio.pause()
    audio.currentTime = 0
    audio.volume = volume
    audio.play().catch(onError)
  })
}

async function playAlertKind(kind: AlertKind) {
  oneShotPlaying = true
  try {
    await playSrcOnce(srcForKind(kind), audioKey(kind, srcForKind(kind)), 0.44)
  } finally {
    oneShotPlaying = false
  }
}

function enqueueAlert(kind: AlertKind) {
  alertQueue.push(kind)
  void drainAlertQueue()
}

function shouldEnqueueCounterAlert(kind: AlertKind, prev: number | null, next: number): boolean {
  if (prev == null || next <= prev) return false
  const key = `${kind}:${prev}->${next}`
  const now = Date.now()
  const last = recentAlertKeys.get(key)
  if (last != null && now - last < ALERT_DEDUP_MS) return false
  recentAlertKeys.set(key, now)
  return true
}

function isStalePollResumo(r: Notificacoes.Resumo): boolean {
  if (Date.now() - lastSemIncreaseAt >= POLL_STALE_GUARD_MS) return false
  return (
    r.sem_responsavel_count < currentResumo.sem_responsavel_count ||
    r.nao_lidas_count < currentResumo.nao_lidas_count ||
    r.wpp_fila_count < currentResumo.wpp_fila_count ||
    r.wpp_respostas_count < currentResumo.wpp_respostas_count
  )
}

async function drainAlertQueue() {
  if (drainingAlerts) return
  drainingAlerts = true
  while (alertQueue.length > 0) {
    const kind = alertQueue.shift()
    if (!kind) continue
    await playAlertKind(kind)
    await new Promise((r) => window.setTimeout(r, 180))
  }
  drainingAlerts = false
}

function playWppFilaLoopPulse() {
  if (oneShotPlaying) return

  const src = SOUND_WPP_FILA
  if (!wppFilaLoopAudio) {
    wppFilaLoopAudio = getAudioElement(audioKey('wpp_fila_loop', src), src)
  }
  const audio = wppFilaLoopAudio
  audio.pause()
  audio.currentTime = 0
  audio.volume = 0.38
  audio.play().catch(() => {
    if (!oneShotPlaying) synthForKind('wpp_fila_pulse')
  })
}

function stopWppFilaLoop() {
  if (wppFilaLoopInterval != null) {
    window.clearInterval(wppFilaLoopInterval)
    wppFilaLoopInterval = null
  }
  wppFilaLoopAudio?.pause()
}

function ensureWppFilaLoop() {
  if (wppFilaLoopInterval != null) return
  playWppFilaLoopPulse()
  wppFilaLoopInterval = window.setInterval(() => {
    playWppFilaLoopPulse()
  }, 5200)
}

function syncWppFilaBeep(wppFilaCount: number) {
  if (wppFilaCount > 0) {
    ensureWppFilaLoop()
  } else {
    stopWppFilaLoop()
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

function persistPrevCounters(r: Notificacoes.Resumo) {
  prevSemResponsavel = r.sem_responsavel_count
  prevNaoLidas = r.nao_lidas_count
  prevWppResp = r.wpp_respostas_count
  prevWppFila = r.wpp_fila_count
  setStoredNumber(LS_KEY_LAST_SEM_RESP, r.sem_responsavel_count)
  setStoredNumber(LS_KEY_LAST_NAO_LIDAS, r.nao_lidas_count)
  setStoredNumber(LS_KEY_LAST_WPP_FILA, r.wpp_fila_count)
  setStoredNumber(LS_KEY_LAST_WPP_RESP, r.wpp_respostas_count)
}

function applyResumo(r: Notificacoes.Resumo, atualizarSom: boolean, source: 'sse' | 'poll' | 'refetch' = 'poll') {
  if (source === 'poll' && isStalePollResumo(r)) return

  currentResumo = r
  const sem = r.sem_responsavel_count
  currentCount = sem
  for (const l of listenersFila) l({ count: sem })
  for (const l of listenersResumo) l(r)

  syncWppFilaBeep(r.wpp_fila_count)

  if (atualizarSom) {
    const prevSem = prevSemResponsavel
    const prevNao = prevNaoLidas
    const prevWR = prevWppResp
    const prevWppFilaValue = prevWppFila

    if (shouldEnqueueCounterAlert('ticket_fila', prevSem, r.sem_responsavel_count)) {
      lastSemIncreaseAt = Date.now()
      const delta = r.sem_responsavel_count - (prevSem ?? r.sem_responsavel_count)
      for (let i = 0; i < delta; i++) enqueueAlert('ticket_fila')
    }

    if (shouldEnqueueCounterAlert('wpp_fila_pulse', prevWppFilaValue, r.wpp_fila_count)) {
      enqueueAlert('wpp_fila_pulse')
    }

    if (shouldEnqueueCounterAlert('ticket_mensagem', prevNao, r.nao_lidas_count)) {
      enqueueAlert('ticket_mensagem')
    }

    if (shouldEnqueueCounterAlert('wpp_mensagem', prevWR, r.wpp_respostas_count)) {
      enqueueAlert('wpp_mensagem')
    }
  }

  persistPrevCounters(r)

  const total = r.total_pendencias
  const base = (typeof document !== 'undefined' ? document.title : 'DX Connect').replace(/^\(\d+\)\s+/, '')
  if (typeof document !== 'undefined') {
    document.title = total > 0 ? `(${total}) ${base}` : base
  }
  void trySetAppBadge(total)
}

function isNotificacaoResumo(payload: Record<string, unknown>): boolean {
  return (
    typeof payload.sem_responsavel_count === 'number' &&
    typeof payload.nao_lidas_count === 'number' &&
    typeof payload.wpp_fila_count === 'number' &&
    typeof payload.wpp_respostas_count === 'number' &&
    typeof payload.total_pendencias === 'number'
  )
}

/** Atualiza contadores a partir de evento SSE `notificacao.contagem`. */
export function applyNotificacaoResumoSse(payload: Record<string, unknown>) {
  if (!isNotificacaoResumo(payload)) return
  applyResumo(payload as unknown as Notificacoes.Resumo, true, 'sse')
}

function restartPollTimer() {
  if (pollTimerId != null) window.clearInterval(pollTimerId)
  const ms = sseSlowPollMode ? POLL_SSE_SAFETY_MS : POLL_MS
  pollTimerId = window.setInterval(() => void poll(), ms)
}

function setSsePollingMode(useFallback: boolean) {
  const slow = !useFallback
  if (slow === sseSlowPollMode) return
  sseSlowPollMode = slow
  if (!started) return
  restartPollTimer()
}

async function poll() {
  if (inFlight) return
  inFlight = true
  try {
    const r = await notificacoes.resumo()
    applyResumo(r, true, 'poll')
  } catch {
    // ignore
  } finally {
    inFlight = false
  }
}

/** Atualiza contadores na UI. `atualizarSom=false` evita beeps pontuais, mas sincroniza o loop da fila WPP. */
export async function refetchPendenciasResumo(atualizarSom = false) {
  if (inFlight) return
  inFlight = true
  try {
    const r = await notificacoes.resumo()
    applyResumo(r, atualizarSom, 'refetch')
  } catch {
    // ignore
  } finally {
    inFlight = false
  }
}

function preloadSounds() {
  const sources = [
    SOUND_TICKET_FILA,
    SOUND_TICKET_MENSAGEM,
    SOUND_TICKET_MENSAGEM_FALLBACK,
    SOUND_WPP_FILA,
    SOUND_WPP_MENSAGEM,
  ]
  for (const src of sources) {
    getAudioElement(`preload:${src}`, src)
  }
}

function ensureStarted() {
  if (started) return
  started = true
  prevSemResponsavel = getStoredNumber(LS_KEY_LAST_SEM_RESP)
  prevNaoLidas = getStoredNumber(LS_KEY_LAST_NAO_LIDAS)
  prevWppFila = getStoredNumber(LS_KEY_LAST_WPP_FILA)
  prevWppResp = getStoredNumber(LS_KEY_LAST_WPP_RESP)

  preloadSounds()

  void poll()
  restartPollTimer()

  const onFocusOrVisible = () => {
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
    void poll()
  }
  window.addEventListener('focus', onFocusOrVisible)
  document.addEventListener('visibilitychange', onFocusOrVisible)
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
  const { subscribe, useFallback } = useEventStream()
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (!enabled) return
    setSsePollingMode(useFallback)
  }, [enabled, useFallback])

  useEffect(() => {
    if (!enabled) return
    ensureStarted()
    sseListenerCount++
    if (sseListenerCount === 1) {
      sseUnsubscribe = subscribe('notificacao.contagem', (payload) => {
        applyNotificacaoResumoSse(payload)
      })
    }
    return () => {
      sseListenerCount = Math.max(0, sseListenerCount - 1)
      if (sseListenerCount === 0) {
        sseUnsubscribe?.()
        sseUnsubscribe = null
      }
    }
  }, [enabled, subscribe])

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
