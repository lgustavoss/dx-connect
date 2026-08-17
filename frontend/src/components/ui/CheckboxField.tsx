import { type InputHTMLAttributes, type ReactNode, useId } from 'react'

type BoxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'className'>

export interface CheckboxFieldProps extends BoxProps {
  children: ReactNode
  variant?: 'chip' | 'inline'
  className?: string
}

/**
 * Checkbox estilizado com foco visível — listas de setores, empresas, etc.
 */
export function CheckboxField({
  children,
  variant = 'chip',
  className = '',
  id: idProp,
  checked,
  disabled,
  ...inputProps
}: CheckboxFieldProps) {
  const uid = useId()
  const id = idProp ?? `cb-${uid}`

  const chipClasses =
    variant === 'chip'
      ? `inline-flex cursor-pointer select-none items-center gap-2.5 rounded-lg border px-3 py-2 text-sm transition-all duration-150 focus-within:ring-2 focus-within:ring-slate-500 focus-within:ring-offset-2 dark:focus-within:ring-offset-slate-900 ${
          checked
            ? 'border-slate-800 bg-white shadow-sm ring-1 ring-slate-800/12 dark:border-slate-400 dark:bg-slate-900 dark:ring-slate-400/20'
            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/90 dark:border-slate-600 dark:bg-slate-900 dark:hover:border-slate-500 dark:hover:bg-slate-800/80'
        }`
      : `inline-flex cursor-pointer select-none items-center gap-2.5 rounded-md text-sm focus-within:ring-2 focus-within:ring-slate-500 focus-within:ring-offset-1 dark:focus-within:ring-offset-slate-900`

  return (
    <label
      className={`${chipClasses} ${disabled ? 'cursor-not-allowed opacity-50' : ''} ${className}`.trim()}
    >
      <input id={id} type="checkbox" className="sr-only" checked={checked} disabled={disabled} {...inputProps} />
      <span
        aria-hidden
        className={`flex size-4 shrink-0 items-center justify-center rounded border-2 transition-colors duration-150 ${
          checked
            ? 'border-slate-800 bg-slate-800 dark:border-slate-200 dark:bg-slate-200'
            : 'border-slate-300 bg-white dark:border-slate-500 dark:bg-slate-800'
        }`}
      >
        {checked && (
          <svg
            className="size-2.5 text-white dark:text-slate-900"
            viewBox="0 0 12 12"
            fill="none"
            aria-hidden
          >
            <path
              d="M2.5 6l2.5 2.5 5-5.5"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </span>
      <span
        className={`font-medium ${
          checked ? 'text-slate-900 dark:text-slate-100' : 'text-slate-700 dark:text-slate-300'
        }`}
      >
        {children}
      </span>
    </label>
  )
}
