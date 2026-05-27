import { useState, useMemo, useRef, useEffect } from 'react'

const MAX_MATCHES = 80
const DEFAULT_RECENT = 8

export interface ItemStringPesquisa {
  value: string
  label: string
}

interface SelectStringComPesquisaProps {
  label: string
  value: string
  onChange: (value: string) => void
  items: ItemStringPesquisa[]
  placeholder?: string
  emptyPlaceholder?: string
  required?: boolean
  disabled?: boolean
  /** Quantidade exibida quando a busca está vazia */
  recentCount?: number
  hint?: string
  id?: string
  loading?: boolean
  /** Classe opcional para o botão trigger (padronização visual). */
  triggerClassName?: string
}

export function SelectStringComPesquisa({
  label,
  value,
  onChange,
  items,
  placeholder = 'Buscar...',
  emptyPlaceholder = 'Selecione…',
  required,
  disabled,
  recentCount = DEFAULT_RECENT,
  hint = 'Digite para filtrar a lista.',
  id: domId,
  loading,
  triggerClassName,
}: SelectStringComPesquisaProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const rootRef = useRef<HTMLDivElement>(null)
  const listId = domId ? `${domId}-listbox` : undefined

  const displayed = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) {
      return items.slice(0, recentCount)
    }
    return items.filter((it) => it.label.toLowerCase().includes(q)).slice(0, MAX_MATCHES)
  }, [items, query, recentCount])

  const selectedLabel = value ? items.find((i) => i.value === value)?.label ?? value : ''

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
    <div ref={rootRef} className="relative">
      <label htmlFor={domId} className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
        {label}
        {required ? ' *' : ''}
      </label>
      <button
        type="button"
        id={domId}
        disabled={disabled || items.length === 0}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => !(disabled || items.length === 0) && setOpen((o) => !o)}
        className={
          triggerClassName?.trim()
            ? triggerClassName
            : "flex w-full items-center justify-between rounded-xl border-0 bg-white px-3 py-2 text-left text-sm text-slate-800 shadow-sm ring-1 ring-slate-200/90 transition-[box-shadow,ring] hover:ring-slate-300/80 focus:outline-none focus:ring-2 focus:ring-slate-400/35 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-900/50 dark:text-slate-100 dark:ring-slate-600 dark:hover:ring-slate-500 dark:focus:ring-cyan-500/30"
        }
      >
        <span className={!selectedLabel ? 'text-slate-400 dark:text-slate-500' : ''}>
          {loading ? 'Carregando…' : items.length === 0 ? emptyPlaceholder : selectedLabel || emptyPlaceholder}
        </span>
        <span className="text-slate-400 dark:text-slate-500" aria-hidden>
          {open ? '▴' : '▾'}
        </span>
      </button>
      {open && (
        <div
          className="absolute z-30 mt-1.5 w-full overflow-hidden rounded-xl border border-slate-200/95 bg-white py-1.5 shadow-xl shadow-slate-200/50 ring-1 ring-slate-900/[0.04] dark:border-slate-600 dark:bg-slate-900 dark:shadow-slate-950/50 dark:ring-white/5"
          role="listbox"
          id={listId}
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="w-full border-b border-slate-100 bg-transparent px-3 py-2 text-sm text-slate-900 outline-none focus:bg-slate-50/50 dark:border-slate-700 dark:text-slate-100 dark:focus:bg-slate-800/50"
            autoFocus
            aria-label={`Buscar em ${label}`}
          />
          <p className="px-3 py-1.5 text-xs text-slate-400 dark:text-slate-500">{hint}</p>
          <ul className="max-h-52 overflow-y-auto py-1">
            {displayed.length === 0 ? (
              <li className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">Nenhum resultado.</li>
            ) : (
              displayed.map((it) => (
                <li key={it.value} role="none">
                  <button
                    type="button"
                    role="option"
                    aria-selected={value === it.value}
                    className={`mx-1 w-[calc(100%-0.5rem)] rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/80 ${value === it.value ? 'bg-slate-100/90 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100' : 'text-slate-700 dark:text-slate-300'}`}
                    onClick={() => {
                      onChange(it.value)
                      setOpen(false)
                      setQuery('')
                    }}
                  >
                    {it.label}
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
