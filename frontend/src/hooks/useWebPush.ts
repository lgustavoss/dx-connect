import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { notificacoes, webPush } from '../api/client'
import { isCapacitorNative } from '../lib/capacitorNative'
import { aplicarAberturaWebPush, type WebPushOpenPayload } from '../lib/webPushDeepLink'
import { urlBase64ToUint8Array } from '../lib/webPushKeys'
import { webPushRequerPwaIos } from '../lib/pwaDisplay'
import { DeskRudderUnifiedPush, type UnifiedPushOpen } from '../plugins/unifiedPush'
import { isFilaAguardandoMuted } from './useAlertaFilaSemResponsavel'

const LS_UNIFIED_ENDPOINT = 'deskrudder-unifiedpush-endpoint'
const NATIVE_UA = 'DeskRudder-Android-UnifiedPush'

function pluginErrorCode(err: unknown): string {
  if (!err || typeof err !== 'object') return String(err)
  const rec = err as { message?: string; errorMessage?: string }
  return (rec.errorMessage || rec.message || '').toLowerCase()
}

function temAbertura(data: UnifiedPushOpen | WebPushOpenPayload | null | undefined): boolean {
  if (!data) return false
  if (data.tipo) return true
  if (data.url_path) return true
  return Number.isFinite(Number(data.id)) && Number(data.id) > 0
}

async function syncUnifiedPushSubscription(
  opts?: { ativar?: boolean },
): Promise<'ok' | 'sem_vapid' | 'negado' | 'indisponivel' | 'ios_pwa'> {
  const vapid = await webPush.vapid()
  if (!vapid.configurado || !vapid.public_key) return 'sem_vapid'

  if (opts?.ativar === false) {
    const endpoint = (() => {
      try {
        return localStorage.getItem(LS_UNIFIED_ENDPOINT)
      } catch {
        return null
      }
    })()
    if (endpoint) {
      try {
        await webPush.apagarEndpoint(endpoint)
      } catch {
        /* sessão já a expirar */
      }
      try {
        localStorage.removeItem(LS_UNIFIED_ENDPOINT)
      } catch {
        /* ignore */
      }
    }
    try {
      await DeskRudderUnifiedPush.unregisterPush()
    } catch {
      /* ignore */
    }
    await notificacoes.preferenciasUpdate({ push_habilitado: false })
    return 'ok'
  }

  try {
    const sub = await DeskRudderUnifiedPush.registerPush({ vapidPublicKey: vapid.public_key })
    if (!sub.endpoint || !sub.p256dh || !sub.auth) return 'indisponivel'
    await webPush.registrar({
      endpoint: sub.endpoint,
      p256dh: sub.p256dh,
      auth: sub.auth,
      user_agent: NATIVE_UA,
    })
    try {
      localStorage.setItem(LS_UNIFIED_ENDPOINT, sub.endpoint)
    } catch {
      /* ignore */
    }
    if (opts?.ativar === true) {
      await notificacoes.preferenciasUpdate({
        push_habilitado: true,
        push_fila: !isFilaAguardandoMuted(),
      })
    }
    return 'ok'
  } catch (err) {
    const code = pluginErrorCode(err)
    if (code.includes('negado')) return 'negado'
    if (code.includes('sem_vapid')) return 'sem_vapid'
    return 'indisponivel'
  }
}

export async function syncWebPushSubscription(
  opts?: { ativar?: boolean },
): Promise<'ok' | 'sem_vapid' | 'negado' | 'indisponivel' | 'ios_pwa'> {
  if (typeof window === 'undefined') return 'indisponivel'
  if (isCapacitorNative()) {
    return syncUnifiedPushSubscription(opts)
  }
  if (opts?.ativar !== false && webPushRequerPwaIos()) {
    return 'ios_pwa'
  }
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return 'indisponivel'
  }
  const vapid = await webPush.vapid()
  if (!vapid.configurado || !vapid.public_key) return 'sem_vapid'

  const ativar = opts?.ativar
  const registration = await navigator.serviceWorker.ready

  if (ativar === false) {
    const existente = await registration.pushManager.getSubscription()
    if (existente) {
      try {
        await webPush.apagarEndpoint(existente.endpoint)
      } catch {
        /* sessão já a expirar */
      }
      await existente.unsubscribe()
    }
    await notificacoes.preferenciasUpdate({ push_habilitado: false })
    return 'ok'
  }

  if (Notification.permission === 'denied') return 'negado'
  if (Notification.permission === 'default') {
    const perm = await Notification.requestPermission()
    if (perm !== 'granted') return 'negado'
  }

  let sub = await registration.pushManager.getSubscription()
  if (!sub) {
    sub = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapid.public_key) as BufferSource,
    })
  }
  const json = sub.toJSON()
  const p256dh = json.keys?.p256dh
  const auth = json.keys?.auth
  if (!json.endpoint || !p256dh || !auth) return 'indisponivel'
  await webPush.registrar({
    endpoint: json.endpoint,
    p256dh,
    auth,
    user_agent: navigator.userAgent.slice(0, 512),
  })
  if (ativar === true) {
    await notificacoes.preferenciasUpdate({
      push_habilitado: true,
      push_fila: !isFilaAguardandoMuted(),
    })
  }
  return 'ok'
}

