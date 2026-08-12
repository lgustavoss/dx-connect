import { useEffect, useState } from 'react'
import { notificacoes, type Notificacoes } from '../api/client'
import { useEventStream } from '../contexts/EventStreamContext'
import { APP_NAME } from '../brand'

const LS_KEY_LAST_SEM_RESP = 'dxconnect.notificacoes.last_sem_responsavel'
const LS_KEY_LAST_NAO_LIDAS = 'dxconnect.notificacoes.last_nao_lidas'
const LS_KEY_LAST_WPP_FILA = 'dxconnect.notificacoes.last_wpp_fila'
const LS_KEY_LAST_WPP_RESP = 'dxconnect.notificacoes.last_wpp_resp'
const LS_KEY_LAST_PORTAL_FILA = 'dxconnect.notificacoes.last_portal_fila'
const LS_KEY_LAST_PORTAL_RESP = 'dxconnect.notificacoes.last_portal_resp'
const LS_KEY_LAST_CHAT_INTERNO = 'dxconnect.notificacoes.last_chat_interno'
/** Preferência local: silenciar loop/pulse da fila Aguardando (WPP + portal). */
const LS_KEY_FILA_AGUARDANDO_MUTED = 'dxconnect.notificacoes.fila_aguardando_muted'
const POLL_MS = 10_000
/** Fallback de segurança quando SSE está ativo (#266). */
const POLL_SSE_SAFETY_MS = 60_000
/** Evita som duplicado quando poll retorna contagem obsoleta após SSE (#406). */
const POLL_STALE_GUARD_MS = 3000
/** Dedup de transição idêntica (SSE duplicado / múltiplos listeners). */
const ALERT_DEDUP_MS = 2000

/** Tickets na fila sem responsável */
const SOUND_TICKET_FILA = '/sons/notification.mp3'
/** Nova mensagem em ticket já atribuído */
const SOUND_TICKET_MENSAGEM = '/sons/ticket-mensagem.mp3'
const SOUND_TICKET_MENSAGEM_FALLBACK = '/sons/notification.mp3'
/** Cliente aguardando na fila WhatsApp / Portal (alerta contínuo) */
const SOUND_WPP_FILA = '/sons/alerta.mp3'
/** Nova mensagem do cliente em chat WhatsApp / Portal em atendimento */
const SOUND_WPP_MENSAGEM = '/sons/wpp-mensagem.mp3'
const SOUND_WPP_MENSAGEM_FALLBACK = '/sons/notification.mp3'
/** Nova mensagem no chat interno (direta, grupo ou canal) */
const SOUND_CHAT_INTERNO = '/sons/wpp-mensagem.mp3'
const SOUND_CHAT_INTERNO_FALLBACK = '/sons/notification.mp3'

type AlertKind = 'ticket_fila' | 'ticket_mensagem' | 'wpp_fila_pulse' | 'wpp_mensagem' | 'chat_interno_mensagem'

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
  portal_fila_count: 0,
  portal_respostas_count: 0,
  chat_interno_nao_lidas_count: 0,
  total_pendencias: 0,
}
let prevSemResponsavel: number | null = null
let prevNaoLidas: number | null = null
let prevWppResp: number | null = null
let prevWppFila: number | null = null
let prevPortalFila: number | null = null
let prevPortalResp: number | null = null
let prevChatInterno: number | null = null
const listenersFila = new Set<ListenerFila>()
const listenersResumo = new Set<ListenerResumo>()

/** Preferências de som do chat interno (mute por conversa + conversa aberta). */
const mutedChatInternoIds = new Set<number>()
let chatInternoUserId: number | null = null
let activeChatInternoConversaId: number | null = null

type ListenerFilaMuted = (muted: boolean) => void
const listenersFilaMuted = new Set<ListenerFilaMuted>()

function readFilaAguardandoMuted(): boolean {
  try {
    if (typeof localStorage === 'undefined') return false
    return localStorage.getItem(LS_KEY_FILA_AGUARDANDO_MUTED) === '1'
  } catch {
    return false
  }
}

