import { Button } from './Button'

type Props = {
  onClick: () => void
  label?: string
  className?: string
  /** Aria-label quando o texto visível for só «Voltar». */
  'aria-label'?: string
}

/** Controlo de navegação «Voltar» com superfície de botão (#867). */
export function VoltarButton({
  onClick,
  label = 'Voltar',
  className = '',
  'aria-label': ariaLabel,
}: Props) {
  return (
    <Button
      type="button"
      variant="secondary"
      onClick={onClick}
      className={className}
      aria-label={ariaLabel ?? label}
    >
      <span aria-hidden>←</span>
      {label}
    </Button>
  )
}
