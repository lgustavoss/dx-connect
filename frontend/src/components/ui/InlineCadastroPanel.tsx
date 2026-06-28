import { useEffect, useRef, type ReactNode } from 'react'
import { Card } from './Card'
import { Button } from './Button'

type PanelProps = {
  title: string
  className?: string
  children: ReactNode
  /** Rola suavemente até o formulário ao abrir. */
  scrollIntoView?: boolean
}

export function InlineCadastroPanel({ title, className = '', children, scrollIntoView = true }: PanelProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!scrollIntoView) return
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [scrollIntoView, title])

  return (
    <div ref={ref} className="scroll-mt-24">
      <Card title={title} className={className}>
        {children}
      </Card>
    </div>
  )
}

type FooterProps = {
  onCancel: () => void
  saving?: boolean
  submitLabel?: string
}

export function InlineCadastroFooter({ onCancel, saving, submitLabel = 'Salvar' }: FooterProps) {
  return (
    <div className="mt-6 flex flex-col-reverse gap-2 border-t border-slate-200 pt-4 dark:border-slate-800 sm:flex-row sm:justify-end">
      <Button type="button" variant="secondary" className="w-full sm:w-auto" onClick={onCancel}>
        Cancelar
      </Button>
      <Button type="submit" loading={saving} className="w-full sm:w-auto">
        {submitLabel}
      </Button>
    </div>
  )
}
