import { useState, useMemo, useRef, useEffect } from 'react'

export interface ItemSelectPesquisa {
  id: number
  label: string
  /** Texto extra para a busca (ex.: CNPJ sem máscara). Não aparece na lista. */
  detalhe?: string
  /** ISO ou string parseável para ordenar “mais recente primeiro” */
  createdAt?: string | null
}

const MAX_MATCHES = 40
const DEFAULT_RECENT = 3

function parseTime(iso?: string | null): number {
  if (!iso) return 0
  const t = Date.parse(iso)
  return Number.isNaN(t) ? 0 : t
}

function soDigitos(valor: string): string {
  return valor.replace(/\D/g, '')
}

/**
 * Casa o termo digitado com o rótulo (e o detalhe) do item.
 * Também compara por dígitos: `65.305.802/0001-70` casa com `65305802000170`
 * e vice-versa, porque o CNPJ é gravado sem máscara (#S202611-0001).
 */
export function itemCasaBusca(item: ItemSelectPesquisa, termo: string): boolean {
  const q = termo.trim().toLowerCase()
  if (!q) return true
  const alvo = `${item.label} ${item.detalhe ?? ''}`.toLowerCase()
  if (alvo.includes(q)) return true
  const digitosTermo = soDigitos(q)
  if (digitosTermo.length < 3) return false
  return soDigitos(alvo).includes(digitosTermo)
}

interface SelectComPesquisaProps {
  label: string
  value: number | ''
  onChange: (id: number) => void
  items: ItemSelectPesquisa[]
  placeholder?: string
  required?: boolean
  disabled?: boolean
  /** Quantidade exibida quando a busca está vazia (últimos por data de cadastro) */
  recentCount?: number
  hint?: string
  id?: string
  /**
   * `absolute` (padrão): lista flutuante sob o botão.
   * `inline`: lista no fluxo do formulário — use dentro de modais/sheets com overflow
   * para a caixa não ficar cortada nem desproporcional.
   */
  menuPlacement?: 'absolute' | 'inline'
  /**
   * Busca no servidor. Quando informado, ao digitar o componente para de filtrar
   * `items` e usa o resultado desta função (com debounce). Serve para catálogos
   * grandes ou quando o item não traz o dado pesquisado no rótulo.
   */
  onSearch?: (termo: string) => Promise<ItemSelectPesquisa[]>
  /** Tempo de espera antes de chamar `onSearch` (ms). */
  searchDebounceMs?: number
  /** Tamanho mínimo do termo para disparar `onSearch`. */
  minSearchLength?: number
}