let filaAguardandoMuted = readFilaAguardandoMuted()

let wppFilaLoopAudio: HTMLAudioElement | null = null
/** Loop contínuo activo (fila > 0 e não silenciado). */
let wppFilaLoopWanted = false
let wppFilaLoopEndedHandler: (() => void) | null = null
let wppFilaLoopRetryTimer: number | null = null
/** Áudio «desbloqueado» por gesto do utilizador — melhora play em aba em background (#652). */
let audioUnlocked = false
let audioUnlockInstalled = false
let lastFilaDesktopNotifyAt = 0
let pollTimerId: number | null = null
let sseSlowPollMode = false
let sseListenerCount = 0
let sseUnsubscribe: (() => void) | null = null
let chatInternoSseUnsubscribe: (() => void) | null = null
let lastSemIncreaseAt = 0
const recentAlertKeys = new Map<string, number>()

export function setChatInternoAlertUserId(userId: number | null) {
  chatInternoUserId = userId
}

export function setActiveChatInternoConversaId(conversaId: number | null) {
  activeChatInternoConversaId = conversaId
}

export function syncChatInternoMutedIds(ids: Iterable<number>) {
  mutedChatInternoIds.clear()
  for (const id of ids) mutedChatInternoIds.add(id)
}

export function setChatInternoMuted(conversaId: number, muted: boolean) {
  if (muted) mutedChatInternoIds.add(conversaId)
  else mutedChatInternoIds.delete(conversaId)
}

export function isFilaAguardandoMuted() {
  return filaAguardandoMuted
}

/** Silencia/reativa só o alerta contínuo (e pulses) da fila Aguardando — não afeta tickets nem chat interno. */
export function setFilaAguardandoMuted(muted: boolean) {
  filaAguardandoMuted = muted
  try {
    localStorage.setItem(LS_KEY_FILA_AGUARDANDO_MUTED, muted ? '1' : '0')
  } catch {
    // ignore
  }
  if (muted) {
    // Corta na hora: loop + pulse one-shot na fila de alertas (#651)
    stopWppFilaLoop()
    stopWppFilaOneShots()
  } else {
    const filaCount = currentResumo.wpp_fila_count + currentResumo.portal_fila_count
    syncWppFilaBeep(filaCount)
  }
  for (const l of listenersFilaMuted) l(muted)
}

export function useFilaAguardandoMuted(): boolean {
  const [muted, setMuted] = useState(filaAguardandoMuted)
  useEffect(() => {
    const listener: ListenerFilaMuted = (m) => setMuted(m)
    listenersFilaMuted.add(listener)
    setMuted(filaAguardandoMuted)
    return () => {
      listenersFilaMuted.delete(listener)
    }
  }, [])
  return muted
}

