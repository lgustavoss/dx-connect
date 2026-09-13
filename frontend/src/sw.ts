/// <reference lib="webworker" />
import { clientsClaim } from 'workbox-core'
import {
  cleanupOutdatedCaches,
  createHandlerBoundToURL,
  precacheAndRoute,
} from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'

declare const self: ServiceWorkerGlobalScope & { __WB_MANIFEST: Array<{ url: string; revision: string | null }> }

self.skipWaiting()
clientsClaim()
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

try {
  registerRoute(
    new NavigationRoute(createHandlerBoundToURL('index.html'), {
      denylist: [/^\/api/, /^\/v1/, /^\/docs/, /^\/health/, /^\/openapi/],
    }),
  )
} catch {
  /* em dev o index.html pode ainda não estar no precache */
}

type PushPayload = {
  tipo?: string
  id?: number
  titulo?: string
  url_path?: string
  corpo?: string | null
}

self.addEventListener('push', (event: PushEvent) => {
  let data: PushPayload = {}
  try {
    if (event.data) data = event.data.json() as PushPayload
  } catch {
    data = { titulo: event.data?.text() || 'DeskRudder' }
  }
  const title = data.titulo || 'DeskRudder'
  const body = data.corpo || 'Nova atividade no atendimento'
  const tipo = data.tipo || ''
  const isFila =
    tipo === 'chat.fila' ||
    tipo === 'chat.fila.remind' ||
    tipo === 'portal.chat.fila' ||
    tipo === 'ticket.fila' ||
    tipo === 'fila' ||
    tipo.endsWith('.fila')
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/deskrudder-pwa-192.png',
      badge: '/deskrudder-pwa-192.png',
      data,
      tag: isFila ? 'dx-connect-fila-aguardando' : `${tipo || 'push'}:${data.id || ''}`,
      renotify: true,
      requireInteraction: isFila,
      vibrate: isFila ? [200, 100, 200, 100, 200] : [180, 80, 180],
    }),
  )
})

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const data = (event.notification.data || {}) as PushPayload
  const path = data.url_path || '/'
  event.waitUntil(
    (async () => {
      const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      for (const client of all) {
        if ('focus' in client) {
          client.postMessage({ type: 'web-push-open', ...data })
          await client.focus()
          return
        }
      }
      const url = new URL(path, self.location.origin)
      if (data.tipo) url.searchParams.set('push_tipo', String(data.tipo))
      if (data.id != null) url.searchParams.set('push_id', String(data.id))
      await self.clients.openWindow(url.toString())
    })(),
  )
})
