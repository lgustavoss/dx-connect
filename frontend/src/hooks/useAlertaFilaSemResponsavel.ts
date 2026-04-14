import { useEffect, useState } from 'react'
import { tickets } from '../api/client'

const LS_KEY_SOUND = 'dxconnect.alerta_fila_sem_responsavel.som'
const LS_KEY_LAST_COUNT = 'dxconnect.alerta_fila_sem_responsavel.last_count'
const DEFAULT_SOUND_ENABLED = true
const POLL_MS = 30_000

type Listener = (state: { count: number }) => void

let started = false
let inFlight = false
let currentCount = 0
let prevCount: number | null = null
const listeners = new Set<Listener>()

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

function ensureStarted() {
  if (started) return
  started = true
  prevCount = getLastCount()

  const poll = async () => {
    if (inFlight) return
    inFlight = true
    try {
      const { total } = await tickets.list({
        sem_responsavel: true,
        offset: 0,
        limit: 1,
      })

      currentCount = total
      for (const l of listeners) l({ count: currentCount })

      const prev = prevCount
      prevCount = total
      setLastCount(total)

      if (getSoundEnabled() && prev != null && total > prev) {
        playBeep()
      }

      const base = (typeof document !== 'undefined' ? document.title : 'DX Connect').replace(/^\(\d+\)\s+/, '')
      if (typeof document !== 'undefined') {
        document.title = total > 0 ? `(${total}) ${base}` : base
      }
      void trySetAppBadge(total)
    } catch {
      // ignore
    } finally {
      inFlight = false
    }
  }

  void poll()
  window.setInterval(poll, POLL_MS)
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
    const listener: Listener = ({ count }) => setCount(count)
    listeners.add(listener)
    // estado inicial imediato
    setCount(currentCount)
    return () => {
      listeners.delete(listener)
      // Mantém o poll ativo globalmente enquanto houver user logado.
    }
  }, [enabled])

  return {
    count,
    soundEnabled,
    setSoundEnabled: setSoundEnabledState,
  }
}

