import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { CabecalhoOrdenavel } from '../../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../../hooks/useOrdenacaoLista'
import { ApiError, saasClientes, type SaasClientes } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Select } from '../../components/ui/Select'
import { ListaAcoesVerEditar } from '../../components/ui/ListaAcoesVerEditar'
import { useToast } from '../../components/ui/Toast'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../../components/ui/BarraBuscaPaginacao'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { SemPermissao } from '../SemPermissao'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import {
  STATUS_CLIENTE_SAAS,
  badgeClassStatusClienteSaaS,
  hrefInstanciaCliente,
  labelStatusClienteSaaS,
} from '../../lib/saasControlPlane'

type Coluna = 'nome' | 'slug' | 'status' | 'data_renovacao'

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = iso.slice(0, 10)
  const [y, m, day] = d.split('-')
  if (!y || !m || !day) return iso
  return `${day}/${m}/${y}`
}

export function SaasLicencas({ embedded = false }: { embedded?: boolean }) {
  const navigate = useNavigate()
  const toast = useToast()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<Coluna>()
  const [list, setList] = useState<SaasClientes.Cliente[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [statusFiltro, setStatusFiltro] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, statusFiltro, ordenarPor, ordem])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    saasClientes
      .list({
        busca: debouncedBusca || undefined,
        status: statusFiltro || undefined,
        ...sortParams,
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
          setList([])
          setTotal(0)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          setList([])
          setTotal(0)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos a lista de licenças.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, page, sortParams, statusFiltro, toast])

  useEffect(() => {
    load()
  }, [load])

  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel de licenças não disponível nesta instância."
        detail="Este módulo só existe na instância comercial DeskRudder (control-plane)."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para gerir licenças SaaS."
      detail="Peça a um administrador acesso ao painel comercial."
      voltarPara="/"
      voltarLabel="Voltar para o Dashboard"
    />
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="Licenças SaaS"
      actions={<Button onClick={() => navigate('/saas/licencas/novo')}>Nova licença</Button>}
    >
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder="Buscar por nome ou slug…"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={
            <div className="min-w-[10rem]">
              <Select
                label="Status"
                labelStyle="overline"
                value={statusFiltro}
                onChange={(v) => setStatusFiltro(String(v))}
                options={STATUS_CLIENTE_SAAS.map((s) => ({ value: s.value, label: s.label }))}
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
          <p className="text-slate-500 dark:text-slate-400">Nenhuma licença cadastrada.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel
                    coluna="nome"
                    rotulo="Cliente"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                  />
                  <CabecalhoOrdenavel
                    coluna="slug"
                    rotulo="Slug"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                  />
                  <CabecalhoOrdenavel
                    coluna="status"
                    rotulo="Status"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                  />
                  <CabecalhoOrdenavel
                    coluna="data_renovacao"
                    rotulo="Renovação"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                  />
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    Instância
                  </th>
                  <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((item) => {
                  const href = hrefInstanciaCliente(item.instancia_url)
                  return (
                    <tr
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => navigate(`/saas/licencas/${item.id}`)}
                      onKeyDown={(ev) => {
                        if (ev.key === 'Enter' || ev.key === ' ') {
                          ev.preventDefault()
                          navigate(`/saas/licencas/${item.id}`)
                        }
                      }}
                      className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/50 focus:outline-none focus-visible:bg-slate-100/80 dark:focus-visible:bg-slate-800/60"
                    >
                      <td className="px-4 py-3.5 sm:px-6">
                        <span className="font-medium text-slate-800 dark:text-slate-100">{item.nome}</span>
                        {item.plano ? (
                          <span className="mt-0.5 block text-xs text-slate-500">{item.plano}</span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-slate-600 sm:px-6 dark:text-slate-300">
                        {item.slug}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 sm:px-6">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClassStatusClienteSaaS(item.status)}`}
                        >
                          {labelStatusClienteSaaS(item.status)}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-300">
                        {formatDate(item.data_renovacao)}
                      </td>
                      <td className="px-4 py-3.5 sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                        {href ? (
                          <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sky-600 hover:underline dark:text-sky-400"
                          >
                            Abrir
                          </a>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                        <ListaAcoesVerEditar
                          onVer={() => navigate(`/saas/licencas/${item.id}`)}
                          onEditar={() => navigate(`/saas/licencas/${item.id}/editar`)}
                          verLabel="Visualizar licença"
                          editarLabel="Editar licença"
                        />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </ConfigListPageShell>
  )
}
