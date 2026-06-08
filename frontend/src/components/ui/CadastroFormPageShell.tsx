import type { ReactNode } from 'react'
import { PageContainer } from './PageContainer'

type Props = {
  children: ReactNode
  onVoltar: () => void
  /** Largura máxima do conteúdo (padrão: listagens simples). */
  wide?: boolean
}

export function CadastroFormPageShell({ children, onVoltar, wide }: Props) {
  return (
    <PageContainer maxWidth={wide ? '6xl' : '5xl'}>
      <div>
        <button
          type="button"
          onClick={onVoltar}
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <span aria-hidden>←</span> Voltar
        </button>
      </div>
      {children}
    </PageContainer>
  )
}
