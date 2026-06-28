import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ApiError,
  funcionariosRede,
  type FuncionariosRede as FuncionarioRedeTipo,
} from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { IconPencil } from '../components/ui/IconPencil'
import { IconTrash } from '../components/ui/IconTrash'
import { useToast } from '../components/ui/Toast'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'

type Tipo = 'socio' | 'supervisor' | 'colaborador'
type ColunaFuncionario = 'nome' | 'email' | 'tipo'

export function FuncionariosRede() {
  const navigate = useNavigate()
  const toast = useToast()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaFuncionario>()
  const [list, setList] = useState<FuncionarioRedeTipo.Funcionario[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [loading, setLoading] = useState(true)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [forbidden, setForbidden] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  const load = useCallback((override?: { busca?: string; page?: number }) => {
    setLoading(true)
    setForbidden(false)
    const buscaEff = override?.busca !== undefined ? override.busca : debouncedBusca
    const pageEff = override?.page !== undefined ? override.page : page
    funcionariosRede
      .list({
        incluir_inativos: incluirInativos,
        busca: buscaEff.trim() || undefined,
        ...sortParams,
        offset: (pageEff - 1) * PAGE_SIZE_PADRAO,
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
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos a lista de funcionários da rede.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, incluirInativos, page, sortParams, toast])

  useEffect(() => {
    load()
  }, [load])

  async function handleDelete(id: number) {
    if (!confirm('Excluir este funcionário?')) return
    try {
      await funcionariosRede.delete(id)
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir o funcionário.'))
    }
  }

  const tipoLabel = { socio: 'Sócio', supervisor: 'Supervisor', colaborador: 'Colaborador' }

  if (forbidden) {
    return (
      <PageContainer>
        <SemPermissao
          title="Você não tem permissão para listar funcionários da rede."
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
        title="Funcionários da rede"
        actions={<Button onClick={() => navigate('/funcionarios-rede/novo')}>Novo</Button>}
      />
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={(v) => {
            setBusca(v)
            setPage(1)
          }}
          placeholder="Buscar por nome ou e-mail"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={
            <FiltroInativos
              incluirInativos={incluirInativos}
              onChange={(v) => {
                setIncluirInativos(v)
                setPage(1)
              }}
            />
          }
        />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum cadastrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel
                    coluna="nome"
                    rotulo="Nome"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      setPage(1)
                      aoOrdenarColuna(c)
                    }}
                  />
                  <CabecalhoOrdenavel
                    coluna="email"
                    rotulo="E-mail"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      setPage(1)
                      aoOrdenarColuna(c)
                    }}
                  />
                  <CabecalhoOrdenavel
                    coluna="tipo"
                    rotulo="Tipo"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      setPage(1)
                      aoOrdenarColuna(c)
                    }}
                  />
                  <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((f) => (
                  <tr
                    key={f.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/funcionarios-rede/${f.id}`)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        navigate(`/funcionarios-rede/${f.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50/80 focus:outline-none focus-visible:bg-slate-100/80 dark:hover:bg-white/50 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 sm:px-6">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`font-medium ${f.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>{f.nome}</span>
                        {!f.ativo && (
                          <span className="shrink-0 rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-400">
                            Inativo
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="max-w-[14rem] truncate px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400" title={f.email}>
                      {f.email}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">
                      {tipoLabel[f.tipo as Tipo]}
                    </td>
                    <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                      <div className="inline-flex gap-1.5">
                        <Button variant="ghost" onClick={() => navigate(`/funcionarios-rede/${f.id}/editar`)} aria-label="Editar funcionário">
                          <IconPencil ariaHidden={false} />
                        </Button>
                        <Button variant="ghost" onClick={() => handleDelete(f.id)} aria-label="Excluir funcionário">
                          <IconTrash ariaHidden={false} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PageContainer>
  )
}
