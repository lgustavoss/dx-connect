import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  kbCategoriaPorId,
  kbCategoriasRaizPublicas,
  kbSubcategoriasPublicas,
} from '../../lib/kbPublicCategorias'
import { useKbPublic, useKbPublicBranding } from './KbPublicContext'

function Chevron({ aberto }: { aberto: boolean }) {
  return (
    <svg
      className={`size-4 shrink-0 transition-transform ${aberto ? 'rotate-90' : ''}`}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden
    >
      <path
        fillRule="evenodd"
        d="M7.21 14.77a.75.75 0 01.02-1.06L10.17 10 7.23 6.29a.75.75 0 111.04-1.08l3.5 3.25a.75.75 0 010 1.08l-3.5 3.25a.75.75 0 01-1.06-.02z"
        clipRule="evenodd"
      />
    </svg>
  )
}

export function KbPublicSidebar() {
  const branding = useKbPublicBranding()
  const { categorias, categoriasLoading, sidebarCollapsed } = useKbPublic()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = Number(searchParams.get('c') || '') || null
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set())

  const raizes = useMemo(() => kbCategoriasRaizPublicas(categorias), [categorias])

  function toggleExpanded(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function selecionarCategoria(id: number) {
    const next = new URLSearchParams(searchParams)
    next.set('c', String(id))
    next.delete('busca')
    setSearchParams(next, { replace: true })
  }

  function handleRaizClick(catId: number) {
    const subs = kbSubcategoriasPublicas(categorias, catId)
    if (subs.length > 0) {
      toggleExpanded(catId)
      return
    }
    selecionarCategoria(catId)
  }

  if (sidebarCollapsed) {
    return null
  }

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200/80 bg-white lg:w-72">
      <div className="border-b border-slate-200/80 px-3 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Categorias</p>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3" aria-label="Categorias da base de conhecimento">
        {categoriasLoading ? (
          <p className="px-2 text-sm text-slate-500">Carregando…</p>
        ) : raizes.length === 0 ? (
          <p className="px-2 text-sm text-slate-500">Nenhuma categoria publicada.</p>
        ) : (
          <ul className="space-y-0.5">
            {raizes.map((root) => {
              const subs = kbSubcategoriasPublicas(categorias, root.id)
              const aberto = expanded.has(root.id) || subs.some((s) => s.id === selectedId)
              const rootSelected = selectedId === root.id
              return (
                <li key={root.id}>
                  <div className="flex items-stretch">
                    {subs.length > 0 ? (
                      <button
                        type="button"
                        onClick={() => toggleExpanded(root.id)}
                        className="flex w-8 shrink-0 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                        aria-label={aberto ? 'Recolher subcategorias' : 'Expandir subcategorias'}
                      >
                        <Chevron aberto={aberto} />
                      </button>
                    ) : (
                      <span className="w-8 shrink-0" />
                    )}
                    <button
                      type="button"
                      onClick={() => handleRaizClick(root.id)}
                      className={`min-w-0 flex-1 rounded-lg px-2 py-2 text-left text-sm font-medium transition-colors ${
                        rootSelected ? 'text-white' : 'text-slate-700 hover:bg-slate-100'
                      }`}
                      style={rootSelected ? { backgroundColor: branding.cor_primaria } : undefined}
                    >
                      {root.nome}
                    </button>
                  </div>
                  {subs.length > 0 && aberto ? (
                    <ul className="ml-8 mt-0.5 space-y-0.5 border-l border-slate-200 pl-2">
                      {subs.map((sub) => {
                        const selected = selectedId === sub.id
                        return (
                          <li key={sub.id}>
                            <button
                              type="button"
                              onClick={() => selecionarCategoria(sub.id)}
                              className={`w-full rounded-lg px-2 py-1.5 text-left text-sm transition-colors ${
                                selected ? 'font-medium text-white' : 'text-slate-600 hover:bg-slate-100'
                              }`}
                              style={selected ? { backgroundColor: branding.cor_primaria } : undefined}
                            >
                              {sub.nome}
                            </button>
                          </li>
                        )
                      })}
                    </ul>
                  ) : null}
                </li>
              )
            })}
          </ul>
        )}

        <div className="mt-4 border-t border-slate-200/80 pt-3">
          <Link
            to="/kb"
            className="block rounded-lg px-2 py-2 text-sm text-slate-600 hover:bg-slate-100"
            onClick={() => setSearchParams({}, { replace: true })}
          >
            Ver todos os manuais
          </Link>
        </div>
      </nav>
    </aside>
  )
}

export function tituloCategoriaPublica(categorias: ReturnType<typeof useKbPublic>['categorias'], id: number | null) {
  if (!id) return null
  return kbCategoriaPorId(categorias, id)?.nome ?? null
}
