import {
  type InputHTMLAttributes,
  type ReactNode,
  forwardRef,
  type ForwardedRef,
} from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  /** Texto de ajuda curto sob o rótulo (ex.: diferença entre campos). */
  hint?: ReactNode
  error?: string
  /** Conteúdo à direita (ex.: botão de mostrar senha). O campo ganha padding extra. */
  endAdornment?: ReactNode
}

/** Classes base de campo de texto (mesmas do Input). Útil para máscaras sem o componente. */
export const INPUT_FIELD_CLASS = `
            w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900
            placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500
            disabled:bg-slate-50 disabled:text-slate-500
            dark:border-slate-600 dark:bg-slate-900/50 dark:text-slate-100 dark:placeholder:text-slate-500
            dark:focus:border-cyan-500/60 dark:focus:ring-cyan-500/40
            dark:disabled:bg-slate-900/30 dark:disabled:text-slate-500
          `

/** Mesmo visual do Input para `<textarea>` soltos. */
export const TEXTAREA_FIELD_CLASS = INPUT_FIELD_CLASS.trim()

function slugFromLabel(label: string) {
  return (
    label
      .toLowerCase()
      .replace(/\s*\*\s*/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-]/g, '') || 'field'
  )
}

export const Input = forwardRef(function InputInner(
  props: InputProps,
  ref: ForwardedRef<HTMLInputElement>,
) {
  const { label, hint, error, className = '', id, endAdornment, ...rawRest } = props
  const ariaDescribedByProp = rawRest['aria-describedby']
  const rest = { ...rawRest } as Record<string, unknown>
  delete rest['aria-describedby']
  const inputId = id ?? (label ? slugFromLabel(label) : 'field')
  const hintId = hint ? `${inputId}-hint` : undefined
  const describedBy = [hintId, ariaDescribedByProp].filter(Boolean).join(' ') || undefined
  const domProps = rest as InputHTMLAttributes<HTMLInputElement>
  const field = (
    <input
      ref={ref}
      {...domProps}
      id={inputId}
      aria-describedby={describedBy}
      className={`
            ${INPUT_FIELD_CLASS}
            ${endAdornment ? 'pr-11' : ''}
            ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}
            ${className}
          `}
      title={error || domProps.title}
    />
  )
  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
          {label}
        </label>
      )}
      {hint ? (
        <p id={`${inputId}-hint`} className="mb-1.5 text-xs leading-snug text-slate-500 dark:text-slate-400">
          {hint}
        </p>
      ) : null}
      {endAdornment ? (
        <div className="relative">
          {field}
          <div className="absolute inset-y-0 right-0 z-10 flex items-center pr-1.5">{endAdornment}</div>
        </div>
      ) : (
        field
      )}
    </div>
  )
})
Input.displayName = 'Input'
