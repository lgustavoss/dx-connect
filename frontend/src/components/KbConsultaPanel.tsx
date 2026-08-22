import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { kb, type Kb } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { KbListaFiltros } from './kb/KbListaFiltros'
import { KbMarkdownPreview } from './kb/KbMarkdownPreview'
import { Button } from './ui/Button'
import { VoltarButton } from './ui/VoltarButton'
import { useToast } from './ui/Toast'
import { textoReferenciaKb } from '../lib/kbReferencia'
import {
  cacheKbArticle,
  getKbOfflineById,
  getKbOfflineBySlug,
  listKbOfflineCache,
  type KbCachedArticle,
} from '../lib/kbOfflineCache'

type Props = {
  onInserirReferencia?: (texto: string) => void
  showInserir?: boolean
}

function cachedToArticle(c: KbCachedArticle): Kb.Article {
  return {
    id: c.id,
    titulo: c.titulo,
    slug: c.slug,
    category_id: null,
    category_nome: c.category_nome,
    status: 'publicado',
    interno_only: false,
    conteudo_markdown: c.conteudo_markdown,
    autor_atendente_id: null,
    autor_nome: null,
    published_at: null,
    updated_at: null,
    archived_at: null,
    created_at: c.cached_at,
  }
}

export function KbConsultaPanel({ onInserirReferencia, showInserir = false }: Props) {
  const toast = useToast()
  const toastRef = useRef(toast)
  toastRef.current = toast
  const [searchParams, setSearchParams] = useSearchParams()
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [categorias, setCategorias] = useState<Kb.Category[]>([])
  const [itens, setItens] = useState<Kb.ArticleBrief[]>([])
  const [loading, setLoading] = useState(false)
  const [artigo, setArtigo] = useState<Kb.Article | null>(null)
  const [loadingArtigo, setLoadingArtigo] = useState(false)
  const [offline, setOffline] = useState(() => typeof navigator !== 'undefined' && !navigator.onLine)
  const [cacheRecentes, setCacheRecentes] = useState<KbCachedArticle[]>(() => listKbOfflineCache())

  useEffect(() => {
    function syncOnline() {
      setOffline(!navigator.onLine)
    }
    window.addEventListener('online', syncOnline)
    window.addEventListener('offline', syncOnline)
    return () => {
      window.removeEventListener('online', syncOnline)
      window.removeEventListener('offline', syncOnline)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 350)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    if (offline) return
    kb.listCategories()
      .then(setCategorias)
      .catch(() => setCategorias([]))
  }, [offline])

  const carregar = useCallback(() => {
    if (offline) {
      const cached = listKbOfflineCache()
      setItens(
        cached.map((c) => ({
          id: c.id,
          titulo: c.titulo,
          slug: c.slug,
          category_id: null,
          category_nome: c.category_nome,
          status: 'publicado',
          interno_only: false,
          autor_nome: null,
          published_at: null,
          updated_at: c.cached_at,
        })),
      )
      return
    }
    setLoading(true)
    kb.consulta({
      busca: debouncedBusca || undefined,
      category_id: categoryId ? Number(categoryId) : undefined,
    })
      .then(setItens)
      .catch((err) => {
        toastRef.current.showWarning(mensagemFalhaParaToast(err, 'Não foi possível buscar artigos.'))
        setItens([])
      })
      .finally(() => setLoading(false))
  }, [categoryId, debouncedBusca, offline])

  useEffect(() => {
    carregar()
  }, [carregar])

  const abrirArtigo = useCallback(
    async (id: number, slug?: string) => {
      setLoadingArtigo(true)
      try {
        if (offline) {
          const cached = getKbOfflineById(id) ?? (slug ? getKbOfflineBySlug(slug) : null)
          if (!cached) {
            toastRef.current.showWarning('Este manual não está salvo neste computador. Abra-o uma vez com internet.')
            return
          }
          setArtigo(cachedToArticle(cached))
          return
        }
        const full = await kb.getPublicado(id)
        setArtigo(full)
        cacheKbArticle(full)
        setCacheRecentes(listKbOfflineCache())
      } catch (err) {
        const cached = getKbOfflineById(id) ?? (slug ? getKbOfflineBySlug(slug) : null)
        if (cached) {
          setArtigo(cachedToArticle(cached))
          toastRef.current.showWarning('Exibindo a última versão salva neste computador.')
        } else {
          toastRef.current.showError(mensagemFalhaParaToast(err, 'Artigo não encontrado.'))
        }
      } finally {
        setLoadingArtigo(false)
      }
    },
    [offline],
  )

  useEffect(() => {
    const slugParam = searchParams.get('artigo')
    const idParam = searchParams.get('id')
    if (slugParam) {
      void (async () => {
        if (offline) {
          const cached = getKbOfflineBySlug(slugParam)
          if (cached) setArtigo(cachedToArticle(cached))
          return
        }
        try {
          const brief = await kb.consulta({ busca: slugParam, limit: 50 })
          const match = brief.find((b) => b.slug === slugParam)
          if (match) await abrirArtigo(match.id, match.slug)
        } catch {
          const cached = getKbOfflineBySlug(slugParam)
          if (cached) setArtigo(cachedToArticle(cached))
        }
      })()
      return
    }
    if (idParam) {
      const id = Number(idParam)
      if (!Number.isNaN(id)) void abrirArtigo(id)
    }
  }, [abrirArtigo, offline, searchParams])

  function voltarLista() {
    setArtigo(null)
    if (searchParams.has('artigo') || searchParams.has('id')) {
      const next = new URLSearchParams(searchParams)
      next.delete('artigo')
      next.delete('id')
      setSearchParams(next, { replace: true })
    }
  }

  if (artigo) {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <VoltarButton onClick={voltarLista} label="Voltar à lista" />
          {showInserir && onInserirReferencia ? (
            <Button
              type="button"
              onClick={() => {
                onInserirReferencia(
                  textoReferenciaKb({
                    titulo: artigo.titulo,
                    slug: artigo.slug,
                    interno_only: artigo.interno_only,
                  }),
                )
                toast.showSuccess('Referência inserida na mensagem.')
              }}
            >
              Inserir referência na mensagem
            </Button>
          ) : null}
        </div>
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{artigo.titulo}</h2>
          {artigo.category_nome ? (
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{artigo.category_nome}</p>
          ) : null}
        </div>
        {loadingArtigo ? (
          <p className="text-sm text-slate-500">Carregando…</p>
        ) : (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/50">
            <KbMarkdownPreview markdown={artigo.conteudo_markdown} />
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {offline ? (
        <p className="rounded-lg border border-amber-200/80 bg-amber-50/90 px-3 py-2 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/25 dark:text-amber-100">
          Sem conexão — mostrando manuais que você consultou recentemente neste computador.
        </p>
      ) : null}

      {cacheRecentes.length > 0 && !offline ? (
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Consultados recentemente</h3>
          <ul className="flex flex-wrap gap-2">
            {cacheRecentes.slice(0, 5).map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => abrirArtigo(c.id, c.slug)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                >
                  {c.titulo}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {!offline ? (
        <KbListaFiltros
          busca={busca}
          onBuscaChange={setBusca}
          buscaPlaceholder="Buscar manuais publicados…"
          categoryId={categoryId}
          onCategoryChange={setCategoryId}
          categorias={categorias}
          disabled={loading}
        />
      ) : null}

      <div className="min-h-[12rem]">
        {loading ? (
          <p className="py-8 text-center text-sm text-slate-500">Carregando…</p>
        ) : itens.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            {offline
              ? 'Nenhum manual salvo neste computador. Conecte-se à internet e abra um manual pelo menos uma vez.'
              : 'Nenhum manual publicado encontrado. Peça a um administrador para publicar em Ajuda → Artigos.'}
          </p>
        ) : (
          <ul className="divide-y divide-slate-200/80 overflow-hidden rounded-xl border border-slate-200/90 dark:divide-slate-800 dark:border-slate-800/80">
            {itens.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => abrirArtigo(item.id, item.slug)}
                  className="flex w-full flex-col gap-0.5 px-4 py-3.5 text-left transition-colors hover:bg-slate-50 dark:hover:bg-white/50"
                >
                  <span className="font-medium text-slate-900 dark:text-slate-100">{item.titulo}</span>
                  <span className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                    {item.category_nome ? <span>{item.category_nome}</span> : null}
                    {item.interno_only ? (
                      <span className="rounded bg-slate-200/80 px-1.5 py-0.5 dark:bg-slate-700">Só equipe</span>
                    ) : null}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
