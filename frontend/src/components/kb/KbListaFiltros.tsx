import { INPUT_FIELD_CLASS } from '../ui/Input'
import { Select } from '../ui/Select'
import { Button } from '../ui/Button'
import { kbCategoriasOpcoesSelect } from '../../lib/kbCategorias'
import type { Kb } from '../../api/client'

const PAGE_SIZE_PADRAO = 20

function IconBusca() {
  return (
    <svg
      className="size-4 shrink-0 text-slate-400 dark:text-slate-500"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
    </svg>
  )
}

const labelOverline =
  'mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400'

type PaginacaoProps = {
  page: number
  total: number
  pageSize?: number
  onPageChange: (page: number) => void
  disabled?: boolean
}

type Props = {
  busca: string
  onBuscaChange: (value: string) => void
  buscaPlaceholder?: string
  categoryId: string
  onCategoryChange: (value: string) => void
  categorias: Kb.Category[]
  disabled?: boolean
  statusId?: string
  onStatusChange?: (value: string) => void
  statusOptions?: { value: string; label: string }[]
  paginacao?: PaginacaoProps
}

function PaginacaoBarra({
  page,
  total,
  pageSize = PAGE_SIZE_PADRAO,
  onPageChange,
  disabled,
}: PaginacaoProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const inicio = total === 0 ? 0 : (page - 1) * pageSize + 1
  const fim = Math.min(page * pageSize, total)

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200/80 pt-4 dark:border-slate-800/80">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        {total > 0 ? (
          <>
            <span className="font-medium text-slate-800 dark:text-slate-200">{total}</span>{' '}
            {total === 1 ? 'resultado' : 'resultados'}
            <span className="mx-2 text-slate-300 dark:text-slate-600">·</span>
            exibindo {inicio}–{fim}
          </>
        ) : (
          'Nenhum resultado'
        )}
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={disabled || page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="px-3 py-1.5 text-xs"
        >
          Anterior
        </Button>
        <span className="min-w-[3.5rem] text-center text-sm tabular-nums text-slate-600 dark:text-slate-400">
          {page} / {totalPages}
        </span>
        <Button
          type="button"
          variant="secondary"
          disabled={disabled || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="px-3 py-1.5 text-xs"
        >
          Próxima
        </Button>
      </div>
    </div>
  )
}

export function KbListaFiltros({
  busca,
  onBuscaChange,
  buscaPlaceholder = 'Buscar por título ou conteúdo…',
  categoryId,
  onCategoryChange,
  categorias,
  disabled,
  statusId,
  onStatusChange,
  statusOptions,
  paginacao,
}: Props) {
  const comStatus = Boolean(statusOptions?.length && onStatusChange)

  return (
    <section className="mb-4 space-y-0">
      <div className="rounded-xl border border-slate-200/90 bg-slate-50/70 p-4 dark:border-slate-800/80 dark:bg-slate-900/40">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-12">
          <div className={comStatus ? 'md:col-span-2 xl:col-span-6' : 'md:col-span-2 xl:col-span-8'}>
            <label htmlFor="kb-filtro-busca" className={labelOverline}>
              Busca
            </label>
            <div className="relative">
              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center">
                <IconBusca />
              </span>
              <input
                id="kb-filtro-busca"
                type="search"
                value={busca}
                onChange={(e) => onBuscaChange(e.target.value)}
                placeholder={buscaPlaceholder}
                disabled={disabled}
                className={`${INPUT_FIELD_CLASS} pl-10`}
              />
            </div>
          </div>

          <div className={comStatus ? 'xl:col-span-3' : 'xl:col-span-4'}>
            <Select
              label="Categoria"
              labelStyle="overline"
              value={categoryId}
              onChange={(v) => onCategoryChange(typeof v === 'string' ? v : String(v))}
              options={kbCategoriasOpcoesSelect(categorias)}
              includeEmpty
              emptyLabel="Todas as categorias"
              placeholder="Todas"
              disabled={disabled}
            />
          </div>

          {comStatus && statusOptions && onStatusChange ? (
            <div className="xl:col-span-3">
              <Select
                label="Status"
                labelStyle="overline"
                value={statusId ?? ''}
                onChange={(v) => onStatusChange(typeof v === 'string' ? v : String(v))}
                options={statusOptions}
                includeEmpty
                emptyLabel="Ativos"
                placeholder="Ativos"
                disabled={disabled}
              />
            </div>
          ) : null}
        </div>

        {paginacao ? <PaginacaoBarra {...paginacao} disabled={disabled || paginacao.disabled} /> : null}
      </div>
    </section>
  )
}

export { PAGE_SIZE_PADRAO as KB_PAGE_SIZE }
