import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { kbPublic } from '../../api/client'
import { KbListaFiltros } from '../../components/kb/KbListaFiltros'
import { useKbPublic, useKbPublicBranding } from './KbPublicContext'
import { tituloCategoriaPublica } from './KbPublicSidebar'

export function KbPublicHome() {
  const branding = useKbPublicBranding()
  const { categorias } = useKbPublic()
  const [searchParams] = useSearchParams()
  const categoryParam = searchParams.get('c')
  const categoryId = categoryParam ? Number(categoryParam) : ''
  const [busca, setBusca] = useState(searchParams.get('busca') ?? '')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [itens, setItens] = useState<Awaited<ReturnType<typeof kbPublic.listArticles>>>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  const tituloCategoria = tituloCategoriaPublica(categorias, categoryId ? Number(categoryId) : null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 350)
    return () => clearTimeout(t)
  }, [busca])

  const carregar = useCallback(() => {
    setLoading(true)
    setErro(null)
    kbPublic
      .listArticles({
        busca: debouncedBusca || undefined,
        category_id: categoryId ? Number(categoryId) : undefined,
        limit: 50,
      })
      .then(setItens)
      .catch(() => {
        setItens([])
        setErro('Não foi possível carregar os manuais.')
      })
      .finally(() => setLoading(false))
  }, [categoryId, debouncedBusca])

  useEffect(() => {
    carregar()
  }, [carregar])

  const subtitulo =
    branding.texto_boas_vindas?.trim() ||
    'Consulte passo a passo para tirar dúvidas sobre o sistema.'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: branding.cor_texto_corpo }}>
          {tituloCategoria ? tituloCategoria : 'Manuais e procedimentos'}
        </h1>
        <p className="mt-1 text-sm opacity-80">{subtitulo}</p>
      </div>

      <KbListaFiltros
        busca={busca}
        onBuscaChange={setBusca}
        categoryId={String(categoryId)}
        onCategoryChange={() => {}}
        categorias={[]}
        disabled={loading}
        hideCategoryFilter
      />

      {loading ? (
        <p className="text-sm opacity-60">Carregando…</p>
      ) : erro ? (
        <p className="text-sm text-red-600">{erro}</p>
      ) : itens.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-8 text-center text-sm text-slate-500">
          {tituloCategoria
            ? 'Nenhum manual publicado nesta categoria.'
            : 'Nenhum manual publicado encontrado.'}
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {itens.map((item) => (
            <li key={item.id}>
              <Link
                to={`/kb/a/${encodeURIComponent(item.slug)}`}
                className="block px-4 py-4 transition-colors hover:bg-slate-50 sm:px-5"
                style={{ color: branding.cor_texto_corpo }}
              >
                <p className="font-medium">{item.titulo}</p>
                {item.category_nome ? (
                  <p className="mt-0.5 text-xs text-slate-500">{item.category_nome}</p>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
