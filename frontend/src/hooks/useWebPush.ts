import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { notificacoes, webPush } from '../api/client'
import { isFilaAguardandoMuted } from './useAlertaFilaSemResponsavel'
import { aplicarAberturaWebPush } from '../lib/webPushDeepLink'
import { urlBase64ToUint8Array } from '../lib/webPushKeys'

export async function syncWebPushSubscription(opts?: { ativar?: boolean }): Promise<'ok' | 'sem_vapid' | 'negado' | 'indisponivel'> {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator) || !('PushManager' in window)) {
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

/** Reinscreve se já estava activo, aplica deep link e escuta o Service Worker (#694). */
export function useWebPushSession(enabled: boolean) {
  const navigate = useNavigate()

  useEffect(() => {
    if (!enabled) return
    aplicarPushQueryNaUrl()
    let cancelled = false
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
  if (typeof window === 'undefined' || !('serviceWorker' in navigator) || !('PushManager' in window)) return
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
