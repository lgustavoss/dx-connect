import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { FuncionariosRede } from '../api/client'
import { Button } from './ui/Button'
import { IconEye } from './ui/IconEye'

const tipoLabel: Record<string, string> = {
  socio: 'Sócio',
  supervisor: 'Supervisor',
  colaborador: 'Colaborador',
}

export type FuncionariosEmpresaListaProps = {
  items: FuncionariosRede.Funcionario[]
  loading: boolean
  emptyMessage?: string
  emptyAction?: ReactNode
}

export function FuncionariosEmpresaLista({
  items,
  loading,
  emptyMessage = 'Nenhum funcionário vinculado a esta empresa.',
  emptyAction,
}: FuncionariosEmpresaListaProps) {
  if (loading && items.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Carregando funcionários...</p>
  }
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-center dark:border-slate-600">
        <p className="text-sm text-slate-500 dark:text-slate-400">{emptyMessage}</p>
        {emptyAction}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
            <th className="px-4 py-3 sm:px-6">Nome</th>
            <th className="px-4 py-3 sm:px-6">E-mail</th>
            <th className="px-4 py-3 sm:px-6">Tipo</th>
            <th className="w-px px-4 py-3 text-right sm:px-6">
              <span className="sr-only">Abrir</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {items.map((f) => (
            <tr
              key={f.id}
              className="transition-colors hover:bg-slate-50/80 dark:hover:bg-white/40"
            >
              <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-100 sm:px-6">
                {f.nome}
              </td>
              <td
                className="max-w-[14rem] truncate px-4 py-3 text-slate-600 dark:text-slate-300 sm:px-6"
                title={f.email}
              >
                {f.email}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-600 dark:text-slate-300 sm:px-6">
                {tipoLabel[f.tipo] ?? f.tipo}
              </td>
              <td className="px-4 py-3 text-right sm:px-6">
                <Link to={`/funcionarios-rede/${f.id}`} aria-label={`Ver ${f.nome}`}>
                  <Button
                    type="button"
                    variant="ghost"
                    className="inline-flex size-9 items-center justify-center p-0"
                  >
                    <IconEye className="size-5 shrink-0" ariaHidden={false} />
                  </Button>
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
