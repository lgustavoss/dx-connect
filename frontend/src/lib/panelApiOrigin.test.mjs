import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  apiOriginFromPanelHost,
  clientApiOrigin,
  isLegacyRuntimeHost,
  sanitizeBakedApiUrl,
} from './panelApiOrigin.ts'

describe('apiOriginFromPanelHost', () => {
  it('deriva a API do tenant a partir do painel DeskRudder', () => {
    assert.equal(
      apiOriginFromPanelHost('duplexsoft.deskrudder.com.br'),
      'https://api-duplexsoft.deskrudder.com.br',
    )
    assert.equal(
      apiOriginFromPanelHost('posto-farol.deskrudder.com.br'),
      'https://api-posto-farol.deskrudder.com.br',
    )
  })

  it('não deriva na apex, no www, em localhost nem no host da API', () => {
    assert.equal(apiOriginFromPanelHost('deskrudder.com.br'), null)
    assert.equal(apiOriginFromPanelHost('www.deskrudder.com.br'), null)
    assert.equal(apiOriginFromPanelHost('localhost'), null)
    assert.equal(apiOriginFromPanelHost('api.deskrudder.com.br'), null)
    assert.equal(apiOriginFromPanelHost('api-duplexsoft.deskrudder.com.br'), null)
  })

  it('não usa host legado como painel', () => {
    assert.equal(apiOriginFromPanelHost('connect.duplexsoft.com.br'), null)
    assert.equal(apiOriginFromPanelHost('duplexsoft.connect.duplexsoft.com.br'), null)
  })
})

describe('sanitizeBakedApiUrl', () => {
  it('descarta a API legada gravada no build', () => {
    assert.equal(sanitizeBakedApiUrl('https://api.connect.duplexsoft.com.br'), undefined)
    assert.equal(sanitizeBakedApiUrl('https://connect.duplexsoft.com.br/'), undefined)
    assert.equal(isLegacyRuntimeHost('api.connect.duplexsoft.com.br'), true)
  })

  it('mantém API DeskRudder e de outro tenant', () => {
    assert.equal(
      sanitizeBakedApiUrl('https://api-duplexsoft.deskrudder.com.br/'),
      'https://api-duplexsoft.deskrudder.com.br',
    )
    assert.equal(
      sanitizeBakedApiUrl('https://api.deskrudder.com.br'),
      'https://api.deskrudder.com.br',
    )
    assert.equal(clientApiOrigin('codewave'), 'https://api-codewave.deskrudder.com.br')
  })
})
