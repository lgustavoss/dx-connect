/** Fila offline de batidas de ponto — localStorage + sync ao voltar online. */

import type { Ponto } from '../api/client'

const STORAGE_KEY = 'dx-ponto-offline-queue-v1'

export type PendingPontoBatida = {
  id: string
  tipo: Ponto.Tipo
  created_at: string
  latitude?: number
  longitude?: number
  accuracy_metros?: number
}

function readAll(): PendingPontoBatida[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as PendingPontoBatida[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeAll(items: PendingPontoBatida[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export function listPendingPontoBatidas(): PendingPontoBatida[] {
  return readAll()
}

export function countPendingPontoBatidas(): number {
  return readAll().length
}

export function enqueuePontoBatida(
  item: Omit<PendingPontoBatida, 'id' | 'created_at'> & { created_at?: string },
): PendingPontoBatida {
  const entry: PendingPontoBatida = {
    id: crypto.randomUUID(),
    created_at: item.created_at ?? new Date().toISOString(),
    tipo: item.tipo,
    latitude: item.latitude,
    longitude: item.longitude,
    accuracy_metros: item.accuracy_metros,
  }
  writeAll([...readAll(), entry])
  return entry
}

export function removePendingPontoBatida(id: string) {
  writeAll(readAll().filter((x) => x.id !== id))
}

export function isLikelyOfflineError(err: unknown): boolean {
  if (typeof navigator !== 'undefined' && !navigator.onLine) return true
  if (err instanceof TypeError) return true
  return false
}

export async function syncPendingPontoBatidas(
  bater: (data: Ponto.Bater) => Promise<Ponto.Batida>,
  origem: Ponto.Origem,
): Promise<number> {
  if (typeof navigator !== 'undefined' && !navigator.onLine) return 0
  const pending = readAll()
  if (pending.length === 0) return 0
  let synced = 0
  for (const item of pending) {
    try {
      await bater({
        tipo: item.tipo,
        origem,
        latitude: item.latitude,
        longitude: item.longitude,
        accuracy_metros: item.accuracy_metros,
      })
      removePendingPontoBatida(item.id)
      synced += 1
    } catch {
      break
    }
  }
  return synced
}
