import { useState, useEffect, useCallback } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { useNavigate } from 'react-router-dom'
import { ApiError, redes, type Redes } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { IconPencil } from '../components/ui/IconPencil'
import { IconTrash } from '../components/ui/IconTrash'
import { useToast } from '../components/ui/Toast'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'

type ColunaRede = 'nome' | 'ativo'

export function Redes() {
  const navigate = useNavigate()
  const toast = useToast()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaRede>()
  const [list, setList] = useState<Redes.Rede[]>([])
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

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    redes
      .list({
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
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos a lista de redes.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, incluirInativos, page, sortParams, toast])

  useEffect(() => {
    load()
  }, [load])

  async function handleDelete(id: number) {
    if (!confirm('Excluir esta rede?')) return
    try {
      await redes.delete(id)
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir a rede.'))
    }
  }

  if (forbidden) {
    return (
      <PageContainer>
        <SemPermissao
          title="Você não tem permissão para listar redes."
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
        title="Redes"
        actions={<Button onClick={() => navigate('/redes/novo')}>Nova rede</Button>}
      />
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={(v) => {
            setBusca(v)
            setPage(1)
          }}
          placeholder="Buscar por nome da rede"
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
          <p className="text-slate-500 dark:text-slate-400">Nenhuma rede encontrada.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
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
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 sm:px-6 dark:text-slate-400">
                    Retaguarda
                  </th>
                  <CabecalhoOrdenavel
                    coluna="ativo"
                    rotulo="Situação"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      setPage(1)
                      aoOrdenarColuna(c)
                    }}
                  />
                  <th className="w-px whitespace-nowrap px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500 sm:px-6 dark:text-slate-400">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((r) => (
                  <tr
                    key={r.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/redes/${r.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        navigate(`/redes/${r.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50/90 focus:outline-none focus-visible:bg-slate-100/80 dark:hover:bg-slate-800/50 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 sm:px-6">
                      <span className={`font-medium ${r.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>{r.nome}</span>
                    </td>
                    <td className="max-w-[14rem] truncate px-4 py-3.5 font-mono text-xs text-slate-600 sm:px-6 dark:text-slate-400" title={r.login_retaguarda ?? undefined}>
                      {r.login_retaguarda?.trim() ? r.login_retaguarda : '—'}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 sm:px-6">
                      {r.ativo ? (
                        <span className="text-slate-600 dark:text-slate-400">Ativo</span>
                      ) : (
                        <span className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-400">Inativo</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-right sm:px-6" onClick={(e) => e.stopPropagation()}>
                      <div className="inline-flex gap-1.5">
                        <Button variant="ghost" onClick={() => navigate(`/redes/${r.id}/editar`)} aria-label="Editar rede">
                          <IconPencil ariaHidden={false} />
                        </Button>
                        <Button variant="ghost" onClick={() => handleDelete(r.id)} aria-label="Excluir rede">
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
