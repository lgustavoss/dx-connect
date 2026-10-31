import * as Notifications from 'expo-notifications'
import { router } from 'expo-router'
import { Platform } from 'react-native'

import { dispositivos } from '../api/client'
import { storageDelete, storageGet, storageSet } from './storage'

const KEY_TOKEN = 'fcm_token'

let lastResponseConsumida = false

function rotaDePayload(data: Record<string, unknown> | undefined): string | null {
  if (!data) return null
  const deep = data.deep_link
  if (typeof deep === 'string' && deep.startsWith('/')) return deep
  const chat = data.chat_id
  if (chat != null && String(chat)) return `/conversa/${chat}`
  const ticket = data.ticket_id
  if (ticket != null && String(ticket)) return `/ticket/${ticket}`
  return null
}

function abrirRota(data: Record<string, unknown> | undefined): void {
  const rota = rotaDePayload(data)
  if (rota) router.push(rota as never)
}

export function instalarHandlerNotificacao(): void {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldPlaySound: true,
      shouldSetBadge: false,
      shouldShowBanner: true,
      shouldShowList: true,
    }),
  })
}

export function escutarAberturaNotificacao(): () => void {
  if (!lastResponseConsumida) {
    lastResponseConsumida = true
    const last = Notifications.getLastNotificationResponse()
    if (last) {
      abrirRota(last.notification.request.content.data as Record<string, unknown>)
      try {
        Notifications.clearLastNotificationResponse()
      } catch {
        /* API nativa pode não existir no emulador */
      }
    }
  }

  const sub = Notifications.addNotificationResponseReceivedListener((response) => {
    abrirRota(response.notification.request.content.data as Record<string, unknown>)
  })
  return () => sub.remove()
}

export async function registrarDispositivo(): Promise<void> {
  try {
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('deskrudder', {
        name: 'DeskRudder',
        importance: Notifications.AndroidImportance.HIGH,
      })
    }
    const perm = await Notifications.requestPermissionsAsync()
    if (!perm.granted) return
    const token = await Notifications.getDevicePushTokenAsync()
    const valor = typeof token.data === 'string' ? token.data : null
    if (!valor) return
    await dispositivos.registrar(valor, 'android')
    await storageSet(KEY_TOKEN, valor)
  } catch {
    /* emulador sem Play ou Firebase ainda sem google-services.json */
  }
}

export async function revogarDispositivo(): Promise<void> {
  try {
    const token = await storageGet(KEY_TOKEN)
    if (token) await dispositivos.apagarPorToken(token)
  } catch {
    /* sessão já inválida */
  } finally {
    await storageDelete(KEY_TOKEN)
  }
}
