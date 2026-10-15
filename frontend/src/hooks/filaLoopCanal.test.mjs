import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  aoIniciarWebAudio,
  htmlDevePararPorqueWebAssumiu,
  podeIniciarHtml,
} from './filaLoopCanal.mjs'

describe('alerta da fila — um canal por vez', () => {
  it('silencia o HTML antes do Web Audio, mesmo com play() ainda pendente', () => {
    assert.deepEqual(aoIniciarWebAudio({ htmlExiste: true }), { silenciarHtml: true })
  })

  it('não tenta silenciar o HTML se o elemento ainda não existe', () => {
    assert.deepEqual(aoIniciarWebAudio({ htmlExiste: false }), { silenciarHtml: false })
  })

  it('não inicia o HTML se o Web Audio tocou, está tocando ou ainda está começando', () => {
    const base = { webOk: false, webTocando: false, webComecando: false, wanted: true, muted: false }
    assert.equal(podeIniciarHtml({ ...base, webOk: true }), false)
    assert.equal(podeIniciarHtml({ ...base, webTocando: true }), false)
    assert.equal(podeIniciarHtml({ ...base, webComecando: true }), false)
  })

  it('inicia o HTML só quando o Web Audio não assumiu o alerta', () => {
    assert.equal(
      podeIniciarHtml({
        webOk: false,
        webTocando: false,
        webComecando: false,
        wanted: true,
        muted: false,
      }),
      true,
    )
  })

  it('não inicia o HTML com a fila muda ou sem pedido de loop', () => {
    const base = { webOk: false, webTocando: false, webComecando: false, wanted: true, muted: false }
    assert.equal(podeIniciarHtml({ ...base, muted: true }), false)
    assert.equal(podeIniciarHtml({ ...base, wanted: false }), false)
  })

  it('pede para parar o HTML se o play() resolver depois que o Web Audio assumiu', () => {
    assert.equal(htmlDevePararPorqueWebAssumiu(true), true)
    assert.equal(htmlDevePararPorqueWebAssumiu(false), false)
  })
})
