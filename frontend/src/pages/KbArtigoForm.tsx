import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, kb, type Kb } from '../api/client'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { FormSection } from '../components/ui/FormSection'
import { CadastroFormPageShell } from '../components/ui/CadastroFormPageShell'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'

export function KbArtigoForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/base-conhecimento')

  const artigoId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)
  const [categorias, setCategorias] = useState<Kb.Category[]>([])
  const [titulo, setTitulo] = useState('')
  const [slug, setSlug] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [conteudo, setConteudo] = useState('')
  const [status, setStatus] = useState('rascunho')

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
        setStatus(item.status)
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

  async function salvar() {
    if (!titulo.trim()) {
      toast.showError('Informe o título.')
      return
    }
    setSaving(true)
    const payload = {
      titulo: titulo.trim(),
      slug: slug.trim() || undefined,
      category_id: categoryId ? Number(categoryId) : null,
      conteudo_markdown: conteudo,
    }
    try {
      if (isEdit && !Number.isNaN(artigoId)) {
        await kb.updateArticle(artigoId, payload)
        toast.showSuccess('Artigo salvo.')
      } else {
        const created = await kb.createArticle(payload)
        toast.showSuccess('Rascunho criado.')
        navigate(`/base-conhecimento/${created.id}/editar`, { replace: true })
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
      await kb.updateArticle(artigoId, {
        titulo: titulo.trim(),
        slug: slug.trim() || undefined,
        category_id: categoryId ? Number(categoryId) : null,
        conteudo_markdown: conteudo,
      })
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
    if (!window.confirm('Arquivar este artigo? Ele deixará de aparecer na consulta interna.')) return
    setSaving(true)
    try {
      const arq = await kb.archiveArticle(artigoId)
      setStatus(arq.status)
      toast.showSuccess('Artigo arquivado.')
      navigate('/base-conhecimento')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível arquivar.'))
    } finally {
      setSaving(false)
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Sem permissão para editar artigos."
        voltarPara="/base-conhecimento"
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
        className="mx-auto max-w-5xl space-y-4 pb-10"
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
          Markdown simples na v1 — salve rascunho ou publique quando estiver pronto.
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
              options={categorias.map((c) => ({ value: String(c.id), label: c.nome }))}
              includeEmpty
              emptyLabel="Sem categoria"
              placeholder="Sem categoria"
            />
            {isEdit ? (
              <Input label="Status" value={status} readOnly disabled className="opacity-80" />
            ) : null}
          </div>
        </FormSection>

        <FormSection title="Conteúdo (Markdown)">
          <textarea
            className="min-h-[280px] w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-sm text-slate-800 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            value={conteudo}
            onChange={(e) => setConteudo(e.target.value)}
            placeholder="# Título do manual&#10;&#10;Descreva o procedimento..."
          />
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
    </CadastroFormPageShell>
  )
}