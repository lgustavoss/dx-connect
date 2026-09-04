import { WebPlugin, registerPlugin, type PluginListenerHandle } from '@capacitor/core'

export type UnifiedPushEndpoint = {
  endpoint: string
  p256dh: string
  auth: string
}

export type UnifiedPushOpen = {
  tipo?: string
  id?: number
  url_path?: string
  titulo?: string
  corpo?: string
}

export type UnifiedPushRegistrationError = {
  reason: string
}

export type NotificationPermissionResult = {
  granted: boolean
  /** granted | denied | prompt | unsupported */
  state: string
}

interface DeskRudderUnifiedPushPlugin {
  registerPush(options: { vapidPublicKey: string }): Promise<UnifiedPushEndpoint>
  unregisterPush(): Promise<void>
  consumePendingOpen(): Promise<UnifiedPushOpen>
  /** Android 13+: pede POST_NOTIFICATIONS (gesto do usuário). */
  requestNotificationPermission(): Promise<NotificationPermissionResult>
  /** Alerta local da fila com canal de som alto (app em 2º plano). */
  showFilaWaiting(options: { count: number }): Promise<void>
  addListener(
    eventName: 'endpoint',
    listenerFunc: (data: UnifiedPushEndpoint) => void,
  ): Promise<PluginListenerHandle>
  addListener(
    eventName: 'open',
    listenerFunc: (data: UnifiedPushOpen) => void,
  ): Promise<PluginListenerHandle>
  addListener(
    eventName: 'registrationError',
    listenerFunc: (data: UnifiedPushRegistrationError) => void,
  ): Promise<PluginListenerHandle>
  addListener(eventName: 'unregistered', listenerFunc: () => void): Promise<PluginListenerHandle>
}

class DeskRudderUnifiedPushWeb extends WebPlugin {
  async registerPush(): Promise<UnifiedPushEndpoint> {
    throw this.unavailable('UnifiedPush só está disponível no app Android.')
  }

  async unregisterPush(): Promise<void> {
    /* no-op no browser */
  }

  async consumePendingOpen(): Promise<UnifiedPushOpen> {
    return {}
  }

  async requestNotificationPermission(): Promise<NotificationPermissionResult> {
    if (typeof Notification === 'undefined') {
      return { granted: false, state: 'unsupported' }
    }
    if (Notification.permission === 'granted') {
      return { granted: true, state: 'granted' }
    }
    if (Notification.permission === 'denied') {
      return { granted: false, state: 'denied' }
    }
    try {
      const p = await Notification.requestPermission()
      return { granted: p === 'granted', state: p }
    } catch {
      return { granted: false, state: 'denied' }
    }
  }

  async showFilaWaiting(): Promise<void> {
    /* no-op — browser usa Notification da web */
  }
}

export const DeskRudderUnifiedPush = registerPlugin<DeskRudderUnifiedPushPlugin>(
  'DeskRudderUnifiedPush',
  {
    web: () => new DeskRudderUnifiedPushWeb(),
  },
)
