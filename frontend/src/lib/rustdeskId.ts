/** Tipo cuja frota fica no servidor da equipe (DeskRemote / nomes antigos). */
export function tipoHospedadoNoServidor(nome: string | null | undefined): boolean {
  const compacto = (nome ?? '').replace(/\s/g, '').toLowerCase()
  return (
    compacto === 'rustdesk' ||
    compacto === 'acessoremoto' ||
    compacto.startsWith('deskrudder') ||
    compacto.startsWith('deskremote')
  )
}

/** Agrupa o ID em blocos de 3 dígitos, da direita para a esquerda. */
export function formatarIdRustdesk(id: string | null | undefined): string {
  const bruto = (id ?? '').trim()
  const digitos = bruto.replace(/\s+/g, '')
  if (!/^\d{4,}$/.test(digitos)) return bruto
  return digitos.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}
