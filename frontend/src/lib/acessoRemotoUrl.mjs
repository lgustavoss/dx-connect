/** Protocolo do instalador DeskRudder (APP_NAME), não o rustdesk:// do cliente oficial. */
export function urlConexaoDeskRudder(id, senha, tituloSessao) {
  const digitos = String(id).replace(/\s+/g, '')
  const params = new URLSearchParams()
  if (senha?.trim()) params.set('password', senha.trim())
  const titulo = tituloSessao?.trim()
  if (titulo) params.set('name', titulo)
  const consulta = params.toString()
  return `deskrudder://connection/new/${digitos}${consulta ? `?${consulta}` : ''}`
}

/** Rótulo da sessão = linha de baixo do vínculo na frota (rede · rótulo código). */
export function rotuloSessaoVinculo(v) {
  if (!v) return ''
  const rotulo = String(v.rotulo_nome || '').trim() || 'Equipamento'
  const codigo = String(v.pdv_codigo || '').trim()
  const base = codigo ? `${rotulo} ${codigo}` : rotulo
  const rede = String(v.rede_nome || '').trim()
  return rede ? `${rede} · ${base}` : base
}