function shouldPlayChatInternoSound(payload: Record<string, unknown>): boolean {
  const conversaId = typeof payload.conversa_id === 'number' ? payload.conversa_id : null
  const remetenteId = typeof payload.remetente_id === 'number' ? payload.remetente_id : null
  if (remetenteId != null && chatInternoUserId != null && remetenteId === chatInternoUserId) {
    return false
  }
  if (conversaId != null && mutedChatInternoIds.has(conversaId)) {
    return false
  }
  if (
    conversaId != null &&
    activeChatInternoConversaId === conversaId &&
    typeof document !== 'undefined' &&
    document.visibilityState === 'visible'
  ) {
    return false
  }
  return true
}

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
    case 'chat_interno_mensagem':
      return SOUND_CHAT_INTERNO
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
    case 'chat_interno_mensagem':
      playSynthPattern([
        { freq: 540, ms: 140 },
        { freq: 720, ms: 180 },
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
      if (key.startsWith('wpp_mensagem:') && src === SOUND_WPP_MENSAGEM) {
        void playSrcOnce(SOUND_WPP_MENSAGEM_FALLBACK, `${key}:fallback`, volume).then(finish)
        return
      }
      if (key.startsWith('chat_interno_mensagem:') && src === SOUND_CHAT_INTERNO) {
        void playSrcOnce(SOUND_CHAT_INTERNO_FALLBACK, `${key}:fallback`, volume).then(finish)
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
    r.wpp_respostas_count < currentResumo.wpp_respostas_count ||
    r.portal_fila_count < currentResumo.portal_fila_count ||
    r.portal_respostas_count < currentResumo.portal_respostas_count ||
    r.chat_interno_nao_lidas_count < currentResumo.chat_interno_nao_lidas_count
  )
}

async function drainAlertQueue() {
  if (drainingAlerts) return
  drainingAlerts = true
  while (alertQueue.length > 0) {
    const kind = alertQueue.shift()
    if (!kind) continue
    if (kind === 'wpp_fila_pulse' && (filaAguardandoMuted || wppFilaLoopWanted)) continue
    await playAlertKind(kind)
    await new Promise((r) => window.setTimeout(r, 180))
  }
  drainingAlerts = false
  // One-shot pode ter adiado o loop da fila — retoma se ainda houver pendências
  if (wppFilaLoopWanted && !filaAguardandoMuted) {
    ensureWppFilaLoop()
  }
}

function clearWppFilaLoopRetry() {
  if (wppFilaLoopRetryTimer != null) {
    window.clearTimeout(wppFilaLoopRetryTimer)
    wppFilaLoopRetryTimer = null
  }
}

function getWppFilaLoopAudio(): HTMLAudioElement {
  const src = SOUND_WPP_FILA
  if (!wppFilaLoopAudio) {
    wppFilaLoopAudio = getAudioElement(audioKey('wpp_fila_loop', src), src)
  }
  return wppFilaLoopAudio
}

function startFilaLoopPlayback() {
  if (!wppFilaLoopWanted || filaAguardandoMuted) return
  if (oneShotPlaying) {
    clearWppFilaLoopRetry()
    wppFilaLoopRetryTimer = window.setTimeout(() => {
      wppFilaLoopRetryTimer = null
      startFilaLoopPlayback()
    }, 250)
    return
  }

  const audio = getWppFilaLoopAudio()
  try {
    audio.pause()
    audio.currentTime = 0
  } catch {
    // ignore
  }
  audio.volume = 0.38
  const playPromise = audio.play()
  if (playPromise && typeof playPromise.then === 'function') {
    playPromise.catch(() => {
      if (!wppFilaLoopWanted || filaAguardandoMuted || oneShotPlaying) return
      // Em aba oculta o browser bloqueia play — notifica no SO e retenta ao voltar (#652)
      const filaCount = currentResumo.wpp_fila_count + currentResumo.portal_fila_count
      notifyFilaDesktop(filaCount)
      if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
        synthForKind('wpp_fila_pulse')
        clearWppFilaLoopRetry()
        wppFilaLoopRetryTimer = window.setTimeout(() => {
          wppFilaLoopRetryTimer = null
          if (wppFilaLoopWanted && !filaAguardandoMuted) startFilaLoopPlayback()
        }, 400)
      }
    })
  }
}

function onFilaLoopEnded() {
  if (!wppFilaLoopWanted || filaAguardandoMuted) return
  // Recomeça na sequência, sem intervalo fixo (sem silêncio artificial)
  startFilaLoopPlayback()
}

/** Remove pulses enfileirados e corta o one-shot da fila que estiver a tocar. */
function stopWppFilaOneShots() {
  for (let i = alertQueue.length - 1; i >= 0; i--) {
    if (alertQueue[i] === 'wpp_fila_pulse') alertQueue.splice(i, 1)
  }
  const pulseKey = audioKey('wpp_fila_pulse', SOUND_WPP_FILA)
  const pulseAudio = audioByKey.get(pulseKey)
  if (pulseAudio && !pulseAudio.paused) {
    pulseAudio.pause()
    try {
      pulseAudio.currentTime = 0
    } catch {
      // ignore
    }
    // Liberta playSrcOnce que espera 'ended'
    pulseAudio.dispatchEvent(new Event('ended'))
  }
}

