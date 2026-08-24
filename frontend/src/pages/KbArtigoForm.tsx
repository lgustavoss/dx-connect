import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, kb, resolvedApiBaseUrl, type Kb } from '../api/client'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Button } from '../components/ui/Button'
import { CheckboxField } from '../components/ui/CheckboxField'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { FormSection } from '../components/ui/FormSection'
import { CadastroFormPageShell } from '../components/ui/CadastroFormPageShell'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { kbCategoriasOpcoesSelect } from '../lib/kbCategorias'
import { KbMarkdownPreview } from '../components/kb/KbMarkdownPreview'
import { KbMarkdownAjudaModal } from '../components/kb/KbMarkdownAjudaModal'
import { KbArtigoHistoricoModal } from '../components/kb/KbArtigoHistoricoModal'
import {
  draftFromApiLinks,
  draftToApiLinks,
  KbArtigoMotivoLinksFields,
  type MotivoLinkDraft,
} from '../components/kb/KbArtigoMotivoLinksFields'

type ModoConteudo = 'editar' | 'visualizar'

export function KbArtigoForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/ajuda/artigos')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const artigoId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [uploadingImage, setUploadingImage] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)
  const [categorias, setCategorias] = useState<Kb.Category[]>([])
  const [titulo, setTitulo] = useState('')
  const [slug, setSlug] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [conteudo, setConteudo] = useState('')
  const [internoOnly, setInternoOnly] = useState(false)
  const [status, setStatus] = useState('rascunho')
  const [modoConteudo, setModoConteudo] = useState<ModoConteudo>('editar')
  const [ajudaMarkdownOpen, setAjudaMarkdownOpen] = useState(false)
  const [historicoOpen, setHistoricoOpen] = useState(false)
  const [versoes, setVersoes] = useState<Kb.ArticleVersion[]>([])
  const [loadingVersoes, setLoadingVersoes] = useState(false)
  const [versaoSelecionada, setVersaoSelecionada] = useState<Kb.ArticleVersionDetail | null>(null)
  const [loadingVersao, setLoadingVersao] = useState(false)
  const [motivoLinks, setMotivoLinks] = useState<MotivoLinkDraft[]>([])
  const [feedbackUtil, setFeedbackUtil] = useState(0)
  const [feedbackNaoUtil, setFeedbackNaoUtil] = useState(0)

  useEffect(() => {
    kb.listCategories()
      .then(setCategorias)
      .catch(() => setCategorias([]))
  }, [])

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(artigoId)) {
      setInexistente({ detalhe: 'Identificador inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    kb.getArticle(artigoId)
      .then((item) => {
        if (cancelled) return
        setTitulo(item.titulo)
        setSlug(item.slug)
        setCategoryId(item.category_id != null ? String(item.category_id) : '')
        setConteudo(item.conteudo_markdown)
        setInternoOnly(item.interno_only)
        setStatus(item.status)
        setFeedbackUtil(item.feedback_util_count ?? 0)
        setFeedbackNaoUtil(item.feedback_nao_util_count ?? 0)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setInexistente({})
          return
        }
        toast.showWarning(interpretarFalhaCarregamento(err, 'Artigo não encontrado.').titulo)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [artigoId, id, isEdit, toast])

  useEffect(() => {
    if (!isEdit || Number.isNaN(artigoId)) return
    let cancelled = false
    kb.listArticleMotivoLinks(artigoId)
      .then((rows) => {
        if (!cancelled) setMotivoLinks(draftFromApiLinks(rows))
      })
      .catch(() => {
        if (!cancelled) setMotivoLinks([])
      })
    return () => {
      cancelled = true
    }
  }, [artigoId, isEdit])

  async function salvarMotivoLinks(articleId: number) {
    await kb.updateArticleMotivoLinks(articleId, draftToApiLinks(motivoLinks))
  }

  function artigoPayload() {
    return {
      titulo: titulo.trim(),
      slug: slug.trim() || undefined,
      category_id: categoryId ? Number(categoryId) : null,
      conteudo_markdown: conteudo,
      interno_only: internoOnly,
    }
  }

  async function salvar() {
    if (!titulo.trim()) {
      toast.showError('Informe o título.')
      return
    }
    setSaving(true)
    try {
      if (isEdit && !Number.isNaN(artigoId)) {
        await kb.updateArticle(artigoId, artigoPayload())
        await salvarMotivoLinks(artigoId)
        toast.showSuccess('Artigo salvo.')
      } else {
        const created = await kb.createArticle(artigoPayload())
        toast.showSuccess('Rascunho criado.')
        navigate(`/ajuda/artigos/${created.id}/editar`, { replace: true })
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setSaving(false)
    }
  }

  async function publicar() {
    if (!isEdit || Number.isNaN(artigoId)) {
      await salvar()
      return
    }
    setSaving(true)
    try {
      await kb.updateArticle(artigoId, artigoPayload())
      await salvarMotivoLinks(artigoId)
      const pub = await kb.publishArticle(artigoId)
      setStatus(pub.status)
      toast.showSuccess('Artigo publicado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível publicar.'))
    } finally {
      setSaving(false)
    }
  }

  async function arquivar() {
    if (!isEdit || Number.isNaN(artigoId)) return
    if (!window.confirm('Arquivar este manual? Ele deixará de aparecer nas buscas de Ajuda.')) return
    setSaving(true)
    try {
      const arq = await kb.archiveArticle(artigoId)
      setStatus(arq.status)
      toast.showSuccess('Artigo arquivado.')
      navigate('/ajuda/artigos')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível arquivar.'))
    } finally {
      setSaving(false)
    }
  }

  function inserirSnippetMarkdown(snippet: string) {
    const sep = conteudo && !conteudo.endsWith('\n') ? '\n\n' : conteudo ? '' : ''
    setConteudo(conteudo + sep + snippet)
    setModoConteudo('editar')
    toast.showSuccess('Exemplo inserido no editor.')
  }

  function inserirNoCursor(texto: string) {
    const el = textareaRef.current
    if (!el) {
      setConteudo((c) => c + texto)
      return
    }
    const start = el.selectionStart
    const end = el.selectionEnd
    const next = conteudo.slice(0, start) + texto + conteudo.slice(end)
    setConteudo(next)
    requestAnimationFrame(() => {
      el.focus()
      const pos = start + texto.length
      el.setSelectionRange(pos, pos)
    })
  }

  async function onSelecionarImagem(file: File | null) {
    if (!file) return
    setUploadingImage(true)
    try {
      const res = await kb.uploadImage(file)
      const url = res.url.startsWith('http') ? res.url : `${resolvedApiBaseUrl()}${res.url}`
      const alt = file.name.replace(/\.[^.]+$/, '') || 'imagem'
      inserirNoCursor(`\n![${alt}](${url})\n`)
      setModoConteudo('editar')
      toast.showSuccess('Imagem inserida no texto.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar a imagem.'))
    } finally {
      setUploadingImage(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function abrirHistorico() {
    if (!isEdit || Number.isNaN(artigoId)) return
    setHistoricoOpen(true)
    setVersaoSelecionada(null)
    setLoadingVersoes(true)
    try {
      const rows = await kb.listArticleVersions(artigoId)
      setVersoes(rows)
      if (rows.length > 0) await carregarVersao(rows[0].id)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o histórico.'))
    } finally {
      setLoadingVersoes(false)
    }
  }

  async function carregarVersao(versionId: number) {
    if (Number.isNaN(artigoId)) return
    setLoadingVersao(true)
    try {
      const v = await kb.getArticleVersion(artigoId, versionId)
      setVersaoSelecionada(v)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Versão não encontrada.'))
    } finally {
      setLoadingVersao(false)
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Sem permissão para editar artigos."
        voltarPara="/ajuda/artigos"
        voltarLabel="Voltar"
      />
    )
  }

  if (loading) {
    return (
      <CadastroFormPageShell onVoltar={voltarAnterior}>
        <div className="h-72 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </CadastroFormPageShell>
    )
  }

  if (inexistente) {
    return (
      <CarregamentoFalhou
        className="mx-auto w-full min-w-0 max-w-5xl space-y-4 pb-10"
        titulo="Artigo não encontrado."
        detalhe={inexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <Card title={isEdit ? 'Editar artigo' : 'Novo artigo'}>
        <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
          Escreva o conteúdo do manual, salve como rascunho ou publique quando estiver pronto.
        </p>
        <FormSection title="Identificação">
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Título" value={titulo} onChange={(e) => setTitulo(e.target.value)} required />
            <Input
              label="Slug (opcional)"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="gerado automaticamente"
            />
            <Select
              label="Categoria"
              value={categoryId}
              onChange={(v) => setCategoryId(typeof v === 'string' ? v : String(v))}
              options={kbCategoriasOpcoesSelect(categorias)}
              includeEmpty
              emptyLabel="Sem categoria"
              placeholder="Sem categoria"
            />
            {isEdit ? (
              <Input label="Status" value={status} readOnly disabled className="opacity-80" />
            ) : null}
          </div>
          <div className="mt-4 space-y-1">
            <CheckboxField checked={internoOnly} onChange={(e) => setInternoOnly(e.target.checked)}>
              Apenas para a equipe
            </CheckboxField>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Manuais marcados assim ficam visíveis só para atendentes no menu Ajuda. Clientes não veem na central de
              ajuda.
            </p>
          </div>
        </FormSection>

        {isEdit && status === 'publicado' && !internoOnly ? (
          <FormSection title="Avaliações do portal">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Visitantes da central de ajuda podem marcar se o manual foi útil.
            </p>
            <div className="mt-3 flex flex-wrap gap-6 text-sm">
              <div>
                <span className="font-semibold text-teal-700 dark:text-teal-400">{feedbackUtil}</span>
                <span className="ml-1 text-slate-600 dark:text-slate-400">úteis</span>
              </div>
              <div>
                <span className="font-semibold text-slate-700 dark:text-slate-300">{feedbackNaoUtil}</span>
                <span className="ml-1 text-slate-600 dark:text-slate-400">não úteis</span>
              </div>
            </div>
          </FormSection>
        ) : null}

        {isEdit ? (
          <FormSection title="Sugestões por classificação">
            <KbArtigoMotivoLinksFields
              links={motivoLinks}
              onChange={setMotivoLinks}
              disabled={status === 'arquivado' || saving}
            />
          </FormSection>
        ) : null}

        <FormSection title="Conteúdo do manual">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant={modoConteudo === 'editar' ? undefined : 'secondary'}
              onClick={() => setModoConteudo('editar')}
            >
              Editar
            </Button>
            <Button
              type="button"
              variant={modoConteudo === 'visualizar' ? undefined : 'secondary'}
              onClick={() => setModoConteudo('visualizar')}
            >
              Visualizar
            </Button>
            <span className="hidden h-6 w-px bg-slate-200 sm:inline dark:bg-slate-700" aria-hidden />
            <Button type="button" variant="secondary" onClick={() => setAjudaMarkdownOpen(true)}>
              Guia de formatação
            </Button>
            <Button type="button" variant="secondary" loading={uploadingImage} onClick={() => fileInputRef.current?.click()}>
              Inserir imagem
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              className="hidden"
              onChange={(e) => void onSelecionarImagem(e.target.files?.[0] ?? null)}
            />
            {isEdit ? (
              <Button type="button" variant="secondary" onClick={() => void abrirHistorico()}>
                Histórico
              </Button>
            ) : null}
          </div>
          {modoConteudo === 'editar' ? (
            <textarea
              ref={textareaRef}
              className="min-h-[280px] w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-sm text-slate-800 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
              value={conteudo}
              onChange={(e) => setConteudo(e.target.value)}
              placeholder="# Título do manual&#10;&#10;Descreva o procedimento..."
            />
          ) : (
            <div className="min-h-[280px] rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/50">
              <KbMarkdownPreview markdown={conteudo} emptyLabel="Nada para visualizar ainda — escreva o conteúdo do manual." />
            </div>
          )}
        </FormSection>

        <div className="flex flex-wrap gap-2">
          <Button type="button" loading={saving} onClick={salvar}>
            Salvar rascunho
          </Button>
          <Button type="button" variant="secondary" loading={saving} onClick={publicar} disabled={status === 'arquivado'}>
            Publicar
          </Button>
          {isEdit && status !== 'arquivado' ? (
            <Button type="button" variant="secondary" loading={saving} onClick={arquivar}>
              Arquivar
            </Button>
          ) : null}
        </div>
      </Card>

      <KbMarkdownAjudaModal
        open={ajudaMarkdownOpen}
        onClose={() => setAjudaMarkdownOpen(false)}
        onInserir={(snippet) => {
          inserirSnippetMarkdown(snippet)
          setAjudaMarkdownOpen(false)
        }}
      />

      {isEdit ? (
        <KbArtigoHistoricoModal
          open={historicoOpen}
          onClose={() => setHistoricoOpen(false)}
          articleId={artigoId}
          versions={versoes}
          loading={loadingVersoes}
          onSelectVersion={(vid) => void carregarVersao(vid)}
          selectedVersion={versaoSelecionada}
          loadingVersion={loadingVersao}
        />
      ) : null}
    </CadastroFormPageShell>
  )
}
