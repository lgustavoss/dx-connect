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

interface DeskRudderUnifiedPushPlugin {
  registerPush(options: { vapidPublicKey: string }): Promise<UnifiedPushEndpoint>
  unregisterPush(): Promise<void>
  consumePendingOpen(): Promise<UnifiedPushOpen>
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
}

export const DeskRudderUnifiedPush = registerPlugin<DeskRudderUnifiedPushPlugin>(
  'DeskRudderUnifiedPush',
  {
    web: () => new DeskRudderUnifiedPushWeb(),
  },
)
