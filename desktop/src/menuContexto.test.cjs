const { describe, it } = require('node:test')
const assert = require('node:assert/strict')
const { itensMenuContexto, idiomasCorretor } = require('./menuContexto.cjs')

describe('itensMenuContexto', () => {
  it('não abre menu vazio sem seleção nem erro de grafia', () => {
    assert.deepEqual(itensMenuContexto({ selectionText: '', mediaType: 'none' }), [])
  })

  it('só Copiar quando há texto selecionado correto', () => {
    assert.deepEqual(itensMenuContexto({ selectionText: 'ok', mediaType: 'none' }), [
      { role: 'copiar', label: 'Copiar' },
    ])
  })

  it('lista sugestões e dicionário na palavra errada', () => {
    const itens = itensMenuContexto({
      misspelledWord: 'orrtografia',
      dictionarySuggestions: ['ortografia', 'ortográfico'],
      selectionText: 'orrtografia',
      mediaType: 'none',
    })
    assert.equal(itens[0].label, 'ortografia')
    assert.equal(itens[0].role, 'sugestao')
    assert.equal(itens[1].label, 'ortográfico')
    assert.equal(itens[2].role, 'separador')
    assert.equal(itens[3].role, 'dicionario')
    assert.equal(itens[4].role, 'separador')
    assert.equal(itens[itens.length - 1].role, 'copiar')
  })

  it('mostra correção mesmo sem texto selecionado', () => {
    const itens = itensMenuContexto({
      misspelledWord: 'orrtografia',
      dictionarySuggestions: ['ortografia'],
      selectionText: '',
      mediaType: 'none',
    })
    assert.equal(itens[0].role, 'sugestao')
    assert.equal(itens[itens.length - 1].role, 'dicionario')
    assert.equal(itens.some((i) => i.role === 'copiar'), false)
  })
})

describe('idiomasCorretor', () => {
  it('prefere pt-BR e en-US quando o Chromium tem os dois', () => {
    assert.deepEqual(idiomasCorretor(['en-US', 'pt-BR', 'es']), ['pt-BR', 'en-US'])
  })

  it('ignora idioma indisponível', () => {
    assert.deepEqual(idiomasCorretor(['en-US']), ['en-US'])
    assert.deepEqual(idiomasCorretor([]), [])
  })
})
