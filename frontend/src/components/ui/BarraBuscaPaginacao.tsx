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
  disabled?: boolean
  extra?: React.ReactNode
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
}: Props) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const inicio = total === 0 ? 0 : (page - 1) * pageSize + 1
  const fim = Math.min(page * pageSize, total)

  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
      <div className="flex min-w-0 flex-1 flex-col gap-2 sm:max-w-2xl sm:flex-row sm:items-end">
        <input
          type="search"
          value={busca}
          onChange={(e) => onBuscaChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={`${INPUT_FIELD_CLASS} min-h-[2.5rem] text-sm`}
          aria-label="Buscar na listagem"
        />
        {extra}
      </div>
      <div className="flex min-h-[2.5rem] flex-wrap items-center justify-end gap-2 text-sm text-slate-600 dark:text-slate-300">
        <span className="whitespace-nowrap">
          {total > 0 ? `${inicio}–${fim} de ${total}` : '0 resultados'}
        </span>
        <Button
          type="button"
          variant="secondary"
          disabled={disabled || page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="px-2 py-1 text-xs"
        >
          Anterior
        </Button>
        <span className="tabular-nums">
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
}
