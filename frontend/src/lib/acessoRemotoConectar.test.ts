import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { urlConexaoDeskRudder } from './acessoRemotoUrl.ts'

describe('urlConexaoDeskRudder', () => {
  it('monta o protocolo DeskRudder com ID sem espaços', () => {
    assert.equal(urlConexaoDeskRudder('131 516 031'), 'deskrudder://connection/new/131516031')
  })

  it('codifica senha com # e @ na query', () => {
    assert.equal(
      urlConexaoDeskRudder('131516031', '#@jjB1312'),
      'deskrudder://connection/new/131516031?password=%23%40jjB1312',
    )
  })

  it('usa o caminho connection/new que o cliente Sciter 1.0.8 traduz para --connect', () => {
    const url = urlConexaoDeskRudder('142577854', 'abc')
    assert.match(url, /^deskrudder:\/\/connection\/new\/142577854\?password=abc$/)
  })
})