function stopWppFilaLoop() {
  wppFilaLoopWanted = false
  clearWppFilaLoopRetry()
  const audio = wppFilaLoopAudio
  if (audio && wppFilaLoopEndedHandler) {
    audio.removeEventListener('ended', wppFilaLoopEndedHandler)
    wppFilaLoopEndedHandler = null
  }
  if (audio) {
    audio.pause()
    try {
      audio.currentTime = 0
    } catch {
      // ignore
    }
  }
}

function ensureWppFilaLoop() {
  if (filaAguardandoMuted) return
  wppFilaLoopWanted = true
  const audio = getWppFilaLoopAudio()
  if (!wppFilaLoopEndedHandler) {
    wppFilaLoopEndedHandler = onFilaLoopEnded
    audio.addEventListener('ended', wppFilaLoopEndedHandler)
  }
  // Já a tocar até ao fim — não reinicia a meio (deixa o 'ended' encadear)
  if (!audio.paused && !audio.ended) return
  startFilaLoopPlayback()
}

function syncWppFilaBeep(wppFilaCount: number) {
  if (wppFilaCount > 0 && !filaAguardandoMuted) {
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
  prevPortalFila = r.portal_fila_count
  prevPortalResp = r.portal_respostas_count
  prevChatInterno = r.chat_interno_nao_lidas_count
  setStoredNumber(LS_KEY_LAST_SEM_RESP, r.sem_responsavel_count)
  setStoredNumber(LS_KEY_LAST_NAO_LIDAS, r.nao_lidas_count)
  setStoredNumber(LS_KEY_LAST_WPP_FILA, r.wpp_fila_count)
  setStoredNumber(LS_KEY_LAST_WPP_RESP, r.wpp_respostas_count)
  setStoredNumber(LS_KEY_LAST_PORTAL_FILA, r.portal_fila_count)
  setStoredNumber(LS_KEY_LAST_PORTAL_RESP, r.portal_respostas_count)
  setStoredNumber(LS_KEY_LAST_CHAT_INTERNO, r.chat_interno_nao_lidas_count)
}

function applyResumo(r: Notificacoes.Resumo, atualizarSom: boolean, source: 'sse' | 'poll' | 'refetch' = 'poll') {
  if (source === 'poll' && isStalePollResumo(r)) return

  currentResumo = r
  const sem = r.sem_responsavel_count
  currentCount = sem
  for (const l of listenersFila) l({ count: sem })
  for (const l of listenersResumo) l(r)

  syncWppFilaBeep(r.wpp_fila_count + r.portal_fila_count)

  if (atualizarSom) {
    const prevSem = prevSemResponsavel
    const prevNao = prevNaoLidas
    const prevWR = prevWppResp
    const prevWppFilaValue = prevWppFila
    const prevPortalFilaValue = prevPortalFila
    const prevPortalRespValue = prevPortalResp
    const prevChatInternoValue = prevChatInterno

    if (shouldEnqueueCounterAlert('ticket_fila', prevSem, r.sem_responsavel_count)) {
      lastSemIncreaseAt = Date.now()
      const delta = r.sem_responsavel_count - (prevSem ?? r.sem_responsavel_count)
      for (let i = 0; i < delta; i++) enqueueAlert('ticket_fila')
    }

    if (
      !filaAguardandoMuted &&
      shouldEnqueueCounterAlert('wpp_fila_pulse', prevWppFilaValue, r.wpp_fila_count)
    ) {
      // Loop contínuo já cobre o alerta; pulse só se o loop ainda não estiver activo
      if (!wppFilaLoopWanted) enqueueAlert('wpp_fila_pulse')
    }

    if (
      !filaAguardandoMuted &&
      shouldEnqueueCounterAlert('wpp_fila_pulse', prevPortalFilaValue, r.portal_fila_count)
    ) {
      if (!wppFilaLoopWanted) enqueueAlert('wpp_fila_pulse')
    }

    const filaTotal = r.wpp_fila_count + r.portal_fila_count
    const prevFilaTotal = (prevWppFilaValue ?? 0) + (prevPortalFilaValue ?? 0)
    if (!filaAguardandoMuted && filaTotal > prevFilaTotal) {
      // Aba em 2º plano: garantir alerta via Notification do SO (#652)
      notifyFilaDesktop(filaTotal)
    }

    if (shouldEnqueueCounterAlert('ticket_mensagem', prevNao, r.nao_lidas_count)) {
      enqueueAlert('ticket_mensagem')
    }

    if (shouldEnqueueCounterAlert('wpp_mensagem', prevWR, r.wpp_respostas_count)) {
      enqueueAlert('wpp_mensagem')
    }

    if (shouldEnqueueCounterAlert('wpp_mensagem', prevPortalRespValue, r.portal_respostas_count)) {
      enqueueAlert('wpp_mensagem')
    }

    // Fallback quando SSE está off: contador sobe sem evento chat.interno.mensagem
    if (
      source !== 'sse' &&
      shouldEnqueueCounterAlert('chat_interno_mensagem', prevChatInternoValue, r.chat_interno_nao_lidas_count)
    ) {
      enqueueAlert('chat_interno_mensagem')
    }
  }

  persistPrevCounters(r)

  const total = r.total_pendencias
  const base = (typeof document !== 'undefined' ? document.title : APP_NAME).replace(/^\(\d+\)\s+/, '')
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
    typeof payload.portal_fila_count === 'number' &&
    typeof payload.portal_respostas_count === 'number' &&
    typeof payload.chat_interno_nao_lidas_count === 'number' &&
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
    SOUND_WPP_MENSAGEM_FALLBACK,
    SOUND_CHAT_INTERNO,
    SOUND_CHAT_INTERNO_FALLBACK,
  ]
  for (const src of sources) {
    getAudioElement(`preload:${src}`, src)
  }
}

