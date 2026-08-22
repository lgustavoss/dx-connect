/** Formatação compartilhada entre Meu ponto e Ponto da equipe. */

export function formatarHora(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function formatarHoraCurta(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

export function formatarDuracao(segundos: number | null | undefined): string {
  if (segundos == null || segundos < 0) return '—'
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  if (h <= 0) return `${m} min`
  return `${h} h ${String(m).padStart(2, '0')} min`
}

export function inicioMesIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

export function hojeIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function linkMapaOsm(lat: number, lon: number): string {
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`
}

export function rotuloPoliticaGeo(p: PontoPoliticaGeo): string {
  switch (p) {
    case 'obrigatoria':
      return 'Obrigatória'
    case 'recomendada':
      return 'Recomendada'
    default:
      return 'Opcional'
  }
}

export type PontoPoliticaGeo = 'opcional' | 'recomendada' | 'obrigatoria'
