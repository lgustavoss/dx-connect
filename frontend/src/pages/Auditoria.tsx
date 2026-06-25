import { useState, useEffect, useCallback } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { ApiError, audit, type Audit } from '../api/client'
import { Card } from '../components/ui/Card'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { Select } from '../components/ui/Select'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

const entityTypeLabel: Record<string, string> = {
  rede: 'Rede',
  empresa: 'Empresa',
  setor: 'Setor',
  atendente: 'Atendente',
  funcionario_rede: 'Funcionário da rede',
  status_ticket: 'Status de ticket',
  ticket: 'Ticket',
  ticket_mensagem: 'Mensagem de ticket',
  whatsapp_chat: 'Chat WhatsApp',
  empresa_pdv: 'PDV',
  export_relatorio: 'Exportação de relatório',
  routing_rule: 'Regra de roteamento',
  sla_policy: 'Política SLA',
  business_calendar: 'Calendário comercial',
  resposta_pronta: 'Resposta pronta',
  ticket_natureza: 'Natureza de ticket',
  ticket_motivo: 'Motivo de ticket',
  pdv_rotulo: 'Rótulo PDV',
  pdv_tipo_acesso_remoto: 'Tipo acesso remoto PDV',
  tipo_negocio: 'Tipo de negócio',
}

const actionLabel: Record<string, string> = {
  create: 'Cadastro',
  update: 'Alteração',
  delete: 'Exclusão',
  assign: 'Atribuição',
  transfer: 'Transferência',
  close: 'Fechamento',
  reopen: 'Reabertura',
  status_change: 'Mudança de status',
  send_email: 'Envio de e-mail',
  view_credential: 'Visualização de credencial',
  reveal_credential: 'Visualização de credencial',
  export: 'Exportação',
  apply: 'Aplicação (roteamento)',
  reorder: 'Reordenação',
  distribuicao_update: 'Distribuição na fila',
}

const ACTION_OPTIONS = Object.entries(actionLabel).map(([value, label]) => ({ value, label }))

type ColunaAudit = 'created_at' | 'entity_type' | 'entity_id' | 'action' | 'atendente'

function formatPayload(payload: Record<string, unknown> | null): string {
  if (!payload || Object.keys(payload).length === 0) return '—'
  try {
    return JSON.stringify(payload, null, 0)
  } catch {
    return '—'
  }
}

export function Auditoria({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaAudit>()
  const [list, setList] = useState<Audit.AuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [loading, setLoading] = useState(true)
  const [exportando, setExportando] = useState(false)
  const [filtroTipo, setFiltroTipo] = useState<string>('')
  const [filtroAcao, setFiltroAcao] = useState<string>('')
  const [de, setDe] = useState('')
  const [ate, setAte] = useState('')
  const [forbidden, setForbidden] = useState(false)
  const [detalhe, setDetalhe] = useState<Audit.AuditLogEntry | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  const filtrosApi = {
    entity_type: filtroTipo || undefined,
    action: filtroAcao || undefined,
    busca: debouncedBusca || undefined,
    de: de || undefined,
    ate: ate || undefined,
  }

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    audit
      .list({
        ...filtrosApi,
        ...sortParams,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
      })
      .catch((err) => {
        setList([])
        setTotal(0)
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos registros de auditoria.'))
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, filtroTipo, filtroAcao, de, ate, page, sortParams, toast])

  useEffect(() => {
    load()
  }, [load])

  const exportarCsv = async () => {
    setExportando(true)
    try {
      const blob = await audit.exportCsv(filtrosApi)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `auditoria-${ate || de || 'periodo'}.csv`
      a.click()
      URL.revokeObjectURL(url)
      toast.showSuccess('CSV exportado com sucesso.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao exportar CSV.'))
    } finally {
      setExportando(false)
    }
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para acessar a auditoria."
      detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
      voltarPara="/"
      voltarLabel="Voltar para o Dashboard"
    />
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="Auditoria"
      subtitle="Trilha de ações sensíveis, cadastros e exportações — quem fez, quando e contexto."
      actions={
        <Button type="button" variant="secondary" loading={exportando} onClick={exportarCsv}>
          Exportar CSV
        </Button>
      }
    >
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={(v) => {
            setBusca(v)
            setPage(1)
          }}
          placeholder="Buscar por tipo, ação, request_id ou atendente"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={
            <div className="flex w-full min-w-0 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
              <div className="w-full min-w-0 sm:w-auto sm:min-w-[200px]">
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
              <div className="w-full min-w-0 sm:w-auto sm:min-w-[200px]">
                <Select
                  label="Ação"
                  value={filtroAcao}
                  onChange={(v) => {
                    setFiltroAcao(typeof v === 'string' ? v : String(v))
                    setPage(1)
                  }}
                  options={ACTION_OPTIONS}
                  includeEmpty
                  emptyLabel="Todas"
                  placeholder="Todas"
                />
              </div>
              <Input
                label="De"
                type="date"
                value={de}
                onChange={(e) => {
                  setDe(e.target.value)
                  setPage(1)
                }}
                className="w-full sm:w-auto"
              />
              <Input
                label="Até"
                type="date"
                value={ate}
                onChange={(e) => {
                  setAte(e.target.value)
                  setPage(1)
                }}
                className="w-full sm:w-auto"
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
                  <th className="pb-2 pr-4 font-medium">Detalhes</th>
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
                    <td className="py-2 pr-4">{r.atendente_nome ?? '—'}</td>
                    <td className="py-2">
                      {(r.payload_json && Object.keys(r.payload_json).length > 0) || r.request_id || r.ip_address ? (
                        <button
                          type="button"
                          className="text-cyan-700 hover:underline dark:text-cyan-300"
                          onClick={() => setDetalhe(r)}
                        >
                          Ver
                        </button>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {detalhe ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="audit-detail-title"
        >
          <Card className="max-h-[85vh] w-full max-w-lg overflow-y-auto p-5">
            <h2 id="audit-detail-title" className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              Registro #{detalhe.id}
            </h2>
            <dl className="mt-4 space-y-2 text-sm">
              {detalhe.request_id ? (
                <div>
                  <dt className="text-slate-500 dark:text-slate-400">Request ID</dt>
                  <dd className="font-mono text-slate-800 dark:text-slate-100">{detalhe.request_id}</dd>
                </div>
              ) : null}
              {detalhe.ip_address ? (
                <div>
                  <dt className="text-slate-500 dark:text-slate-400">IP</dt>
                  <dd className="text-slate-800 dark:text-slate-100">{detalhe.ip_address}</dd>
                </div>
              ) : null}
              {detalhe.payload_json && Object.keys(detalhe.payload_json).length > 0 ? (
                <div>
                  <dt className="text-slate-500 dark:text-slate-400">Payload</dt>
                  <dd className="mt-1 overflow-x-auto rounded-md bg-slate-50 p-2 font-mono text-xs text-slate-800 dark:bg-slate-900/60 dark:text-slate-100">
                    {formatPayload(detalhe.payload_json)}
                  </dd>
                </div>
              ) : null}
            </dl>
            <div className="mt-5 flex justify-end">
              <Button type="button" variant="secondary" onClick={() => setDetalhe(null)}>
                Fechar
              </Button>
            </div>
          </Card>
        </div>
      ) : null}
    </ConfigListPageShell>
  )
}