/** Desbloqueia reprodução após gesto do utilizador (autoplay / aba em background). */
export function unlockAlertAudio() {
  if (audioUnlocked) return
  audioUnlocked = true
  const sources = [
    SOUND_TICKET_FILA,
    SOUND_TICKET_MENSAGEM,
    SOUND_WPP_FILA,
    SOUND_WPP_MENSAGEM,
    SOUND_CHAT_INTERNO,
  ]
  for (const src of sources) {
    const audio = getAudioElement(`preload:${src}`, src)
    const wasMuted = audio.muted
    audio.muted = true
    void audio
      .play()
      .then(() => {
        audio.pause()
        try {
          audio.currentTime = 0
        } catch {
          // ignore
        }
        audio.muted = wasMuted
      })
      .catch(() => {
        audio.muted = wasMuted
      })
  }
  try {
    const Ctx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (Ctx) {
      const ctx = new Ctx()
      void ctx.resume().finally(() => {
        void ctx.close().catch(() => {})
      })
    }
  } catch {
    // ignore
  }
}

export type AlertasDesktopResultado = 'granted' | 'denied' | 'default' | 'unsupported'

/**
 * Pedido explícito (gesto do utilizador no banner): desbloqueia áudio + permissão
 * de notificação do SO para alertar com aba em 2º plano / browser minimizado (#652).
 */
export async function ativarAlertasEmSegundoPlano(): Promise<AlertasDesktopResultado> {
  unlockAlertAudio()
  if (typeof Notification === 'undefined') return 'unsupported'
  if (Notification.permission === 'granted') {
    // Confirmação curta — o utilizador acabou de autorizar / já tinha
    try {
      const n = new Notification(APP_NAME, {
        body: 'Alertas activos mesmo com a aba em segundo plano.',
        tag: 'dx-connect-fila-perm-ok',
        silent: false,
      })
      window.setTimeout(() => n.close(), 4000)
    } catch {
      // ignore
    }
    return 'granted'
  }
  if (Notification.permission === 'denied') return 'denied'
  try {
    const p = await Notification.requestPermission()
    if (p === 'granted') {
      try {
        const n = new Notification(APP_NAME, {
          body: 'Alertas activos mesmo com a aba em segundo plano.',
          tag: 'dx-connect-fila-perm-ok',
          silent: false,
        })
        window.setTimeout(() => n.close(), 4000)
      } catch {
        // ignore
      }
      return 'granted'
    }
    return p === 'denied' ? 'denied' : 'default'
  } catch {
    return 'denied'
  }
}

