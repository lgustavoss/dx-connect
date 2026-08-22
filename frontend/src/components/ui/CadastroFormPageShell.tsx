import type { ReactNode } from 'react'
import { PageContainer } from './PageContainer'
import { VoltarButton } from './VoltarButton'

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
        <VoltarButton onClick={onVoltar} />
      </div>
      {children}
    </PageContainer>
  )
}
