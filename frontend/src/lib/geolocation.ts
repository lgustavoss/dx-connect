/** Geolocalização para batidas de ponto (web + WebView Capacitor). */

export type GeoPosition = {
  latitude: number
  longitude: number
  accuracy: number
}

export type GeoError = {
  code: number
  message: string
}

const OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  timeout: 12_000,
  maximumAge: 60_000,
}

export function geolocationSupported(): boolean {
  return typeof navigator !== 'undefined' && !!navigator.geolocation
}

export function getCurrentPosition(): Promise<GeoPosition> {
  return new Promise((resolve, reject) => {
    if (!geolocationSupported()) {
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
      OPTIONS,
    )
  })
}
