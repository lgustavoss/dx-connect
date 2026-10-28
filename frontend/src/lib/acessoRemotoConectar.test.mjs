import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { rotuloSessaoVinculo, urlConexaoDeskRudder } from './acessoRemotoUrl.mjs'

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

  it('usa o caminho connection/new que o cliente Sciter traduz para --connect', () => {
    const url = urlConexaoDeskRudder('142577854', 'abc')
    assert.match(url, /^deskrudder:\/\/connection\/new\/142577854\?password=abc$/)
  })

  it('inclui name= com o rótulo da sessão (vinculo)', () => {
    const url = urlConexaoDeskRudder('1998377577', 'x', 'Posto Farol · SERVIDOR 001')
    assert.equal(
      url,
      'deskrudder://connection/new/1998377577?password=x&name=Posto+Farol+%C2%B7+SERVIDOR+001',
    )
  })
})

describe('rotuloSessaoVinculo', () => {
  it('monta empresa · rótulo código (ignora o nome da rede)', () => {
    assert.equal(
      rotuloSessaoVinculo({
        empresa_nome: 'AUTO POSTO EXPRESSO MEDALHA',
        rede_nome: 'Rede Expresso',
        rotulo_nome: 'SERVIDOR',
        pdv_codigo: '001',
      }),
      'AUTO POSTO EXPRESSO MEDALHA · SERVIDOR 001',
    )
  })

  it('cai na rede se a empresa vier vazia', () => {
    assert.equal(
      rotuloSessaoVinculo({
        rede_nome: 'Posto Farol',
        rotulo_nome: 'SERVIDOR',
        pdv_codigo: '001',
      }),
      'Posto Farol · SERVIDOR 001',
    )
  })

  it('omite prefixo quando empresa e rede vêm vazias', () => {
    assert.equal(
      rotuloSessaoVinculo({ rotulo_nome: 'PDV', pdv_codigo: '02' }),
      'PDV 02',
    )
  })
})
