import { type InputHTMLAttributes, type ReactNode, useId } from 'react'

type BoxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'className'>

export interface CheckboxFieldProps extends BoxProps {
  children: ReactNode
  variant?: 'chip' | 'inline' | 'card'
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
  title,
  ...inputProps
}: CheckboxFieldProps) {
  const uid = useId()
  const id = idProp ?? `cb-${uid}`

  const bordaMarcada = checked
    ? 'border-slate-800 bg-white shadow-sm ring-1 ring-slate-800/12 dark:border-slate-400 dark:bg-slate-900 dark:ring-slate-400/20'
    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/90 dark:border-slate-600 dark:bg-slate-900 dark:hover:border-slate-500 dark:hover:bg-slate-800/80'
  const chipClasses =
    variant === 'card'
      ? `flex h-full w-full cursor-pointer select-none items-start gap-3 rounded-xl border p-4 text-sm transition-all duration-150 focus-within:ring-2 focus-within:ring-slate-500 focus-within:ring-offset-2 dark:focus-within:ring-offset-slate-900 ${bordaMarcada}`
      : variant === 'chip'
        ? `inline-flex cursor-pointer select-none items-center gap-2.5 rounded-lg border px-3 py-2 text-sm transition-all duration-150 focus-within:ring-2 focus-within:ring-slate-500 focus-within:ring-offset-2 dark:focus-within:ring-offset-slate-900 ${bordaMarcada}`
        : `inline-flex cursor-pointer select-none items-center gap-2.5 rounded-md text-sm focus-within:ring-2 focus-within:ring-slate-500 focus-within:ring-offset-1 dark:focus-within:ring-offset-slate-900`

  return (
    <label
      title={title}
      className={`${chipClasses} ${disabled ? 'cursor-not-allowed opacity-50' : ''} ${className}`.trim()}
    >
      <input id={id} type="checkbox" className="sr-only" checked={checked} disabled={disabled} {...inputProps} />
      <span
        aria-hidden
        className={`flex size-4 shrink-0 items-center justify-center rounded border-2 transition-colors duration-150 ${
          variant === 'card' ? 'mt-0.5' : ''
        } ${
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
        className={`${variant === 'card' ? 'min-w-0 flex-1' : ''} font-medium ${
          checked ? 'text-slate-900 dark:text-slate-100' : 'text-slate-700 dark:text-slate-300'
        }`}
      >
        {children}
      </span>
    </label>
  )
}

/**
 * Lista de opções, uma por linha, todas visíveis — #1239 / #S202610-0017.
 */
export function CheckboxOptionList({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`contain-layout overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/40 ${className}`.trim()}
    >
      <div className="flex flex-col divide-y divide-slate-200 dark:divide-slate-800 [&>label]:w-full [&>label]:rounded-none [&>label]:border-0 [&>label]:px-3.5 [&>label]:py-2.5 [&>label]:hover:bg-slate-50 dark:[&>label]:hover:bg-slate-800/50">
        {children}
      </div>
    </div>
  )
}
