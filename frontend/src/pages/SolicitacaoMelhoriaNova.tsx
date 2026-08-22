import { useEffect, useRef, useState, type ClipboardEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { solicitacoesMelhoria, system, type SolicitacoesMelhoria } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { KbMarkdownAjudaModal } from '../components/kb/KbMarkdownAjudaModal'
import { KbMarkdownPreview } from '../components/kb/KbMarkdownPreview'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { PageContainer } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'

const ACCEPT_ANEXO = 'image/png,image/jpeg,image/webp,image/gif,application/pdf,video/mp4,video/webm,video/quicktime'
const MAX_ANEXOS = 20

function inserirNoCursor(
  el: HTMLTextAreaElement | null,
  snippet: string,
  fallback: string,
  setValue: (v: string) => void,
) {
  const value = el?.value ?? fallback
  if (!el) {
    setValue(value + snippet)
    return
  }
  const start = el.selectionStart
  const end = el.selectionEnd
  const next = value.slice(0, start) + snippet + value.slice(end)
  setValue(next)
  requestAnimationFrame(() => {
    el.focus()
    const pos = start + snippet.length
    el.setSelectionRange(pos, pos)
  })
}

export function SolicitacaoMelhoriaNovaPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [params] = useSearchParams()
  const tipoParam = params.get('tipo') === 'problema' ? 'problema' : 'sugestao'

  const [tipo, setTipo] = useState<SolicitacoesMelhoria.Tipo>(tipoParam)
  const [titulo, setTitulo] = useState('')
  const [descricao, setDescricao] = useState('')
  const [versao, setVersao] = useState<string | null>(null)
  const [anexos, setAnexos] = useState<SolicitacoesMelhoria.Anexo[]>([])
  const [modo, setModo] = useState<'editar' | 'visualizar'>('editar')
  const [enviando, setEnviando] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [ajudaMarkdown, setAjudaMarkdown] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const anexoInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setTipo(tipoParam)
  }, [tipoParam])

  useEffect(() => {
    void system
      .info()
      .then((i) => setVersao(i.version_display || i.version || null))
      .catch(() => undefined)
  }, [])

  async function enviarFicheiro(file: File, papel: 'inline' | 'anexo') {
    if (anexos.length >= MAX_ANEXOS) {
      toast.showError('Pode anexar no máximo 20 ficheiros neste pedido.')
      return
    }
    setUploading(true)
    try {
      const row = await solicitacoesMelhoria.uploadMedia(file, papel)
      setAnexos((cur) => [...cur, row])
      if (papel === 'inline') {
        const alt = file.name.replace(/\.[^.]+$/, '') || 'print'
        inserirNoCursor(textareaRef.current, `\n![${alt}](${row.url})\n`, descricao, setDescricao)
        setModo('editar')
        toast.showSuccess('Imagem colada no texto.')
      } else {
        toast.showSuccess('Ficheiro anexado.')
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar o ficheiro.'))
    } finally {
      setUploading(false)
      if (anexoInputRef.current) anexoInputRef.current.value = ''
    }
  }

  function onPaste(e: ClipboardEvent<HTMLTextAreaElement>) {
    const items = e.clipboardData?.items
    if (!items) return
    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile()
        if (file) {
          e.preventDefault()
          void enviarFicheiro(file, 'inline')
        }
        return
      }
    }
  }

  function inserirMarkdown(snippet: string) {
    setModo('editar')
    inserirNoCursor(textareaRef.current, snippet, descricao, setDescricao)
    setAjudaMarkdown(false)
    toast.showSuccess('Marcação inserida no texto.')
  }

  async function enviar() {
    setErro(null)
    const t = titulo.trim()
    const d = descricao.trim()
    if (t.length < 3) {
      setErro('Indique um título com pelo menos 3 caracteres.')
      return
    }
    if (d.length < 10) {
      setErro('Descreva o pedido com pelo menos 10 caracteres.')
      return
    }
    setEnviando(true)
    try {
      const row = await solicitacoesMelhoria.criar({
        tipo,
        titulo: t,
        descricao: d,
        versao_contexto: versao,
        anexo_ids: anexos.map((a) => a.id),
      })
      toast.showSuccess('Pedido enviado. Pode acompanhar em Minhas solicitações.')
      navigate(`/minhas-solicitacoes/${row.id}`)
    } catch (err) {
      const msg = mensagemFalhaParaToast(err, 'Não foi possível enviar o pedido.')
      setErro(msg)
      toast.showError(msg)
    } finally {
      setEnviando(false)
    }
  }

  const anexosLista = anexos.filter((a) => a.papel !== 'inline')

  return (
    <PageContainer className="flex h-full min-h-0 w-full flex-col" spacing="none">
      <div className="shrink-0">
        <Link
          to="/sobre"
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <span aria-hidden>←</span> Voltar a Sobre / novidades
        </Link>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          {tipo === 'problema' ? 'Relatar um problema' : 'Enviar sugestão'}
        </h1>
      </div>

      <div className="mt-6 flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/95 dark:shadow-none dark:ring-1 dark:ring-white/5">
        <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-hidden p-5 sm:p-6">
          <div className="grid shrink-0 items-start gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,3fr)]">
            <Select
              label="Tipo"
              className="[&>button]:box-border [&>button]:h-10 [&>button]:rounded-lg [&>button]:py-0"
              value={tipo}
              onChange={(v) => setTipo(String(v) as SolicitacoesMelhoria.Tipo)}
              options={[
                { value: 'sugestao', label: 'Sugestão de melhoria' },
                { value: 'problema', label: 'Relatar problema' },
              ]}
            />
            <Input
              label="Título"
              className="box-border h-10"
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder="Resumo em poucas palavras"
              maxLength={200}
            />
          </div>

          <div className="flex min-h-0 flex-1 flex-col">
            <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-700 dark:text-slate-300">
                Descrição
                <button
                  type="button"
                  className="inline-flex size-5 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-cyan-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-cyan-400"
                  aria-label="Guia de formatação da descrição"
                  title="Guia de formatação"
                  onClick={() => setAjudaMarkdown(true)}
                >
                  <svg className="size-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </span>
              <div
                className="relative inline-grid grid-cols-2 rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-800 dark:bg-slate-900/70"
                role="radiogroup"
                aria-label="Modo da descrição"
              >
                <span
                  aria-hidden
                  className={`pointer-events-none absolute inset-y-1 left-1 w-[calc(50%-4px)] rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 shadow-sm shadow-cyan-500/20 transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                    modo === 'visualizar' ? 'translate-x-full' : 'translate-x-0'
                  }`}
                />
                {(
                  [
                    { value: 'editar', label: 'Edição' },
                    { value: 'visualizar', label: 'Visualização' },
                  ] as const
                ).map((opt) => {
                  const ativo = modo === opt.value
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      role="radio"
                      aria-checked={ativo}
                      onClick={() => setModo(opt.value)}
                      className={`relative z-10 inline-flex items-center justify-center rounded-lg px-4 py-1.5 text-sm font-medium transition-colors duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                        ativo
                          ? 'text-slate-950'
                          : 'text-slate-600 hover:text-slate-800 dark:text-slate-300 dark:hover:text-slate-100'
                      }`}
                    >
                      {opt.label}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-300 dark:border-slate-600">
              {modo === 'editar' ? (
                <textarea
                  ref={textareaRef}
                  className="min-h-0 w-full flex-1 resize-none bg-transparent px-3 py-2.5 text-sm leading-relaxed text-slate-900 placeholder:text-slate-400 focus:outline-none dark:text-slate-100 dark:placeholder:text-slate-500"
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  onPaste={onPaste}
                  placeholder="Explique o contexto, o que esperava e o impacto. Cole prints (Ctrl+V) à medida que descreve os passos."
                  maxLength={20000}
                />
              ) : (
                <div className="min-h-0 flex-1 overflow-y-auto px-3 py-2.5">
                  <KbMarkdownPreview markdown={descricao} emptyLabel="Nada para visualizar ainda." />
                </div>
              )}
            </div>
          </div>

          {anexosLista.length > 0 ? (
            <ul className="shrink-0 space-y-1 text-sm text-slate-600 dark:text-slate-300">
              {anexosLista.map((a) => (
                <li key={a.id}>Anexo: {a.nome_original}</li>
              ))}
            </ul>
          ) : null}

          {erro ? <p className="shrink-0 text-sm text-rose-600 dark:text-rose-400">{erro}</p> : null}
        </div>

        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-white px-5 pt-3 dark:border-slate-800 dark:bg-slate-900/95 sm:px-6 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              loading={uploading}
              onClick={() => anexoInputRef.current?.click()}
            >
              Anexar
            </Button>
            <input
              ref={anexoInputRef}
              type="file"
              accept={ACCEPT_ANEXO}
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) void enviarFicheiro(f, 'anexo')
              }}
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="danger" onClick={() => navigate('/sobre')} disabled={enviando}>
              Cancelar
            </Button>
            <Button type="button" variant="primary" loading={enviando || uploading} onClick={() => void enviar()}>
              Enviar
            </Button>
          </div>
        </div>
      </div>

      <KbMarkdownAjudaModal
        open={ajudaMarkdown}
        onClose={() => setAjudaMarkdown(false)}
        onInserir={inserirMarkdown}
      />
    </PageContainer>
  )
}
