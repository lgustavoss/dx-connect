import { useEffect, useState, useCallback, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { atendentes, whatsappChats, type WhatsappChats, type Atendentes } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import { AvaliacaoEstrelas } from '../../components/ui/AvaliacaoEstrelas'
import { rotuloEstadoChat } from '../../lib/whatsappChatMeta'
import {
  buildHistoricoReturnPath,
  marcarWhatsappChatAtivo,
  saveWhatsappListScroll,
  whatsappConversaLink,
} from '../../lib/whatsappListReturn'
import { useWhatsappListScrollRestore } from '../../hooks/useWhatsappListScrollRestore'
import { ChatIniciarConversaModal } from '../../components/chat/ChatIniciarConversaModal'
import { CollapsibleCard } from '../../components/ui/CollapsibleCard'
import { CopiarWaIdButton } from '../../components/chat/CopiarWaIdButton'

const PAGE_SIZE = 15

type FiltroEstadoHistorico =
  | 'finalizados'
  | 'encerrado'
  | 'aguardando_avaliacao'
  | 'em_atendimento'
  | 'aguardando_atendente'
  | 'todos'

export function WhatsappHistorico() {
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const [items, setItems] = useState<WhatsappChats.Chat[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(() => Number(searchParams.get('offset') || 0))
  const [loading, setLoading] = useState(true)
  const [busca, setBusca] = useState(() => searchParams.get('busca') ?? '')
  const [atendentesList, setAtendentesList] = useState<Atendentes.Atendente[]>([])
  const [retomarChat, setRetomarChat] = useState<WhatsappChats.Chat | null>(null)
  const [atendenteId, setAtendenteId] = useState<number | ''>(() => {
    const v = searchParams.get('atendente_id')
    return v ? Number(v) : ''
  })
  const [desde, setDesde] = useState(() => searchParams.get('desde') ?? '')
  const [ate, setAte] = useState(() => searchParams.get('ate') ?? '')
  const [estadoFiltro, setEstadoFiltro] = useState<FiltroEstadoHistorico>(() => {
    const v = searchParams.get('estado')
    return (v as FiltroEstadoHistorico) || 'todos'
  })
  /** Acordeão de filtros avançados só no mobile (#825). */
  const [filtrosAbertos, setFiltrosAbertos] = useState(false)

  const filtrosAvancadosAtivos = useMemo(() => {
    let n = 0
    if (estadoFiltro !== 'todos') n += 1
    if (desde) n += 1
    if (ate) n += 1
    if (atendenteId !== '') n += 1
    return n
  }, [ate, atendenteId, desde, estadoFiltro])

  const historicoReturnPath = useMemo(
    () =>
      buildHistoricoReturnPath({
        busca,
        atendenteId,
        desde,
        ate,
        estado: estadoFiltro,
        offset,
      }),
    [ate, atendenteId, busca, desde, estadoFiltro, offset],
  )

  const syncUrl = useCallback(
    (from: number) => {
      const path = buildHistoricoReturnPath({
        busca,
        atendenteId,
        desde,
        ate,
        estado: estadoFiltro,
        offset: from,
      })
      const qs = path.includes('?') ? path.split('?')[1] : ''
      setSearchParams(qs ? new URLSearchParams(qs) : new URLSearchParams(), { replace: true })
    },
    [ate, atendenteId, busca, desde, estadoFiltro, setSearchParams],
  )

  const load = useCallback(async (from: number) => {
    setLoading(true)
    try {
      const params: Record<string, string | number | undefined> = {
        offset: from,
        limit: PAGE_SIZE,
      }
      if (busca.trim()) params.busca = busca.trim()
      if (atendenteId !== '') params.atendente_id = atendenteId
      if (desde) params.encerramento_inicio = `${desde}T00:00:00`
      if (ate) params.encerramento_fim = `${ate}T23:59:59`
      params.estado = estadoFiltro
      const { items: rows, total: t } = await whatsappChats.encerrados(params)
      setItems(rows)
      setTotal(t)
      setOffset(from)
      syncUrl(from)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao carregar atendimentos.'))
    } finally {
      setLoading(false)
    }
  }, [atendenteId, ate, busca, desde, estadoFiltro, syncUrl, toast])

  useWhatsappListScrollRestore('historico', historicoReturnPath, !loading)

  // Carga inicial (respeita ?offset=). Paginação e «Filtrar» chamam load() explicitamente —
  // não reagir a [load], senão Próxima volta à página 1 (#667).
  useEffect(() => {
    void load(offset)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só mount
  }, [])

  useEffect(() => {
    void atendentes
      .list({ incluir_inativos: true, offset: 0, limit: 100 })
      .then((result) => setAtendentesList(result.items))
      .catch(() => setAtendentesList([]))
  }, [])

  const formatDuration = (chat: WhatsappChats.Chat) => {
    if (!chat.atendimento_inicio_at) return '—'
    if (!chat.encerramento_at) return 'Em curso'
    const start = new Date(chat.atendimento_inicio_at)
    const end = new Date(chat.encerramento_at)
    const diff = Math.max(0, Math.round((end.getTime() - start.getTime()) / 1000))
    const minutes = Math.floor(diff / 60)
    if (minutes < 60) return `${minutes} min`
    const hours = Math.floor(minutes / 60)
    const remain = minutes % 60
    return `${hours}h ${remain}m`
  }

  // Cálculo de páginas
  const paginaAtual = Math.floor(offset / PAGE_SIZE) + 1
  const totalPaginas = Math.ceil(total / PAGE_SIZE)

  const filtrosAvancados = (
    <>
      <div className="grid w-full max-w-full grid-cols-1 gap-3 sm:max-w-2xl sm:grid-cols-2 lg:grid-cols-4">
        <Select
          label="Estado"
          value={estadoFiltro}
          onChange={(value) => setEstadoFiltro(value as FiltroEstadoHistorico)}
          options={[
            { value: 'todos', label: 'Todos' },
            { value: 'em_atendimento', label: 'Em andamento' },
            { value: 'aguardando_atendente', label: 'Aguardando' },
            { value: 'finalizados', label: 'Finalizados' },
          ]}
        />
        <Input
          type="date"
          label="De"
          value={desde}
          onChange={(e) => setDesde(e.target.value)}
        />
        <Input
          type="date"
          label="Até"
          value={ate}
          onChange={(e) => setAte(e.target.value)}
        />
        <div className="min-w-0">
          <Select
            label="Atendente"
            value={atendenteId}
            onChange={(value) => setAtendenteId(value === '' ? '' : Number(value))}
            options={atendentesList.map((a) => ({ value: a.id, label: a.nome }))}
            placeholder="Atendente"
            includeEmpty
            emptyLabel="Atendente"
          />
        </div>
      </div>
      <Button className="w-full sm:w-auto sm:self-end" variant="secondary" onClick={() => void load(0)}>
        Filtrar
      </Button>
    </>
  )

  const campoBusca = (
    <div className="relative min-w-0 flex-1">
      <Input
        placeholder="Buscar por nome, telefone ou protocolo (ex.: #C202604-0001)…"
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        className="pl-10"
        onKeyDown={(e) => {
          if (e.key === 'Enter') void load(0)
        }}
      />
      <span className="absolute left-3 top-2.5 text-slate-400">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      </span>
    </div>
  )

  return (
    <div className="flex min-w-0 flex-col space-y-8 animate-in fade-in duration-500 pb-10">
      
      {/* Header com Filtros — mobile: busca + acordeão (#825); desktop: layout actual */}
      <header className="flex min-w-0 flex-col gap-6 border-b pb-6 dark:border-slate-800 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1 md:shrink-0">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Atendimentos</h1>
          <p className="text-sm text-slate-500">Acompanhe todo o ciclo dos chats — em andamento, aguardando e finalizados.</p>
        </div>

        {/* Mobile */}
        <div className="flex min-w-0 flex-col gap-3 md:hidden">
          {campoBusca}
          <CollapsibleCard
            title="Filtros"
            badge={
              filtrosAvancadosAtivos > 0
                ? `${filtrosAvancadosAtivos} filtro${filtrosAvancadosAtivos === 1 ? '' : 's'}`
                : null
            }
            open={filtrosAbertos}
            onOpenChange={setFiltrosAbertos}
          >
            <div className="flex flex-col gap-3">{filtrosAvancados}</div>
          </CollapsibleCard>
        </div>

        {/* Desktop */}
        <div className="hidden min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between md:flex">
          {campoBusca}
          {filtrosAvancados}
        </div>
      </header>

      {/* Tabela de Resultados (Cards) */}
      <div className="min-w-0 space-y-4">
        {loading && items.length === 0 ? (
          // Skeletons
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 w-full animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ))
        ) : items.length === 0 ? (
          <Card className="flex flex-col items-center justify-center border-dashed border-2 py-16 text-center">
            <div className="rounded-full bg-slate-50 p-4 dark:bg-slate-900/50">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-300"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8"/><path d="M8 13h6"/></svg>
            </div>
            <h3 className="mt-4 font-semibold text-slate-900 dark:text-slate-100">Nenhum registro encontrado</h3>
            <p className="text-sm text-slate-500">Tente ajustar seus termos de busca.</p>
          </Card>
        ) : (
          <div className="grid min-w-0 gap-3">
            {items.map((c) => (
              <Card
                key={c.id}
                className="group min-w-0 overflow-hidden border-none p-4 shadow-sm ring-1 ring-slate-200 transition-all hover:ring-cyan-500/50 dark:ring-slate-800"
              >
                <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                  
                  {/* Info do Cliente e Protocolo */}
                  <div className="flex min-w-0 flex-1 items-center gap-3 sm:gap-4 md:min-w-[240px]">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-50 text-slate-400 transition-colors group-hover:bg-cyan-50 group-hover:text-cyan-600 dark:bg-slate-900 dark:group-hover:bg-cyan-900/20">
                      <span className="text-sm font-bold">{c.cliente_nome?.charAt(0).toUpperCase() || 'C'}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                        <h3 className="max-w-full truncate font-bold text-slate-900 dark:text-slate-100" title={c.cliente_nome || 'Cliente'}>
                          {c.cliente_nome || 'Cliente'}
                        </h3>
                        <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          {rotuloEstadoChat(c.estado)}
                        </span>
                      </div>
                      <CopiarWaIdButton
                        waId={c.wa_id}
                        className="mt-0.5 text-[10px] font-bold text-slate-400"
                      />
                      <p
                        className="truncate font-mono text-xs font-bold text-cyan-600 dark:text-cyan-400"
                        title={exibirProtocolo(c.protocolo)}
                      >
                        {exibirProtocolo(c.protocolo)}
                      </p>
                      <p
                        className="truncate text-xs text-slate-500 dark:text-slate-400"
                        title={c.empresa_nome || 'Sem empresa'}
                      >
                        {c.empresa_nome || 'Sem empresa'}
                      </p>
                      <p className="mt-1 truncate text-xs text-slate-500 sm:hidden" title={c.atendente_nome || 'Sistema'}>
                        Atendido por {c.atendente_nome || 'Sistema'}
                      </p>
                    </div>
                  </div>

                  {/* Metadados + acções */}
                  <div className="flex min-w-0 w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-center sm:gap-6 md:gap-8">
                    <div className="hidden text-right sm:block">
                      <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Atendido por</p>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-300">{c.atendente_nome || 'Sistema'}</p>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-left sm:grid-cols-1 sm:text-right">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Início</p>
                        <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                          {c.atendimento_inicio_at ? new Date(c.atendimento_inicio_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Finalizado em</p>
                        <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                          {c.encerramento_at ? new Date(c.encerramento_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Duração</p>
                        <p className="text-xs font-medium text-slate-700 dark:text-slate-300">{formatDuration(c)}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Avaliação</p>
                        <div className="flex sm:justify-end">
                          <AvaliacaoEstrelas chat={c} size="sm" />
                        </div>
                      </div>
                    </div>

                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <Link
                        to={whatsappConversaLink(historicoReturnPath, 'historico')}
                        onClick={() => {
                          marcarWhatsappChatAtivo(c.id)
                          saveWhatsappListScroll('historico', historicoReturnPath)
                        }}
                        className="inline-flex shrink-0 items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-600 transition-all hover:bg-cyan-600 hover:text-white dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-cyan-700 sm:rounded-full sm:p-2 sm:px-2"
                        title="Ver conversa"
                      >
                        <span className="sm:hidden">Ver conversa</span>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                      </Link>
                      {(c.estado === 'encerrado' || c.estado === 'aguardando_avaliacao') && (
                        <Button
                          type="button"
                          variant="secondary"
                          className="h-9 min-w-0 flex-1 px-3 text-xs sm:flex-none"
                          onClick={() => setRetomarChat(c)}
                        >
                          Retomar contacto
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <ChatIniciarConversaModal
        open={retomarChat != null}
        onClose={() => setRetomarChat(null)}
        telefoneInicial={retomarChat?.wa_id}
        funcionarioId={retomarChat?.funcionario_rede_id}
        empresas={retomarChat?.empresas_opcoes}
        titulo={retomarChat ? `Retomar ${retomarChat.cliente_nome || retomarChat.wa_id}` : undefined}
      />

      {/* Paginação Estilizada */}
      <footer className="flex flex-col items-center justify-between gap-4 border-t pt-6 dark:border-slate-800 sm:flex-row">
        <div className="text-sm text-slate-500">
          Mostrando <span className="font-bold text-slate-900 dark:text-slate-200">{offset + 1}</span>-
          <span className="font-bold text-slate-900 dark:text-slate-200">{Math.min(offset + PAGE_SIZE, total)}</span> de{' '}
          <span className="font-bold text-slate-900 dark:text-slate-200">{total}</span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            disabled={offset <= 0 || loading}
            onClick={() => void load(offset - PAGE_SIZE)}
            className="h-9 px-4"
          >
            Anterior
          </Button>
          
          <div className="flex h-9 items-center gap-1 rounded-md bg-slate-100 px-3 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
            <span>Página</span>
            <span className="text-cyan-600">{paginaAtual}</span>
            <span>de</span>
            <span>{totalPaginas}</span>
          </div>

          <Button
            variant="secondary"
            disabled={offset + PAGE_SIZE >= total || loading}
            onClick={() => void load(offset + PAGE_SIZE)}
            className="h-9 px-4"
          >
            Próxima
          </Button>
        </div>
      </footer>
    </div>
  )
}