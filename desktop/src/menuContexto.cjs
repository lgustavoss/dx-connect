/** Itens do menu de contexto do painel Electron (ortografia + Copiar). */

function itensMenuContexto(params) {
  const palavra = String(params?.misspelledWord || '').trim()
  const sugestoes = Array.isArray(params?.dictionarySuggestions) ? params.dictionarySuggestions : []
  const temImagem = params?.mediaType === 'image' && Boolean(params?.hasImageContents)
  const temTexto = String(params?.selectionText || '').trim().length > 0

  const itens = []
  if (palavra) {
    for (const s of sugestoes) {
      const label = String(s || '').trim()
      if (label) itens.push({ role: 'sugestao', label })
    }
    if (itens.length) itens.push({ role: 'separador' })
    itens.push({ role: 'dicionario', label: 'Adicionar ao dicionário' })
  }
  if (temImagem || temTexto) {
    if (itens.length) itens.push({ role: 'separador' })
    itens.push({ role: 'copiar', label: 'Copiar' })
  }
  return itens
}

function idiomasCorretor(disponiveis) {
  const lista = Array.isArray(disponiveis) ? disponiveis : []
  return ['pt-BR', 'en-US'].filter((c) => lista.includes(c))
}

module.exports = { itensMenuContexto, idiomasCorretor }
