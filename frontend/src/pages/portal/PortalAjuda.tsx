import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { kbPublic, type Kb } from '../../api/client'
import { KbMarkdownPreview } from '../../components/kb/KbMarkdownPreview'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useToast } from '../../components/ui/Toast'
import { PortalPageHeader, portalCardClass, portalInputClass } from './portalUi'

export function PortalAjudaHome() {
  const [busca, setBusca] = useState('')
  const [buscaDebounced, setBuscaDebounced] = useState('')
  const [categorias, setCategorias] = useState<Kb.Category[]>([])
  const [artigos, setArtigos] = useState<Kb.ArticleBrief[]>([])
  const [loading, setLoading] = useState(true)
  const toast = useToast()

  useEffect(() => {
    const t = window.setTimeout(() => setBuscaDebounced(busca.trim()), 300)
    return () => window.clearTimeout(t)
  }, [busca])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      kbPublic.listCategories(),
      kbPublic.listArticles({ busca: buscaDebounced || undefined, limit: 40 }),
    ])
      .then(([cats, arts]) => {
        if (cancelled) return
        setCategorias(cats)
        setArtigos(arts)
      })
      .catch((err) => {
        if (!cancelled) toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar a ajuda.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [buscaDebounced, toast])

  return (
    <div className="space-y-6">
      <PortalPageHeader
        title="Central de ajuda"
        subtitle="Consulte manuais e artigos antes de abrir um chamado."
      />

      <input
        type="search"
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        placeholder="Buscar artigos…"
        className={portalInputClass}
      />

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-slate-200/60" />
          ))}
        </div>
      ) : (
        <>
          {categorias.length > 0 && !buscaDebounced ? (
            <div className="flex flex-wrap gap-2">
              {categorias.map((c) => (
                <span
                  key={c.id}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200/80"
                >
                  {c.nome}
                </span>
              ))}
            </div>
          ) : null}

          {artigos.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-10 text-center text-sm text-slate-500">
              Nenhum artigo encontrado.
            </div>
          ) : (
            <ul className="space-y-2">
              {artigos.map((a) => (
                <li key={a.id}>
                  <Link to={`/portal/ajuda/${a.slug}`} className={`block ${portalCardClass}`}>
                    <p className="font-medium text-slate-900">{a.titulo}</p>
                    {a.category_nome ? (
                      <p className="mt-0.5 text-sm text-slate-500">{a.category_nome}</p>
                    ) : null}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <p className="text-center text-sm text-slate-500">
        Não achou o que precisava?{' '}
        <Link
          to="/portal/tickets/novo"
          className="font-semibold hover:underline"
          style={{ color: 'var(--portal-link)' }}
        >
          Abrir chamado
        </Link>
      </p>
    </div>
  )
}

export function PortalAjudaArtigo() {
  const { slug } = useParams<{ slug: string }>()
  const [artigo, setArtigo] = useState<Kb.Article | null>(null)
  const [loading, setLoading] = useState(true)
  const toast = useToast()

  useEffect(() => {
    if (!slug) return
    let cancelled = false
    setLoading(true)
    kbPublic
      .getArticleBySlug(slug)
      .then((a) => {
        if (!cancelled) setArtigo(a)
      })
      .catch((err) => {
        if (!cancelled) toast.showError(mensagemFalhaParaToast(err, 'Artigo não encontrado.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [slug, toast])

  if (loading) {
    return <div className="h-64 animate-pulse rounded-2xl bg-slate-100" />
  }
  if (!artigo) {
    return (
      <div className="space-y-3">
        <Link to="/portal/ajuda" className="text-sm font-medium text-slate-500 hover:text-slate-800">
          ← Voltar
        </Link>
        <p className="text-sm text-slate-600">Artigo não encontrado.</p>
      </div>
    )
  }

  return (
    <article className="space-y-4">
      <Link to="/portal/ajuda" className="text-sm font-medium text-slate-500 hover:text-slate-800">
        ← Voltar à ajuda
      </Link>
      <div className={`${portalCardClass} p-5 sm:p-6`}>
        <h1 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{artigo.titulo}</h1>
        {artigo.category_nome ? (
          <p className="mt-2 text-sm text-slate-500">{artigo.category_nome}</p>
        ) : null}
        <div className="prose prose-slate mt-5 max-w-none prose-a:text-[var(--portal-link)]">
          <KbMarkdownPreview markdown={artigo.conteudo_markdown || ''} />
        </div>
      </div>
      <p className="text-center text-sm text-slate-500">
        Ainda com dúvida?{' '}
        <Link
          to="/portal/tickets/novo"
          className="font-semibold hover:underline"
          style={{ color: 'var(--portal-link)' }}
        >
          Abrir chamado
        </Link>
      </p>
    </article>
  )
}
