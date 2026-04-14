import { useId, type ButtonHTMLAttributes } from 'react'

type OmitBase = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'type' | 'role' | 'onClick' | 'children'>

export interface SwitchProps extends OmitBase {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  label: string
  description?: string
  /** Sem caixa; só rótulo + interruptor */
  bare?: boolean
  /** Selo textual (ex.: Ativo / Inativo) — recomendado para não depender só de cor. */
  showStatusPill?: boolean
  statusOnText?: string
  statusOffText?: string
}

/**
 * Interruptor acessível (role="switch"), visual alinhado aos botões primary (slate-800).
 */
export function Switch({
  checked,
  onCheckedChange,
  label,
  description,
  disabled,
  bare = false,
  showStatusPill = false,
  statusOnText = 'Ativo',
  statusOffText = 'Inativo',
  className = '',
  id: idProp,
  ...rest
}: SwitchProps) {
  const uid = useId()
  const id = idProp ?? `switch-${uid}`
  const alignRow = description ? 'items-start' : 'items-center'

  return (
    <div
      className={
        bare
          ? `flex w-full ${alignRow} justify-between gap-3 ${className}`
          : `flex w-full ${alignRow} justify-between gap-3 rounded-lg border border-slate-200/80 bg-slate-50/50 px-3.5 py-2.5 shadow-sm shadow-slate-900/5 dark:border-slate-600/50 dark:bg-slate-800/30 dark:shadow-none ${className}`
      }
    >
      <div className={`min-w-0 flex-1 ${description ? 'pt-0.5' : ''}`}>
        <label
          htmlFor={id}
          className={`text-sm font-medium text-slate-700 dark:text-slate-300 ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
        >
          {label}
        </label>
        {description ? (
          <p className="mt-0.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">{description}</p>
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        {showStatusPill ? (
          <span
            className={`min-w-[4.25rem] rounded-full px-2.5 py-1 text-center text-xs font-semibold tabular-nums transition-colors ${
              checked
                ? 'bg-emerald-100 text-emerald-800 ring-1 ring-emerald-600/15 dark:bg-emerald-950/55 dark:text-emerald-300 dark:ring-emerald-500/25'
                : 'bg-rose-50 text-rose-700 ring-1 ring-rose-600/15 dark:bg-rose-950/35 dark:text-rose-200 dark:ring-rose-500/25'
            }`}
          >
            {checked ? statusOnText : statusOffText}
          </span>
        ) : null}
        <button
          id={id}
          type="button"
          role="switch"
          aria-checked={checked}
          disabled={disabled}
          {...rest}
          onClick={() => !disabled && onCheckedChange(!checked)}
          className={`
          relative inline-flex h-7 w-11 shrink-0 cursor-pointer rounded-full border transition-colors duration-200
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900
          disabled:cursor-not-allowed disabled:opacity-45
          ${
            checked
              ? 'border-emerald-600 bg-emerald-600 dark:border-emerald-500 dark:bg-emerald-500'
              : 'border-slate-300/60 bg-slate-200 dark:border-slate-600 dark:bg-slate-700/80'
          }
        `}
        >
          <span
            aria-hidden
            className={`
            pointer-events-none absolute left-0.5 top-0.5 size-5 rounded-full shadow-sm ring-1 transition-transform duration-200 ease-out
            ${
              checked
                ? 'translate-x-[22px] bg-white ring-emerald-900/10'
                : 'translate-x-0 bg-white ring-slate-900/5 dark:bg-slate-300 dark:ring-slate-900/20'
            }
          `}
          />
        </button>
      </div>
    </div>
  )
}
