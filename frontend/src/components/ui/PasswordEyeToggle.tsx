import { IconEye, IconEyeOff } from './IconEye'

type PasswordEyeToggleProps = {
  visible: boolean
  onToggle: () => void
  disabled?: boolean
}

/** Botão de mostrar/ocultar senha para `Input` `endAdornment`. */
export function PasswordEyeToggle({ visible, onToggle, disabled }: PasswordEyeToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className="inline-flex size-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 disabled:pointer-events-none disabled:opacity-40 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-slate-200"
      aria-label={visible ? 'Ocultar senha' : 'Mostrar senha'}
      aria-pressed={visible}
    >
      {visible ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
    </button>
  )
}
