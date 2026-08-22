import type { Ponto } from '../api/client'

/** Actualiza estado local após batida offline (antes do sync). */
export function aplicarBatidaOptimista(
  estado: Ponto.EstadoMe | null,
  tipo: Ponto.Tipo,
  quando = new Date().toISOString(),
): Ponto.EstadoMe | null {
  if (!estado) return estado
  if (tipo === 'entrada') {
    return {
      ...estado,
      em_jornada: true,
      em_pausa: false,
      entrada_aberta_em: quando,
    }
  }
  if (tipo === 'saida') {
    return {
      ...estado,
      em_jornada: false,
      em_pausa: false,
      entrada_aberta_em: null,
    }
  }
  if (tipo === 'pausa_inicio') {
    return { ...estado, em_pausa: true }
  }
  if (tipo === 'pausa_fim') {
    return { ...estado, em_pausa: false }
  }
  return estado
}

export function rotuloGeoIntervalo(it: Ponto.Intervalo): string | null {
  const partes: string[] = []
  if (it.entrada_latitude != null && it.entrada_longitude != null) {
    partes.push(it.entrada_fora_area ? 'Entrada fora da área' : 'Entrada com GPS')
  }
  if (it.saida_latitude != null && it.saida_longitude != null) {
    partes.push(it.saida_fora_area ? 'Saída fora da área' : 'Saída com GPS')
  }
  return partes.length ? partes.join(' · ') : null
}

export function coordenadasMapaIntervalo(
  it: Ponto.Intervalo,
): { lat: number; lon: number; label: string } | null {
  if (it.entrada_latitude != null && it.entrada_longitude != null) {
    return {
      lat: it.entrada_latitude,
      lon: it.entrada_longitude,
      label: it.entrada_fora_area ? 'Entrada (fora da área)' : 'Entrada',
    }
  }
  if (it.saida_latitude != null && it.saida_longitude != null) {
    return {
      lat: it.saida_latitude,
      lon: it.saida_longitude,
      label: it.saida_fora_area ? 'Saída (fora da área)' : 'Saída',
    }
  }
  return null
}