export function getNotificationPermission(): AlertasDesktopResultado {
  if (typeof Notification === 'undefined') return 'unsupported'
  const p = Notification.permission
  if (p === 'granted' || p === 'denied' || p === 'default') return p
  return 'unsupported'
}

function installAudioUnlockListeners() {
  if (audioUnlockInstalled || typeof window === 'undefined') return
  audioUnlockInstalled = true
  const onGesture = () => {
    unlockAlertAudio()
    window.removeEventListener('pointerdown', onGesture)
    window.removeEventListener('keydown', onGesture)
    window.removeEventListener('touchstart', onGesture)
  }
  window.addEventListener('pointerdown', onGesture, { passive: true })
  window.addEventListener('keydown', onGesture)
  window.addEventListener('touchstart', onGesture, { passive: true })
}

/**
 * Notificação do SO quando a aba está oculta — browsers bloqueiam audio.play() em background.
 * Respeita silenciar da fila. Dedup ~4s para não spammar.
 */
function notifyFilaDesktop(filaCount: number) {
  if (filaAguardandoMuted || filaCount <= 0) return
  if (typeof document === 'undefined' || document.visibilityState === 'visible') return
  if (typeof Notification === 'undefined') return
  if (Notification.permission !== 'granted') return
  const now = Date.now()
  if (now - lastFilaDesktopNotifyAt < 4000) return
  lastFilaDesktopNotifyAt = now
  try {
    const body =
      filaCount === 1
        ? 'Há 1 chat aguardando atendimento'
        : `Há ${filaCount} chats aguardando atendimento`
    const n = new Notification(APP_NAME, {
      body,
      tag: 'dx-connect-fila-aguardando',
      renotify: true,
      silent: false,
    })
    n.onclick = () => {
      try {
        window.focus()
      } catch {
        // ignore
      }
      n.close()
    }
  } catch {
    // ignore
  }
}

function ensureStarted() {
  if (started) return
  started = true
  prevSemResponsavel = getStoredNumber(LS_KEY_LAST_SEM_RESP)
  prevNaoLidas = getStoredNumber(LS_KEY_LAST_NAO_LIDAS)
  prevWppFila = getStoredNumber(LS_KEY_LAST_WPP_FILA)
  prevWppResp = getStoredNumber(LS_KEY_LAST_WPP_RESP)
  prevPortalFila = getStoredNumber(LS_KEY_LAST_PORTAL_FILA)
  prevPortalResp = getStoredNumber(LS_KEY_LAST_PORTAL_RESP)
  prevChatInterno = getStoredNumber(LS_KEY_LAST_CHAT_INTERNO)

  preloadSounds()
  installAudioUnlockListeners()

  void poll()
  restartPollTimer()

  const onFocusOrVisible = () => {
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
    // Retoma o loop imediatamente ao voltar à aba (#652), sem esperar o poll
    const fila = currentResumo.wpp_fila_count + currentResumo.portal_fila_count
    syncWppFilaBeep(fila)
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
      chatInternoSseUnsubscribe = subscribe('chat.interno.mensagem', (payload) => {
        if (!shouldPlayChatInternoSound(payload)) return
        const conversaId = typeof payload.conversa_id === 'number' ? payload.conversa_id : 'x'
        const mensagemId = typeof payload.mensagem_id === 'number' ? payload.mensagem_id : Date.now()
        const key = `chat_interno_mensagem:${conversaId}:${mensagemId}`
        const now = Date.now()
        const last = recentAlertKeys.get(key)
        if (last != null && now - last < ALERT_DEDUP_MS) return
        recentAlertKeys.set(key, now)
        enqueueAlert('chat_interno_mensagem')
      })
    }
    return () => {
      sseListenerCount = Math.max(0, sseListenerCount - 1)
      if (sseListenerCount === 0) {
        sseUnsubscribe?.()
        sseUnsubscribe = null
        chatInternoSseUnsubscribe?.()
        chatInternoSseUnsubscribe = null
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
