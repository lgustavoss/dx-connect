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

export function formatarDataRef(iso: string | null | undefined): string {
  if (!iso) return '—'
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!m) return iso
  return `${m[3]}/${m[2]}/${m[1]}`
}

/** Data de referência junto do horário pedido na inclusão ou correção. */
export function quandoSolicitado(dataRef: string, horarioIso: string | null | undefined): string {
  return `${formatarDataRef(dataRef)} às ${formatarHoraCurta(horarioIso)}`
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

export function formatarDuracaoChip(segundos: number | null | undefined): string {
  if (segundos == null || segundos < 0) return '0min'
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  if (h <= 0) return `${m}min`
  return `${h}h ${m}min`
}

export function inicioMesIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

export function hojeIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Janela de até 12 meses anteriores ao mês — o saldo líquido é o saldo inicial da competência. */
export function boundsSaldoInicialMes(ano: number, mes: number): { desde: string; ate: string } {
  const pad = (n: number) => String(n).padStart(2, '0')
  const ateDate = new Date(ano, mes - 1, 0) // último dia do mês anterior
  const ateAno = ateDate.getFullYear()
  const ateMes = ateDate.getMonth() + 1
  const ateDia = ateDate.getDate()
  const desdeDate = new Date(ateAno, ateMes - 12, 1)
  return {
    desde: `${desdeDate.getFullYear()}-${pad(desdeDate.getMonth() + 1)}-01`,
    ate: `${ateAno}-${pad(ateMes)}-${pad(ateDia)}`,
  }
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
