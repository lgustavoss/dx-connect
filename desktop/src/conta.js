const form = document.getElementById('form')
const input = document.getElementById('slug')
const erro = document.getElementById('erro')
const botao = document.getElementById('entrar')

if (new URLSearchParams(location.search).get('erro') === 'conexao') {
  erro.textContent = 'Não foi possível abrir o painel. Verifique a internet e clique em Continuar.'
}

void window.deskrudder.contaAtual().then((slug) => {
  if (slug && !input.value) input.value = slug
})

form.addEventListener('submit', async (ev) => {
  ev.preventDefault()
  botao.disabled = true
  botao.textContent = 'Verificando…'
  erro.textContent = ''
  try {
    const res = await window.deskrudder.definirConta(input.value)
    if (!res.ok) erro.textContent = res.erro
  } catch {
    erro.textContent = 'Algo deu errado. Tente de novo.'
  } finally {
    botao.disabled = false
    botao.textContent = 'Continuar'
  }
})
