import { useState, useEffect, useCallback } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { useNavigate } from 'react-router-dom'
import { ApiError, empresas as apiEmpresas, redes, type Empresas, type Redes } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { ListaAcoesVerEditar } from '../components/ui/ListaAcoesVerEditar'
import { useToast } from '../components/ui/Toast'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { maskCnpjCpf } from '../utils/maskCnpjCpf'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'

type ColunaEmpresa = 'nome' | 'cnpj_cpf' | 'rede'

export function Empresas() {
  const navigate = useNavigate()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaEmpresa>()
  const toast = useToast()
  const [list, setList] = useState<Empresas.Empresa[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [redesList, setRedesList] = useState<Redes.Rede[]>([])
  const [loading, setLoading] = useState(true)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [forbidden, setForbidden] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, incluirInativos, ordenarPor, ordem])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    apiEmpresas
      .list<Empresas.Empresa>({
        incluir_inativos: incluirInativos,
        busca: debouncedBusca || undefined,
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
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos a lista de empresas.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, incluirInativos, page, sortParams, toast])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    coletarTodasPaginas<Redes.Rede>((o, l) => redes.list({ incluir_inativos: true, offset: o, limit: l })).then(
      setRedesList,
    )
  }, [])

  async function handleDelete(id: number) {
    if (!confirm('Excluir esta empresa?')) return
    try {
      await apiEmpresas.delete(id)
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir a empresa.'))
    }
  }

  if (forbidden) {
    return (
      <PageContainer>
        <SemPermissao
          title="Você não tem permissão para listar empresas."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara="/"
          voltarLabel="Voltar para o Dashboard"
        />
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Empresas"
        actions={<Button onClick={() => navigate('/empresas/novo')}>Nova empresa</Button>}
      />

      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder="Buscar por nome, razão social, CNPJ ou e-mail"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
        />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhuma empresa encontrada.</p>
        ) : (
          <div className="-mx-2 overflow-x-auto rounded-lg">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <CabecalhoOrdenavel
                    coluna="nome"
                    rotulo="Empresa"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="py-2.5 pl-2 pr-4"
                  />
                  <CabecalhoOrdenavel
                    coluna="cnpj_cpf"
                    rotulo="CNPJ / CPF"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="py-2.5 pr-4"
                  />
                  <CabecalhoOrdenavel
                    coluna="rede"
                    rotulo="Rede"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="min-w-[8rem] py-2.5 pr-4"
                  />
                  <th className="w-px py-2.5 pr-2 text-right" aria-hidden />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((e) => {
                  const redeNome = redesList.find((r) => r.id === e.rede_id)?.nome ?? '—'
                  const doc = e.cnpj_cpf ? maskCnpjCpf(e.cnpj_cpf) : '—'
                  return (
                    <tr
                      key={e.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => navigate(`/empresas/${e.id}`)}
                      onKeyDown={(ev) => {
                        if (ev.key === 'Enter' || ev.key === ' ') {
                          ev.preventDefault()
                          navigate(`/empresas/${e.id}`)
                        }
                      }}
                      className="cursor-pointer transition-colors hover:bg-slate-50/90 focus-within:bg-slate-50/90 dark:hover:bg-white/50 dark:focus-within:bg-slate-800/50"
                    >
                      <td className="max-w-0 py-3 pl-2 pr-4">
                        <div className="flex min-w-0 flex-wrap items-center gap-2">
                          <span className={`truncate font-medium ${e.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>
                            {e.nome}
                          </span>
                          {!e.ativo && (
                            <span className="shrink-0 rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-400">
                              Inativo
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="whitespace-nowrap py-3 pr-4 font-mono text-xs text-slate-600 tabular-nums dark:text-slate-400">
                        {doc}
                      </td>
                      <td className="max-w-[14rem] truncate py-3 pr-4 text-slate-600 dark:text-slate-400" title={redeNome}>
                        {redeNome}
                      </td>
                      <td className="py-3 pr-2 text-right" onClick={(ev) => ev.stopPropagation()}>
                        <ListaAcoesVerEditar
                          onVer={() => navigate(`/empresas/${e.id}`)}
                          onEditar={() => navigate(`/empresas/${e.id}/editar`)}
                          onExcluir={() => handleDelete(e.id)}
                          verLabel="Visualizar empresa"
                          editarLabel="Editar empresa"
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
    </PageContainer>
  )
}
