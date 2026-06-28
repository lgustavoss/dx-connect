import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, respostasProntas, type RespostasProntas } from '../api/client'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { ListaAcoesVerEditar } from '../components/ui/ListaAcoesVerEditar'
import { useToast } from '../components/ui/Toast'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

type Coluna = 'titulo' | 'ordem' | 'ativo'

export function RespostasProntasPage({ embedded = false }: { embedded?: boolean }) {
  const navigate = useNavigate()
  const toast = useToast()
  const { ordenarPor, ordem: ordemLista, aoOrdenarColuna, sortParams } = useOrdenacaoLista<Coluna>()
  const [list, setList] = useState<RespostasProntas.Resposta[]>([])
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
  }, [debouncedBusca, incluirInativos, ordenarPor, ordemLista])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    respostasProntas
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
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos a lista de respostas prontas.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, incluirInativos, page, sortParams, toast])

  useEffect(() => {
    load()
  }, [load])

  async function handleDelete(id: number) {
    if (!window.confirm('Excluir esta resposta pronta?')) return
    try {
      await respostasProntas.delete(id)
      toast.showSuccess('Resposta pronta excluída.')
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível excluir.'))
    }
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para gerenciar respostas prontas."
      voltarPara="/"
      voltarLabel="Voltar para o Dashboard"
    />
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="Respostas prontas"
      subtitle="Macros reutilizáveis no ticket — globais ou por setor."
      actions={<Button onClick={() => navigate('/respostas-prontas/novo')}>Nova resposta</Button>}
    >
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder="Buscar por título ou texto"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
        />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhuma resposta cadastrada.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel coluna="titulo" rotulo="Título" ordenarPor={ordenarPor} ordem={ordemLista} aoOrdenar={aoOrdenarColuna} />
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">Escopo</th>
                  <CabecalhoOrdenavel coluna="ordem" rotulo="Ordem" ordenarPor={ordenarPor} ordem={ordemLista} aoOrdenar={aoOrdenarColuna} />
                  <CabecalhoOrdenavel coluna="ativo" rotulo="Situação" ordenarPor={ordenarPor} ordem={ordemLista} aoOrdenar={aoOrdenarColuna} />
                  <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((item) => (
                  <tr
                    key={item.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/respostas-prontas/${item.id}`)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        navigate(`/respostas-prontas/${item.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/50 focus:outline-none focus-visible:bg-slate-100/80 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 font-medium text-slate-800 sm:px-6 dark:text-slate-100">{item.titulo}</td>
                    <td className="px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">
                      {item.setor_nome ?? 'Global (todos os setores)'}
                    </td>
                    <td className="px-4 py-3.5 tabular-nums text-slate-600 sm:px-6 dark:text-slate-400">{item.ordem}</td>
                    <td className="px-4 py-3.5 sm:px-6">{item.ativo ? 'Ativo' : 'Inativo'}</td>
                    <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                      <ListaAcoesVerEditar
                        onVer={() => navigate(`/respostas-prontas/${item.id}`)}
                        onEditar={() => navigate(`/respostas-prontas/${item.id}/editar`)}
                        onExcluir={() => handleDelete(item.id)}
                        verLabel="Visualizar resposta"
                        editarLabel="Editar resposta"
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
