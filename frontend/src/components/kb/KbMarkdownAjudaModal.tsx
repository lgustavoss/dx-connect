import { useEffect } from 'react'
import { Button } from '../ui/Button'
import { useToast } from '../ui/Toast'
import { MODAL_OVERLAY, MODAL_PANEL_WIDE_SHELL } from '../../lib/modalPanel'
import { KbMarkdownPreview } from './KbMarkdownPreview'

type ExemploMarkdown = {
  titulo: string
  sintaxe: string
  descricao: string
}

const EXEMPLOS: ExemploMarkdown[] = [
  {
    titulo: 'Título principal',
    sintaxe: '# Título do manual',
    descricao: 'Use um # para o título principal do artigo.',
  },
  {
    titulo: 'Subtítulo',
    sintaxe: '## Passo a passo',
    descricao: 'Dois ou três # criam seções menores.',
  },
  {
    titulo: 'Negrito',
    sintaxe: '**texto importante**',
    descricao: 'Destaque palavras ou frases.',
  },
  {
    titulo: 'Itálico',
    sintaxe: '*observação*',
    descricao: 'Ênfase leve ou termos técnicos.',
  },
  {
    titulo: 'Lista com marcadores',
    sintaxe: '- Primeiro item\n- Segundo item\n- Terceiro item',
    descricao: 'Cada linha começa com hífen e espaço.',
  },
  {
    titulo: 'Lista numerada',
    sintaxe: '1. Abra o sistema\n2. Clique em Salvar\n3. Confirme a operação',
    descricao: 'Ideal para procedimentos em sequência.',
  },
  {
    titulo: 'Link',
    sintaxe: '[Central de ajuda](https://exemplo.com/ajuda)',
    descricao: 'Texto clicável entre colchetes + URL entre parênteses.',
  },
  {
    titulo: 'Código inline',
    sintaxe: 'Pressione o botão `Confirmar`',
    descricao: 'Use crases para comandos, campos ou atalhos.',
  },
  {
    titulo: 'Bloco de código',
    sintaxe: '```\nSELECT * FROM clientes;\n```',
    descricao: 'Três crases antes e depois do bloco.',
  },
  {
    titulo: 'Citação',
    sintaxe: '> Atenção: faça backup antes de alterar cadastros.',
    descricao: 'Destaque avisos ou observações importantes.',
  },
  {
    titulo: 'Linha separadora',
    sintaxe: '---',
    descricao: 'Separe seções com uma linha horizontal.',
  },
]

const EXEMPLO_COMPLETO = `# Cadastro de clientes

Siga os passos abaixo para incluir um novo cliente.

## Pré-requisitos

- Acesso ao menu **Clientes**
- Permissão de *cadastro*

## Procedimento

1. Clique em **Novo cliente**
2. Preencha os campos obrigatórios
3. Pressione \`Salvar\`

> **Atenção:** confira o CNPJ antes de confirmar.

---

[Dúvidas? Abra um ticket](https://exemplo.com/suporte)
`

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function gerarHtmlGuiaMarkdown(): string {
  const linhas = EXEMPLOS.map(
    (e) =>
      `<section><h3>${escapeHtml(e.titulo)}</h3><p>${escapeHtml(e.descricao)}</p><pre><code>${escapeHtml(e.sintaxe)}</code></pre></section>`,
  ).join('')

  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Guia Markdown — Base de conhecimento</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 64rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #0f172a; }
    h1 { font-size: 1.5rem; }
    h3 { margin: 1.5rem 0 0.25rem; font-size: 1rem; }
    p { color: #475569; margin: 0.25rem 0 0.5rem; }
    pre { background: #f1f5f9; padding: 0.75rem 1rem; border-radius: 0.5rem; overflow-x: auto; font-size: 0.85rem; white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>Guia rápido de Markdown</h1>
  <p>Comandos mais usados nos manuais da base de conhecimento.</p>
  ${linhas}
  <section>
    <h3>Exemplo completo</h3>
    <pre><code>${escapeHtml(EXEMPLO_COMPLETO)}</code></pre>
  </section>
</body>
</html>`
}

export function abrirGuiaMarkdownNovaAba(): boolean {
  const blob = new Blob([gerarHtmlGuiaMarkdown()], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const win = window.open(url, '_blank', 'noopener,noreferrer')
  if (!win) {
    URL.revokeObjectURL(url)
    return false
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
  return true
}

type Props = {
  open: boolean
  onClose: () => void
  onInserir?: (snippet: string) => void
}

export function KbMarkdownAjudaModal({ open, onClose, onInserir }: Props) {
  const toast = useToast()

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  function abrirNovaAba() {
    if (!abrirGuiaMarkdownNovaAba()) {
      toast.showWarning('Não foi possível abrir nova aba. Verifique se o navegador bloqueou pop-ups.')
    }
  }

  if (!open) return null

  return (
    <div
      className={MODAL_OVERLAY}
      role="dialog"
      aria-modal="true"
      aria-labelledby="kb-markdown-ajuda-title"
      onClick={onClose}
    >
      <div className={MODAL_PANEL_WIDE_SHELL} onClick={(e) => e.stopPropagation()}>
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-700">
          <div>
            <h2 id="kb-markdown-ajuda-title" className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              Guia de formatação
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Atalhos para negrito, listas, links e outros recursos. Use <strong>Visualizar</strong> no editor para
              conferir o resultado.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Button type="button" variant="secondary" onClick={abrirNovaAba}>
              Abrir em nova aba
            </Button>
            <Button type="button" variant="secondary" onClick={onClose}>
              Fechar
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <ul className="space-y-4">
            {EXEMPLOS.map((item) => (
              <li
                key={item.titulo}
                className="rounded-xl border border-slate-200/90 bg-slate-50/70 p-4 dark:border-slate-700/80 dark:bg-slate-900/40"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.titulo}</h3>
                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{item.descricao}</p>
                    <pre className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-xs text-slate-800 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                      {item.sintaxe}
                    </pre>
                  </div>
                  {onInserir ? (
                    <Button type="button" variant="secondary" onClick={() => onInserir(item.sintaxe)}>
                      Inserir
                    </Button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>

          <div className="mt-6 rounded-xl border border-cyan-200/80 bg-cyan-50/40 p-4 dark:border-cyan-900/50 dark:bg-cyan-950/20">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Exemplo completo</h3>
              {onInserir ? (
                <Button type="button" variant="secondary" onClick={() => onInserir(EXEMPLO_COMPLETO)}>
                  Inserir modelo
                </Button>
              ) : null}
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <pre className="max-h-64 overflow-auto rounded-lg border border-slate-200 bg-white p-3 font-mono text-xs text-slate-800 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                {EXEMPLO_COMPLETO}
              </pre>
              <div className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-950/60">
                <KbMarkdownPreview markdown={EXEMPLO_COMPLETO} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