/** Reinscreve se já estava activo, aplica deep link e escuta o Service Worker / UnifiedPush. */
export function useWebPushSession(enabled: boolean) {
  const navigate = useNavigate()

  useEffect(() => {
    if (!enabled) return
    aplicarPushQueryNaUrl()
    let cancelled = false

    if (isCapacitorNative()) {
      let removeEndpoint: (() => void) | undefined
      let removeOpen: (() => void) | undefined
      void (async () => {
        try {
          const endpointHandle = await DeskRudderUnifiedPush.addListener('endpoint', (data) => {
            void webPush
              .registrar({
                endpoint: data.endpoint,
                p256dh: data.p256dh,
                auth: data.auth,
                user_agent: NATIVE_UA,
              })
              .then(() => {
                try {
                  localStorage.setItem(LS_UNIFIED_ENDPOINT, data.endpoint)
                } catch {
                  /* ignore */
                }
              })
              .catch(() => undefined)
          })
          const openHandle = await DeskRudderUnifiedPush.addListener('open', (data) => {
            if (!temAbertura(data)) return
            navigate(aplicarAberturaWebPush(data))
          })
          removeEndpoint = () => {
            void endpointHandle.remove()
          }
          removeOpen = () => {
            void openHandle.remove()
          }
          const pending = await DeskRudderUnifiedPush.consumePendingOpen()
          if (!cancelled && temAbertura(pending)) {
            navigate(aplicarAberturaWebPush(pending))
          }
          const prefs = await notificacoes.preferenciasGet()
          if (cancelled) return
          const muted = isFilaAguardandoMuted()
          if (muted && prefs.push_fila) {
            await notificacoes.preferenciasUpdate({ push_fila: false })
          }
          if (prefs.push_habilitado) {
            await syncWebPushSubscription()
          }
        } catch {
          /* sessão a carregar ou vapid desligado */
        }
      })()
      return () => {
        cancelled = true
        removeEndpoint?.()
        removeOpen?.()
      }
    }

    void (async () => {
      try {
        const prefs = await notificacoes.preferenciasGet()
        if (cancelled) return
        const muted = isFilaAguardandoMuted()
        if (muted && prefs.push_fila) {
          await notificacoes.preferenciasUpdate({ push_fila: false })
        }
        if (prefs.push_habilitado && Notification.permission === 'granted') {
          await syncWebPushSubscription()
        }
      } catch {
        /* sessão a carregar ou vapid desligado */
      }
    })()

    const onMsg = (ev: MessageEvent) => {
      const data = ev.data as { type?: string; tipo?: string; id?: number; url_path?: string } | null
      if (!data || data.type !== 'web-push-open') return
      const path = aplicarAberturaWebPush(data)
      navigate(path)
    }
    navigator.serviceWorker?.addEventListener('message', onMsg)
    return () => {
      cancelled = true
      navigator.serviceWorker?.removeEventListener('message', onMsg)
    }
  }, [enabled, navigate])
}

export async function revogarWebPushNoLogout(): Promise<void> {
  if (typeof window === 'undefined') return
  if (isCapacitorNative()) {
    const endpoint = (() => {
      try {
        return localStorage.getItem(LS_UNIFIED_ENDPOINT)
      } catch {
        return null
      }
    })()
    try {
      if (endpoint) await webPush.apagarEndpoint(endpoint)
    } catch {
      /* logout continua */
    }
    try {
      localStorage.removeItem(LS_UNIFIED_ENDPOINT)
    } catch {
      /* ignore */
    }
    try {
      await DeskRudderUnifiedPush.unregisterPush()
    } catch {
      /* logout continua */
    }
    return
  }
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return
  try {
    const registration = await navigator.serviceWorker.getRegistration()
    if (!registration) return
    const sub = await registration.pushManager.getSubscription()
    if (!sub) return
    await webPush.apagarEndpoint(sub.endpoint)
    await sub.unsubscribe()
  } catch {
    /* logout continua mesmo se o push falhar */
  }
}

export function aplicarPushQueryNaUrl(): void {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams(window.location.search)
  const tipo = params.get('push_tipo')
  const idRaw = params.get('push_id')
  if (!tipo || !idRaw) return
  const id = Number(idRaw)
  if (!Number.isFinite(id)) return
  aplicarAberturaWebPush({ tipo, id })
  params.delete('push_tipo')
  params.delete('push_id')
  const next = `${window.location.pathname}${params.toString() ? `?${params}` : ''}${window.location.hash}`
  window.history.replaceState({}, '', next)
}
