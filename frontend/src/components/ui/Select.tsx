import { useState, useRef, useEffect, useLayoutEffect, useId } from 'react'
import { createPortal } from 'react-dom'

/** Valor vazio = nenhuma opção numérica/string selecionada (filtros, opcionais). */
export type SelectValue = string | number | ''

export type SelectOption = { value: string | number; label: string }

const chevron = (
  <svg className="size-4 shrink-0 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
)

export interface SelectProps {
  id?: string
  label?: string
  /** `overline`: rótulo compacto em caixa alta (filtros). */
  labelStyle?: 'default' | 'overline'
  value: SelectValue
  onChange: (value: SelectValue) => void
  options: SelectOption[]
  /** Texto quando `value === ''` ou sem opção correspondente. */
  placeholder?: string
  /** Inclui linha no topo que define valor `''`. */
  includeEmpty?: boolean
  emptyLabel?: string
  disabled?: boolean
  className?: string
  /** id para testes / associar label */
  'aria-label'?: string
}

function sameValue(a: SelectValue, b: string | number): boolean {
  if (a === b) return true
  if (a === '' || b === '') return false
  const na = Number(a)
  const nb = Number(b)
  if (!Number.isNaN(na) && !Number.isNaN(nb) && na === nb) return true
  return false
}

export function Select({
  id: idProp,
  label,
  labelStyle = 'default',
  value,
  onChange,
  options,
  placeholder = 'Selecione',
  includeEmpty = false,
  emptyLabel = '—',
  disabled,
  className = '',
  'aria-label': ariaLabel,
}: SelectProps) {
  const reactId = useId()
  const id = idProp ?? `select-${reactId}`
  const listboxId = `${id}-listbox`

  const [open, setOpen] = useState(false)
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0, width: 0, maxH: 240 })

  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  const selectedLabel =
    value === '' ? null : (options.find((o) => sameValue(value, o.value))?.label ?? String(value))

  const displayText =
    value === '' ? (includeEmpty ? emptyLabel : placeholder) : (selectedLabel ?? placeholder)

  const updatePosition = () => {
    const el = triggerRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const gap = 6
    const margin = 12
    const vh = window.visualViewport?.height ?? window.innerHeight
    const spaceBelow = vh - r.bottom - gap - margin
    const spaceAbove = r.top - gap - margin
    // Em bottom sheets no mobile quase não há espaço abaixo — abre para cima.
    const openBelow = spaceBelow >= 140 || spaceBelow >= spaceAbove
    const maxH = Math.min(280, Math.max(96, openBelow ? spaceBelow : spaceAbove))
    setMenuPos({
      top: openBelow ? r.bottom + gap : Math.max(margin, r.top - gap - maxH),
      left: r.left,
      width: r.width,
      maxH,
    })
  }

  useLayoutEffect(() => {
    if (!open) return
    updatePosition()
  }, [open])

  useEffect(() => {
    if (!open) return
    const onWin = () => updatePosition()
    window.addEventListener('resize', onWin)
    window.addEventListener('scroll', onWin, true)
    return () => {
      window.removeEventListener('resize', onWin)
      window.removeEventListener('scroll', onWin, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    function onDoc(e: MouseEvent) {
      const t = e.target as Node
      if (triggerRef.current?.contains(t) || menuRef.current?.contains(t)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  const labelClass =
    labelStyle === 'overline'
      ? 'mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500'
      : 'mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300'

  const menu =
    open &&
    !disabled &&
    createPortal(
      <div
        ref={menuRef}
        id={listboxId}
        role="listbox"
        className="fixed z-[600] overflow-y-auto rounded-xl border border-slate-200/95 bg-white py-1.5 shadow-xl shadow-slate-200/50 ring-1 ring-slate-900/[0.04] dark:border-slate-600 dark:bg-slate-900 dark:shadow-black/40 dark:ring-white/10"
        style={{
          top: menuPos.top,
          left: menuPos.left,
          width: Math.max(menuPos.width, 168),
          maxHeight: menuPos.maxH,
        }}
      >
        {includeEmpty && (
          <button
            type="button"
            role="option"
            aria-selected={value === ''}
            className={`mx-1 flex w-[calc(100%-0.5rem)] rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/80 ${
              value === ''
                ? 'bg-slate-100/90 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                : 'text-slate-700 dark:text-slate-300'
            }`}
            onClick={() => {
              onChange('')
              setOpen(false)
            }}
          >
            {emptyLabel}
          </button>
        )}
        {options.map((o) => {
          const selected = sameValue(value, o.value)
          return (
            <button
              key={String(o.value)}
              type="button"
              role="option"
              aria-selected={selected}
              className={`mx-1 flex w-[calc(100%-0.5rem)] rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/80 ${
                selected
                  ? 'bg-slate-100/90 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                  : 'text-slate-700 dark:text-slate-300'
              }`}
              onClick={() => {
                onChange(o.value)
                setOpen(false)
              }}
            >
              {o.label}
            </button>
          )
        })}
      </div>,
      document.body,
    )

  return (
    <div className={`relative min-w-0 ${className}`}>
      {label && (
        <label htmlFor={id} className={labelClass}>
          {label}
        </label>
      )}
      <button
        ref={triggerRef}
        type="button"
        id={id}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-label={ariaLabel ?? label ?? placeholder}
        onClick={() => !disabled && setOpen((o) => !o)}
        className={`flex w-full items-center justify-between gap-2 rounded-xl border-0 bg-white py-2 pl-3 pr-2.5 text-left text-sm shadow-sm ring-1 ring-slate-200/90 transition-[box-shadow,ring] hover:ring-slate-300/80 focus:outline-none focus:ring-2 focus:ring-slate-400/35 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-900/80 dark:text-slate-100 dark:ring-slate-600/90 dark:hover:ring-slate-500 dark:focus:ring-slate-500/40 ${
          value === '' ? 'text-slate-500 dark:text-slate-400' : 'text-slate-900 dark:text-slate-100'
        }`}
      >
        <span className="min-w-0 flex-1 truncate">{displayText}</span>
        {chevron}
      </button>
      {menu}
    </div>
  )
}
