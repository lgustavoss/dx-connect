import { Button } from './Button'
import { INPUT_FIELD_CLASS } from './Input'

export const PAGE_SIZE_PADRAO = 20

type Props = {
  busca: string
  onBuscaChange: (value: string) => void
  placeholder?: string
  /** Página 1-based */
  page: number
  total: number
  pageSize?: number
  onPageChange: (page: number) => void
  /** Bloqueia só a paginação. O campo de busca permanece editável para não perder o foco (#S202610-0019). */
  disabled?: boolean
  /** Campo à direita da busca (ex.: filtro de natureza). Em tela larga, 30% do espaço restante; a busca fica com 70%. */
  extra?: React.ReactNode
  /** Permanece colado à paginação em qualquer largura (ex.: Ativos/Todos). */
  juntoPaginacao?: React.ReactNode
}

export function BarraBuscaPaginacao({
  busca,
  onBuscaChange,
  placeholder = 'Buscar...',
  page,
  total,
  pageSize = PAGE_SIZE_PADRAO,
  onPageChange,
  disabled,
  extra,
  juntoPaginacao,
}: Props) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const inicio = total === 0 ? 0 : (page - 1) * pageSize + 1
  const fim = Math.min(page * pageSize, total)
  const temExtra = extra != null

  const paginacao = (
    <div className="flex min-h-[2.5rem] max-w-full flex-wrap items-center justify-end gap-2 text-sm text-slate-600 dark:text-slate-300">
      {juntoPaginacao}
      <div className="flex shrink-0 flex-nowrap items-center gap-2">
        <span className="whitespace-nowrap">{total > 0 ? `${inicio}–${fim} de ${total}` : '0 resultados'}</span>
        <Button
          type="button"
          variant="secondary"
          disabled={disabled || page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="px-2 py-1 text-xs"
        >
          Anterior
        </Button>
        <span className="whitespace-nowrap tabular-nums">
          {page} / {totalPages}
        </span>
        <Button
          type="button"
          variant="secondary"
          disabled={disabled || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="px-2 py-1 text-xs"
        >
          Próxima
        </Button>
      </div>
    </div>
  )

  return (
    <div className="@container mb-4" aria-busy={disabled || undefined}>
      <div
        className={
          temExtra
            ? 'grid grid-cols-1 items-center gap-2 @[52rem]:grid-cols-[minmax(0,7fr)_minmax(8rem,3fr)_auto] @[52rem]:gap-x-2'
            : 'grid grid-cols-1 items-center gap-2 @[32rem]:grid-cols-[minmax(0,1fr)_auto] @[32rem]:gap-x-2'
        }
      >
        <div className="min-w-0">
          <input
            type="search"
            value={busca}
            onChange={(e) => onBuscaChange(e.target.value)}
            placeholder={placeholder}
            className={`${INPUT_FIELD_CLASS} min-h-[2.5rem] text-sm`}
            aria-label="Buscar na listagem"
          />
        </div>
        {temExtra ? <div className="min-w-0">{extra}</div> : null}
        <div className={temExtra ? 'flex justify-end @[52rem]:justify-self-end' : 'flex justify-end @[32rem]:justify-self-end'}>
          {paginacao}
        </div>
      </div>
    </div>
  )
}
