/** Protocolo do instalador DeskRudder (APP_NAME), não o rustdesk:// do cliente oficial. */
export function urlConexaoDeskRudder(id, senha) {
  const digitos = String(id).replace(/\s+/g, '')
  const params = new URLSearchParams()
  if (senha?.trim()) params.set('password', senha.trim())
  const consulta = params.toString()
  return `deskrudder://connection/new/${digitos}${consulta ? `?${consulta}` : ''}`
}
