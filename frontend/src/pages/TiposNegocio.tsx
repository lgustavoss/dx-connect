import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { ApiError, tiposNegocio, type TiposNegocio } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { ListaAcoesVerEditar } from '../components/ui/ListaAcoesVerEditar'
import { useToast } from '../components/ui/Toast'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

type ColunaTipo = 'nome' | 'ativo'

export function TiposNegocio({ embedded = false }: { embedded?: boolean }) {
  const navigate = useNavigate()
  const toast = useToast()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaTipo>()
  const [list, setList] = useState<TiposNegocio.Tipo[]>([])
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

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, incluirInativos, ordenarPor, ordem])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    tiposNegocio
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
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos a lista de tipos de negócio.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, incluirInativos, page, sortParams, toast])

  useEffect(() => {
    load()
  }, [load])

  async function handleDelete(id: number) {
    if (!confirm('Excluir este tipo de negócio?')) return
    try {
      await tiposNegocio.delete(id)
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir o tipo de negócio.'))
    }
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para listar tipos de negócio."
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
      title="Tipos de negócio"
      actions={<Button onClick={() => navigate('/tipos-negocio/novo')}>Novo tipo</Button>}
    >
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder="Buscar por nome"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
        />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum tipo encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel coluna="nome" rotulo="Nome" ordenarPor={ordenarPor} ordem={ordem} aoOrdenar={aoOrdenarColuna} />
                  <CabecalhoOrdenavel coluna="ativo" rotulo="Situação" ordenarPor={ordenarPor} ordem={ordem} aoOrdenar={aoOrdenarColuna} />
                  <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((t) => (
                  <tr
                    key={t.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/tipos-negocio/${t.id}`)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        navigate(`/tipos-negocio/${t.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/5 focus:outline-none focus-visible:bg-slate-100/80 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 sm:px-6">
                      <span className={`font-medium ${t.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>{t.nome}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 sm:px-6">
                      {t.ativo ? (
                        <span className="text-slate-600 dark:text-slate-400">Ativo</span>
                      ) : (
                        <span className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-400">Inativo</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                      <ListaAcoesVerEditar
                        onVer={() => navigate(`/tipos-negocio/${t.id}`)}
                        onEditar={() => navigate(`/tipos-negocio/${t.id}/editar`)}
                        onExcluir={() => handleDelete(t.id)}
                        verLabel="Visualizar tipo"
                        editarLabel="Editar tipo"
                      />
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
