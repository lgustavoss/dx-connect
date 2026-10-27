const { describe, it } = require('node:test')
const assert = require('node:assert/strict')
const {
  slugDaOrigemPainel,
  montarCorpoSessao,
  origemPainelHttpsInstancia,
} = require('./sessaoDeskRemote.cjs')

describe('slugDaOrigemPainel', () => {
  it('extrai o slug do host do painel', () => {
    assert.equal(
      slugDaOrigemPainel('https://posto-farol.deskrudder.com.br/tickets'),
      'posto-farol',
    )
  })

  it('rejeita host reservado e cai no fallback da conta', () => {
    assert.equal(
      slugDaOrigemPainel('https://www.deskrudder.com.br/', 'posto-farol'),
      'posto-farol',
    )
  })

  it('file:// e URL inválida usam o fallback da conta', () => {
    assert.equal(slugDaOrigemPainel('file:///C:/app/conta.html', 'posto-farol'), 'posto-farol')
    assert.equal(slugDaOrigemPainel('not a url', 'acme'), 'acme')
    assert.equal(slugDaOrigemPainel('not a url', 'www'), null)
  })
})

describe('origemPainelHttpsInstancia', () => {
  it('aceita o subdomínio da instância', () => {
    assert.equal(
      origemPainelHttpsInstancia('https://posto-farol.deskrudder.com.br/login'),
      true,
    )
  })

  it('recusa file, apex, http e host reservado', () => {
    assert.equal(origemPainelHttpsInstancia('file:///C:/app/conta.html'), false)
    assert.equal(origemPainelHttpsInstancia('https://deskrudder.com.br/'), false)
    assert.equal(origemPainelHttpsInstancia('http://posto-farol.deskrudder.com.br/'), false)
    assert.equal(origemPainelHttpsInstancia('https://www.deskrudder.com.br/'), false)
  })
})

describe('montarCorpoSessao', () => {
  it('grava slug + access e omite refresh vazio', () => {
    assert.deepEqual(montarCorpoSessao('Acme', ' tok ', '  '), {
      slug: 'acme',
      access_token: 'tok',
    })
  })

  it('inclui refresh quando há', () => {
    assert.deepEqual(montarCorpoSessao('acme', 'a', 'r'), {
      slug: 'acme',
      access_token: 'a',
      refresh_token: 'r',
    })
  })

  it('recusa slug reservado, token vazio ou token enorme', () => {
    assert.equal(montarCorpoSessao('www', 'tok'), null)
    assert.equal(montarCorpoSessao('acme', '  '), null)
    assert.equal(montarCorpoSessao('acme', 'x'.repeat(16001)), null)
  })
})
