/** Geolocalização para batidas de ponto (web + Capacitor APK). */

import { Geolocation } from '@capacitor/geolocation'
import { isCapacitorNative } from './capacitorNative'

export type GeoPosition = {
  latitude: number
  longitude: number
  accuracy: number
}

export type GeoError = {
  code: number
  message: string
}

const WEB_OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  timeout: 12_000,
  maximumAge: 60_000,
}

export function geolocationSupported(): boolean {
  if (isCapacitorNative()) return true
  return typeof navigator !== 'undefined' && !!navigator.geolocation
}

async function getCurrentPositionNative(): Promise<GeoPosition> {
  let perm = await Geolocation.checkPermissions()
  if (perm.location === 'denied' || perm.coarseLocation === 'denied') {
    perm = await Geolocation.requestPermissions()
  }
  if (perm.location === 'denied' && perm.coarseLocation === 'denied') {
    throw { code: 1, message: 'Permissão de localização negada.' } satisfies GeoError
  }
  const pos = await Geolocation.getCurrentPosition({
    enableHighAccuracy: true,
    timeout: 12_000,
    maximumAge: 60_000,
  })
  return {
    latitude: pos.coords.latitude,
    longitude: pos.coords.longitude,
    accuracy: pos.coords.accuracy,
  }
}

function getCurrentPositionWeb(): Promise<GeoPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject({ code: 0, message: 'Geolocalização não é suportada neste dispositivo.' } satisfies GeoError)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        })
      },
      (err) => {
        let message = 'Não foi possível obter a localização.'
        if (err.code === err.PERMISSION_DENIED) {
          message = 'Permissão de localização negada.'
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          message = 'Localização indisponível. Verifique o GPS.'
        } else if (err.code === err.TIMEOUT) {
          message = 'Tempo esgotado ao obter a localização.'
        }
        reject({ code: err.code, message } satisfies GeoError)
      },
      WEB_OPTIONS,
    )
  })
}

export async function getCurrentPosition(): Promise<GeoPosition> {
  if (isCapacitorNative()) {
    return getCurrentPositionNative()
  }
  return getCurrentPositionWeb()
}
