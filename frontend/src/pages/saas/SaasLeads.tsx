import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, saasLeads, type SaasLeads } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../../components/ui/BarraBuscaPaginacao'
import { Card } from '../../components/ui/Card'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { SemPermissao } from '../SemPermissao'

const STATUS_OPTS = [
  { value: 'novo', label: 'Novo' },
  { value: 'em_atendimento', label: 'Em atendimento' },
  { value: 'fechado', label: 'Fechado' },
]

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

export function SaasLeads() {
  const navigate = useNavigate()
  const toast = useToast()
  const [list, setList] = useState<SaasLeads.Lead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, statusFiltro])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    saasLeads
      .list({
        busca: debouncedBusca || undefined,
        status: statusFiltro || undefined,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos os leads comerciais.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, page, statusFiltro, toast])

  useEffect(() => {
    load()
  }, [load])

  if (indisponivel) {
    return (
      <SemPermissao
        title="Leads comerciais não disponíveis nesta instância."
        detail="Este módulo só existe na instância comercial DeskRudder."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  return (
    <ConfigListPageShell
      forbidden={forbidden}
      denied={
        <SemPermissao
          title="Você não tem permissão para ver leads comerciais."
          voltarPara="/"
          voltarLabel="Voltar para o Dashboard"
        />
      }
      title="Leads comerciais"
    >
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder="Buscar por nome, e-mail ou empresa…"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={
            <div className="min-w-[10rem] shrink-0">
              <Select
                aria-label="Filtrar por status"
                value={statusFiltro}
                onChange={(v) => setStatusFiltro(String(v))}
                options={STATUS_OPTS}
                includeEmpty
                emptyLabel="Todos"
                placeholder="Status"
                disabled={loading}
              />
            </div>
          }
        />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum lead ainda.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Contacto</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Empresa</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Status</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Quando</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((lead) => (
                  <tr
                    key={lead.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/saas/leads/${lead.id}`)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        navigate(`/saas/leads/${lead.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/50"
                  >
                    <td className="px-4 py-3.5 sm:px-6">
                      <span className="font-medium text-slate-800 dark:text-slate-100">{lead.nome}</span>
                      <span className="mt-0.5 block text-xs text-slate-500">{lead.email}</span>
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-300">
                      {lead.empresa || '—'}
                    </td>
                    <td className="px-4 py-3.5 sm:px-6">
                      <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                        {STATUS_OPTS.find((s) => s.value === lead.status)?.label ?? lead.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-300">
                      {formatWhen(lead.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </ConfigListPageShell>
  )
}
