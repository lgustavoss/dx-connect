import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ApiError,
  atendentes,
  relatorios,
  setores,
  type Atendentes,
  type Relatorios,
  type Setores,
} from '../api/client'
import { RelatoriosNav } from '../components/relatorios/RelatoriosNav'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'

function formatarData(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR')
  } catch {
    return iso
  }
}

export function RelatoriosChats() {
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const [de, setDe] = useState(searchParams.get('de') ?? '')
  const [ate, setAte] = useState(searchParams.get('ate') ?? '')
  const [setorId, setSetorId] = useState<number | ''>(() => {
    const v = searchParams.get('setor_id')
    return v ? Number(v) : ''
  })
  const [atendenteId, setAtendenteId] = useState<number | ''>(() => {
    const v = searchParams.get('atendente_filtro_id')
    return v ? Number(v) : ''
  })
  const [data, setData] = useState<Relatorios.ChatsResponse | null>(null)
  const [setoresLista, setSetoresLista] = useState<Setores.Setor[]>([])
  const [atendentesLista, setAtendentesLista] = useState<Atendentes.Atendente[]>([])
  const [loading, setLoading] = useState(true)
  const [exportando, setExportando] = useState(false)
  const [semPermissao, setSemPermissao] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const filtrosApi = useMemo(
    () => ({
      de: de || undefined,
      ate: ate || undefined,
      setor_id: setorId === '' ? undefined : setorId,
      atendente_filtro_id: atendenteId === '' ? undefined : atendenteId,
    }),
    [de, ate, setorId, atendenteId],
  )

  useEffect(() => {
    Promise.all([
      setores.list({ limit: 100, ordenar_por: 'nome', ordem: 'asc' }),
      atendentes.list({ limit: 100, ordenar_por: 'nome', ordem: 'asc' }),
    ])
      .then(([s, a]) => {
        setSetoresLista(s.items)
        setAtendentesLista(a.items)
      })
      .catch(() => undefined)
  }, [])

  const carregar = useCallback(() => {
    setLoading(true)
    setError(null)
    setSemPermissao(false)
    relatorios
      .chats(filtrosApi)
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setSemPermissao(true)
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Não foi possível carregar o relatório.')
        setError(m.titulo)
        toast.showError(mensagemFalhaParaToast(m))
      })
      .finally(() => setLoading(false))
  }, [filtrosApi, toast])

  useEffect(() => {
    carregar()
  }, [carregar])

  const aplicarFiltros = () => {
    const params = new URLSearchParams()
    if (de) params.set('de', de)
    if (ate) params.set('ate', ate)
    if (setorId !== '') params.set('setor_id', String(setorId))
    if (atendenteId !== '') params.set('atendente_filtro_id', String(atendenteId))
    setSearchParams(params, { replace: true })
    carregar()
  }

  const exportarCsv = async () => {
    setExportando(true)
    try {
      const blob = await relatorios.exportChatsCsv(filtrosApi)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `relatorio-chats-${ate || 'periodo'}.csv`
      a.click()
      URL.revokeObjectURL(url)
      toast.showSuccess('CSV exportado com sucesso.')
    } catch (err) {
      const m = interpretarFalhaCarregamento(err, 'Falha ao exportar CSV.')
      toast.showError(mensagemFalhaParaToast(m))
    } finally {
      setExportando(false)
    }
  }

  if (semPermissao) {
    return (
      <PageContainer>
        <SemPermissao
          title="Relatórios de chats são exclusivos para administradores."
          voltarPara="/dashboard/chats"
          voltarLabel="Voltar ao dashboard de WhatsApp"
        />
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Relatórios"
        subtitle="Pré-visualização e exportação CSV (admin)"
        actions={
          <div className="flex flex-wrap gap-2">
            <Link to="/dashboard/chats">
              <Button variant="secondary">Dashboard WhatsApp</Button>
            </Link>
            <Button type="button" loading={exportando} onClick={exportarCsv}>
              Exportar CSV
            </Button>
          </div>
        }
      />

      <RelatoriosNav />

      <Card className="mb-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end">
          <label className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-400">
            De
            <input
              type="date"
              value={de}
              onChange={(e) => setDe(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-400">
            Até
            <input
              type="date"
              value={ate}
              onChange={(e) => setAte(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-400">
            Setor
            <select
              value={setorId}
              onChange={(e) => setSetorId(e.target.value ? Number(e.target.value) : '')}
              className="min-w-[10rem] rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
            >
              <option value="">Todos</option>
              {setoresLista.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nome}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-400">
            Atendente
            <select
              value={atendenteId}
              onChange={(e) => setAtendenteId(e.target.value ? Number(e.target.value) : '')}
              className="min-w-[10rem] rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
            >
              <option value="">Todos</option>
              {atendentesLista.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nome}
                </option>
              ))}
            </select>
          </label>
          <Button type="button" onClick={aplicarFiltros}>
            Aplicar filtros
          </Button>
        </div>
      </Card>

      {loading ? (
        <Card>
          <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
        </Card>
      ) : error ? (
        <Card>
          <p className="text-slate-600 dark:text-slate-300">{error}</p>
        </Card>
      ) : data ? (
        <Card title={`Pré-visualização (${data.itens.length} de ${data.total} chats)`}>
          {data.itens.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400">Nenhum chat no período/filtros selecionados.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[960px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                    <th className="px-2 py-2">Protocolo</th>
                    <th className="px-2 py-2">Cliente</th>
                    <th className="px-2 py-2">Estado</th>
                    <th className="px-2 py-2">Setor</th>
                    <th className="px-2 py-2">Atendente</th>
                    <th className="px-2 py-2">Empresa</th>
                    <th className="px-2 py-2">Aberto</th>
                    <th className="px-2 py-2">Encerrado</th>
                    <th className="px-2 py-2">Nota</th>
                  </tr>
                </thead>
                <tbody>
                  {data.itens.map((row) => (
                    <tr key={row.protocolo} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="px-2 py-2 font-medium">{row.protocolo}</td>
                      <td className="max-w-xs truncate px-2 py-2">{row.cliente_nome || row.wa_id}</td>
                      <td className="px-2 py-2">{row.estado_rotulo}</td>
                      <td className="px-2 py-2">{row.setor_nome || '—'}</td>
                      <td className="px-2 py-2">{row.atendente_nome || '—'}</td>
                      <td className="px-2 py-2">{row.empresa_nome || '—'}</td>
                      <td className="whitespace-nowrap px-2 py-2">{formatarData(row.aberto_em)}</td>
                      <td className="whitespace-nowrap px-2 py-2">{formatarData(row.encerrado_em)}</td>
                      <td className="px-2 py-2">{row.avaliacao_nota ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      ) : null}
    </PageContainer>
  )
}