export function SelectComPesquisa({
  label,
  value,
  onChange,
  items,
  placeholder = 'Buscar...',
  required,
  disabled,
  recentCount = DEFAULT_RECENT,
  hint = 'Sem digitar: últimos cadastros. Digite para filtrar.',
  id: domId,
  menuPlacement = 'absolute',
  onSearch,
  searchDebounceMs = 300,
  minSearchLength = 2,
}: SelectComPesquisaProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [remotos, setRemotos] = useState<ItemSelectPesquisa[] | null>(null)
  const [buscando, setBuscando] = useState(false)
  const [rotuloEscolhido, setRotuloEscolhido] = useState<string | null>(null)
  const rootRef = useRef<HTMLDivElement>(null)
  const buscaSeq = useRef(0)
  const listId = domId ? `${domId}-listbox` : undefined

  const sorted = useMemo(
    () => [...items].sort((a, b) => parseTime(b.createdAt) - parseTime(a.createdAt)),
    [items],
  )

  const displayed = useMemo(() => {
    const q = query.trim()
    if (!q) {
      return sorted.slice(0, recentCount)
    }
    if (onSearch && remotos) {
      return remotos.slice(0, MAX_MATCHES)
    }
    return sorted.filter((it) => itemCasaBusca(it, q)).slice(0, MAX_MATCHES)
  }, [sorted, query, recentCount, onSearch, remotos])

  const selectedLabel =
    value !== ''
      ? items.find((i) => i.id === value)?.label ??
        remotos?.find((i) => i.id === value)?.label ??
        rotuloEscolhido ??
        ''
      : ''

  useEffect(() => {
    if (!open) {
      setQuery('')
      setRemotos(null)
      setBuscando(false)
    }
  }, [open])

  useEffect(() => {
    if (value === '') setRotuloEscolhido(null)
  }, [value])

  // Busca no servidor: debounce + descarte de resposta fora de ordem.
  useEffect(() => {
    if (!open || !onSearch) return
    const termo = query.trim()
    if (termo.length < minSearchLength) {
      setRemotos(null)
      setBuscando(false)
      return
    }
    const seq = ++buscaSeq.current
    let cancelado = false
    setBuscando(true)
    const timer = window.setTimeout(() => {
      onSearch(termo)
        .then((lista) => {
          if (cancelado || seq !== buscaSeq.current) return
          setRemotos(lista)
        })
        .catch(() => {
          if (cancelado || seq !== buscaSeq.current) return
          setRemotos(null)
        })
        .finally(() => {
          if (cancelado || seq !== buscaSeq.current) return
          setBuscando(false)
        })
    }, searchDebounceMs)
    return () => {
      cancelado = true
      window.clearTimeout(timer)
    }
  }, [open, onSearch, query, minSearchLength, searchDebounceMs])

  useEffect(() => {
    if (!open) return
    function onDocClick(ev: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(ev.target as Node)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  return (
    <div ref={rootRef} className="relative w-full min-w-0">
      <label htmlFor={domId} className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
        {label}
        {required ? ' *' : ''}
      </label>
      <button
        type="button"
        id={domId}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => !disabled && setOpen((o) => !o)}
        className="flex w-full min-w-0 items-center justify-between gap-2 rounded-xl border-0 bg-white px-3 py-2.5 text-left text-sm text-slate-800 shadow-sm ring-1 ring-slate-200/90 transition-[box-shadow,ring] hover:ring-slate-300/80 focus:outline-none focus:ring-2 focus:ring-slate-400/35 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-900/50 dark:text-slate-100 dark:ring-slate-600 dark:hover:ring-slate-500 dark:focus:ring-cyan-500/30"
      >
        <span
          className={`min-w-0 flex-1 truncate ${!selectedLabel ? 'text-slate-400 dark:text-slate-500' : ''}`}
        >
          {selectedLabel || placeholder}
        </span>
        <span className="shrink-0 text-slate-400 dark:text-slate-500" aria-hidden>
          {open ? '▴' : '▾'}
        </span>
      </button>
      {open && (
        <div
          className={
            menuPlacement === 'inline'
              ? 'relative z-10 mt-1.5 w-full min-w-0 overflow-hidden rounded-xl border border-slate-200/95 bg-white py-1.5 shadow-md ring-1 ring-slate-900/[0.04] dark:border-slate-600 dark:bg-slate-900 dark:ring-white/5'
              : 'absolute left-0 right-0 z-30 mt-1.5 w-full min-w-0 overflow-hidden rounded-xl border border-slate-200/95 bg-white py-1.5 shadow-xl shadow-slate-200/50 ring-1 ring-slate-900/[0.04] dark:border-slate-600 dark:bg-slate-900 dark:shadow-slate-950/50 dark:ring-white/5'
          }
          role="listbox"
          id={listId}
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="w-full border-b border-slate-100 bg-transparent px-3 py-2.5 text-sm text-slate-900 outline-none focus:bg-slate-50/50 dark:border-slate-800 dark:text-slate-100 dark:focus:bg-slate-800/50"
            autoFocus
            aria-label={`Buscar em ${label}`}
          />
          <p className="px-3 py-1.5 text-xs text-slate-400 dark:text-slate-500">
            {buscando ? 'Buscando…' : hint}
          </p>
          <ul className="dx-scrollbar max-h-56 overflow-y-auto py-1">
            {displayed.length === 0 ? (
              <li className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">
                {buscando ? 'Buscando…' : 'Nenhum resultado.'}
              </li>
            ) : (
              displayed.map((it) => (
                <li key={it.id} role="none">
                  <button
                    type="button"
                    role="option"
                    aria-selected={value === it.id}
                    className={`mx-1 w-[calc(100%-0.5rem)] rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/80 ${value === it.id ? 'bg-slate-100/90 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100' : 'text-slate-700 dark:text-slate-300'}`}
                    onClick={() => {
                      onChange(it.id)
                      setRotuloEscolhido(it.label)
                      setOpen(false)
                      setQuery('')
                    }}
                  >
                    <span className="line-clamp-2 break-words">{it.label}</span>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  )
}
