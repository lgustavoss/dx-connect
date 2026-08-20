import { type ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  loading?: boolean
}

const variants: Record<Variant, string> = {
  primary:
    'bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 shadow-md shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-950',
  secondary:
    'bg-slate-100 text-slate-800 hover:bg-slate-200 focus:ring-slate-400 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
  ghost:
    'bg-transparent text-slate-700 hover:bg-slate-100 focus:ring-slate-400 dark:text-slate-300 dark:hover:bg-slate-800',
}

export function Button({
  variant = 'primary',
  loading,
  className = '',
  disabled,
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  // Se o caller passa `hidden` / `md:inline-flex`, não forçar `inline-flex` na base
  // (sem twMerge, utilitários de display competem e o botão fica visível — #748).
  const callerControlsDisplay = /\b(hidden|inline-flex|flex|block|inline-block)\b/.test(className)
  const displayClass = callerControlsDisplay ? '' : 'inline-flex'
  return (
    <button
      type={type}
      className={`
        ${displayClass} items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium
        focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]}
        ${className}
      `}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <>
          <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          Aguarde...
        </>
      ) : (
        children
      )}
    </button>
  )
}
