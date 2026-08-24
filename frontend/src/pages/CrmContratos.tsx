import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ApiError,
  atendentes,
  comercialContratos,
  type Atendentes,
  type ComercialContrato,
} from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { textoDiasFidelidade } from '../components/crm/CrmContratoCard'
import { maskCnpjCpf } from '../utils/maskCnpjCpf'
import { SemPermissao } from './SemPermissao'

const STATUS_LABEL: Record<string, string> = {
  rascunho: 'Rascunho',
  enviado: 'Enviado',
  assinado: 'Assinado',
  cancelado: 'Cancelado',
  renovado: 'Renovado',
}

const STATUS_FILTROS = ['', 'rascunho', 'enviado', 'assinado', 'cancelado'] as const

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso.includes('T') ? iso : `${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('pt-BR')
}

function classeDias(dias: number | null | undefined): string {
  if (dias == null) return 'text-slate-500'
  if (dias < 0) return 'text-red-700 dark:text-red-300'
  if (dias <= 30) return 'text-amber-800 dark:text-amber-200'
  return 'text-slate-700 dark:text-slate-300'
}

export function CrmContratos() {
  const toast = useToast()
  const { isAdmin } = useAuth()
  const [list, setList] = useState<ComercialContrato.Contrato[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [status, setStatus] = useState('')
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [responsavelId, setResponsavelId] = useState<number | ''>('')
  const [responsaveis, setResponsaveis] = useState<Atendentes.Atendente[]>([])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    if (!isAdmin) return
    atendentes
      .list({ limit: 100, offset: 0 })
      .then(({ items }) => {
        setResponsaveis(items.filter((a) => a.ativo && (a.role === 'comercial' || a.role === 'admin')))
      })
      .catch(() => setResponsaveis([]))
  }, [isAdmin])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    comercialContratos
      .list({
        status: status || undefined,
        cnpj: debouncedBusca || undefined,
        responsavel_id: isAdmin && responsavelId !== '' ? responsavelId : undefined,
      })
      .then(setList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setList([])
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os contratos.'))
        setList([])
      })
      .finally(() => setLoading(false))
  }, [status, debouncedBusca, responsavelId, isAdmin, toast])

  useEffect(() => {
    load()
  }, [load])

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para ver contratos."
        detail="A lista de contratos é só para o perfil comercial e administradores."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-6xl space-y-4 pb-10">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Contratos</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {isAdmin
            ? 'Todos os contratos da instância. Filtre por responsável ou abra a negociação para gerar, enviar ou assinar.'
            : 'Contratos das suas negociações. Abra a negociação para gerar, enviar ou assinar.'}
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-wrap gap-2">
          {STATUS_FILTROS.map((s) => (
            <button
              key={s || 'todos'}
              type="button"
              onClick={() => setStatus(s)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                status === s
                  ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200'
              }`}
            >
              {s ? STATUS_LABEL[s] : 'Todos'}
            </button>
          ))}
        </div>
        <div className="min-w-[200px] flex-1">
          <Input
            label="CNPJ ou razão social"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Filtrar…"
          />
        </div>
        {isAdmin ? (
          <div className="min-w-[200px]">
            <Select
              label="Responsável"
              value={responsavelId === '' ? '' : String(responsavelId)}
              onChange={(v) => setResponsavelId(v === '' ? '' : Number(v))}
              options={responsaveis.map((a) => ({ value: String(a.id), label: a.nome }))}
              includeEmpty
              emptyLabel="Todos"
            />
          </div>
        ) : null}
      </div>

      <Card>
        {loading ? (
          <p className="text-slate-500">Carregando…</p>
        ) : list.length === 0 ? (
          <div className="space-y-2 text-sm text-slate-500">
            {status || debouncedBusca || responsavelId !== '' ? (
              <p>Nenhum contrato encontrado com esses filtros.</p>
            ) : (
              <>
                <p>Ainda não há contratos. O documento é gerado na negociação do CRM, por CNPJ.</p>
                <p>
                  <Link
                    to="/crm/leads"
                    className="font-medium text-cyan-700 hover:underline dark:text-cyan-400"
                  >
                    Abrir o CRM
                  </Link>
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Status</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">CNPJ</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Responsável</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Fidelidade</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Negociação</th>
                </tr>
              </thead>
              <tbody>
                {list.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100 dark:border-slate-800/80">
                    <td className="px-3 py-2.5">
                      <span className="font-medium text-slate-900 dark:text-slate-100">
                        {STATUS_LABEL[row.status] || row.status}
                      </span>
                      <div className="text-xs text-slate-500">#{row.id}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-slate-900 dark:text-slate-100">
                        {row.razao_social || '—'}
                      </div>
                      <div className="text-xs text-slate-500">
                        {row.cnpj ? maskCnpjCpf(row.cnpj) : 'sem CNPJ'}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300">
                      {row.responsavel_nome || '—'}
                    </td>
                    <td className={`px-3 py-2.5 ${classeDias(row.dias_restantes_fidelidade)}`}>
                      {textoDiasFidelidade(row.dias_restantes_fidelidade)}
                      <div className="text-xs text-slate-500">até {formatDate(row.data_fim_fidelidade)}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      {row.negociacao_id ? (
                        <Link
                          to={`/crm/negociacoes/${row.negociacao_id}`}
                          className="font-medium text-cyan-700 hover:underline dark:text-cyan-400"
                        >
                          {row.lead_nome || `Negociação #${row.negociacao_id}`}
                        </Link>
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
    </div>
  )
}
