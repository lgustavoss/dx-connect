import { useState, useEffect, useCallback } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { audit, type Audit } from '../api/client'
import { Card } from '../components/ui/Card'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { Select } from '../components/ui/Select'

const entityTypeLabel: Record<string, string> = {
  rede: 'Rede',
  empresa: 'Empresa',
  setor: 'Setor',
  atendente: 'Atendente',
  funcionario_rede: 'Funcionário da rede',
  status_ticket: 'Status de ticket',
}

const actionLabel: Record<string, string> = {
  create: 'Cadastro',
  update: 'Alteração',
}

type ColunaAudit = 'created_at' | 'entity_type' | 'entity_id' | 'action' | 'atendente'

export function Auditoria() {
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaAudit>()
  const [list, setList] = useState<Audit.AuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [loading, setLoading] = useState(true)
  const [filtroTipo, setFiltroTipo] = useState<string>('')

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  const load = useCallback(() => {
    setLoading(true)
    audit
      .list({
        entity_type: filtroTipo || undefined,
        busca: debouncedBusca || undefined,
        ...sortParams,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
      })
      .catch(() => {
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, filtroTipo, page, sortParams])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Auditoria</h1>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Registro de cadastros e alterações: quem fez e quando.
      </p>
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={(v) => {
            setBusca(v)
            setPage(1)
          }}
          placeholder="Buscar por tipo ou nome do atendente"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={
            <div className="w-full min-w-0 sm:w-auto sm:min-w-[220px]">
              <Select
                label="Tipo"
                value={filtroTipo}
                onChange={(v) => {
                  setFiltroTipo(typeof v === 'string' ? v : String(v))
                  setPage(1)
                }}
                options={Object.entries(entityTypeLabel).map(([k, v]) => ({ value: k, label: v }))}
                includeEmpty
                emptyLabel="Todos"
                placeholder="Todos"
              />
            </div>
          }
        />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum registro de auditoria.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700/80 text-slate-600 dark:text-slate-400">
                  <CabecalhoOrdenavel
                    coluna="created_at"
                    rotulo="Data/Hora"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      setPage(1)
                      aoOrdenarColuna(c)
                    }}
                    className="pb-2 pr-4 font-medium normal-case"
                  />
                  <CabecalhoOrdenavel
                    coluna="entity_type"
                    rotulo="Tipo"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      setPage(1)
                      aoOrdenarColuna(c)
                    }}
                    className="pb-2 pr-4 font-medium normal-case"
                  />
                  <CabecalhoOrdenavel
                    coluna="entity_id"
                    rotulo="ID"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      setPage(1)
                      aoOrdenarColuna(c)
                    }}
                    className="pb-2 pr-4 font-medium normal-case"
                  />
                  <CabecalhoOrdenavel
                    coluna="action"
                    rotulo="Ação"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      setPage(1)
                      aoOrdenarColuna(c)
                    }}
                    className="pb-2 pr-4 font-medium normal-case"
                  />
                  <CabecalhoOrdenavel
                    coluna="atendente"
                    rotulo="Quem"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      setPage(1)
                      aoOrdenarColuna(c)
                    }}
                    className="pb-2 pr-4 font-medium normal-case"
                  />
                </tr>
              </thead>
              <tbody>
                {list.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 dark:border-slate-700/60">
                    <td className="py-2 pr-4 text-slate-600 dark:text-slate-400">
                      {r.created_at ? new Date(r.created_at).toLocaleString('pt-BR') : '—'}
                    </td>
                    <td className="py-2 pr-4">{entityTypeLabel[r.entity_type] ?? r.entity_type}</td>
                    <td className="py-2 pr-4 font-mono text-slate-600 dark:text-slate-400">{r.entity_id}</td>
                    <td className="py-2 pr-4">{actionLabel[r.action] ?? r.action}</td>
                    <td className="py-2">{r.atendente_nome ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
