import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { kbPublic, type Kb } from '../../api/client'
import { KbMarkdownPreview } from '../../components/kb/KbMarkdownPreview'
import { VoltarButton } from '../../components/ui/VoltarButton'
import { useKbPublicBranding } from './KbPublicContext'
import { KbPublicArtigoFeedback } from './KbPublicArtigoFeedback'

export function KbPublicArtigo() {
  const branding = useKbPublicBranding()
  const navigate = useNavigate()
  const { slug } = useParams<{ slug: string }>()
  const [artigo, setArtigo] = useState<Kb.Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [naoEncontrado, setNaoEncontrado] = useState(false)

  useEffect(() => {
    if (!slug) {
      setNaoEncontrado(true)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    kbPublic
      .getArticleBySlug(slug)
      .then((a) => {
        if (!cancelled) {
          setArtigo(a)
          setNaoEncontrado(false)
          document.title = `${a.titulo} — ${branding.portal_titulo}`
        }
      })
      .catch(() => {
        if (!cancelled) {
          setArtigo(null)
          setNaoEncontrado(true)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [slug, branding.portal_titulo])

  const linkStyle = { color: branding.cor_link }

  if (loading) {
    return <p className="text-sm opacity-60">Carregando manual…</p>
  }

  if (naoEncontrado || !artigo) {
    return (
      <div className="space-y-4">
        <p>Manual não encontrado ou não está mais disponível.</p>
        <VoltarButton
          onClick={() => navigate('/kb')}
          label="Voltar para a central de ajuda"
        />
      </div>
    )
  }

  return (
    <article className="space-y-6">
      <nav className="text-sm opacity-70">
        <Link to="/kb" className="font-medium hover:underline" style={linkStyle}>
          Central de ajuda
        </Link>
        {artigo.category_nome ? <span> / {artigo.category_nome}</span> : null}
      </nav>

      <header>
        <h1 className="text-2xl font-bold sm:text-3xl" style={{ color: branding.cor_texto_corpo }}>
          {artigo.titulo}
        </h1>
        {artigo.updated_at ? (
          <p className="mt-2 text-xs opacity-60">
            Atualizado em {new Date(artigo.updated_at).toLocaleDateString('pt-BR')}
          </p>
        ) : null}
      </header>

      <div
        className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8"
        style={{ color: branding.cor_texto_corpo }}
      >
        <KbMarkdownPreview markdown={artigo.conteudo_markdown} />
      </div>

      <KbPublicArtigoFeedback slug={artigo.slug} />

      <VoltarButton onClick={() => navigate('/kb')} label="Voltar para todos os manuais" />
    </article>
  )
}
