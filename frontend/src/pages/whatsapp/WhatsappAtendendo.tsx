import { useCallback, useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, whatsappChats, type WhatsappChats } from '../../api/client'
import { whatsappConversaLink, WHATSAPP_LIST_PATHS } from '../../lib/whatsappListReturn'
import { refetchPendenciasResumo } from '../../hooks/useAlertaFilaSemResponsavel'
import { useEventStream } from '../../contexts/EventStreamContext'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import { rotuloResponsavelChat } from '../../lib/whatsappChatMeta'

function TempoEspera({ data }: { data?: string | null }) {
  const [minutos, setMinutos] = useState(0)

  useEffect(() => {
    if (!data) return
    const atualizar = () => {
      const diff = Math.floor((new Date().getTime() - new Date(data).getTime()) / 60000)
      setMinutos(diff)
    }
    atualizar()
    const interval = setInterval(atualizar, 30000)
    return () => clearInterval(interval)
  }, [data])

  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
        minutos > 10
          ? 'animate-pulse bg-red-100 text-red-600'
          : 'bg-slate-100 text-slate-500 dark:bg-slate-800'
      }`}
    >
      {minutos === 0 ? 'Agora' : `${minutos} min`}
    </span>
  )
}

export function WhatsappAtendendo() {
  const toast = useToast()
  const { subscribe, useFallback } = useEventStream()
  const [fila, setFila] = useState<WhatsappChats.Chat[]>([])
  const [meus, setMeus] = useState<WhatsappChats.Chat[]>([])
  const [loading, setLoading] = useState(true)
  const isFirstLoad = useRef(true)
  const prevFilaCount = useRef(0)

  const load = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true)
      try {
        const [rowsFila, rowsMeus] = await Promise.all([whatsappChats.fila(), whatsappChats.meus()])
        setFila(rowsFila)
        setMeus(rowsMeus)
      } catch (err) {
        if (!silent) toast.showError(mensagemFalhaParaToast(err, 'Erro ao sincronizar dados.'))
      } finally {
        setLoading(false)
        isFirstLoad.current = false
      }
    },
    [toast],
  )

  useEffect(() => {
    const refresh = () => void load(true)
    const unsubFila = subscribe('chat.fila', refresh)
    const unsubMsg = subscribe('chat.mensagem', refresh)
    return () => {
      unsubFila()
      unsubMsg()
    }
  }, [subscribe, load])

  useEffect(() => {
    void load()
    const intervalMs = useFallback ? 10000 : 8000
    const timer = setInterval(() => void load(true), intervalMs)
    return () => clearInterval(timer)
  }, [load, useFallback])

  useEffect(() => {
    if (fila.length > prevFilaCount.current) {
      void refetchPendenciasResumo(true)
    } else if (fila.length < prevFilaCount.current) {
      void refetchPendenciasResumo()
    }
    prevFilaCount.current = fila.length
  }, [fila.length])

  async function assumir(id: number) {
    try {
      await whatsappChats.assumir(id)
      toast.showSuccess('Chat assumido com sucesso!')
      await load(true)
      void refetchPendenciasResumo()
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 400
          ? (err.body as { detail?: string })?.detail || 'Erro ao assumir.'
          : mensagemFalhaParaToast(err)
      toast.showWarning(msg)
    }
  }

  const meusAtivos = meus.filter((c) => c.estado === 'em_atendimento')
  const meusAClassificar = meus.filter(
    (c) => c.classificacao_demanda_pendente && c.estado !== 'em_atendimento',
  )

  if (loading && isFirstLoad.current) {
    return (
      <div className="flex h-64 items-center justify-center text-sm font-medium text-slate-400 animate-pulse">
        Carregando central de atendimento...
      </div>
    )
  }

  return (
    <div className="flex flex-col space-y-8 animate-in fade-in duration-500">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b pb-6 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Fila de Atendimento</h1>
          <p className="text-sm text-slate-500">Monitore a fila e gerencie seus chats em tempo real.</p>
        </div>
        <div className="flex gap-6">
          <div className="text-right">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Na Fila</p>
            <p
              className={`text-xl font-mono font-bold ${fila.length > 0 ? 'text-amber-500' : 'text-slate-300'}`}
            >
              {fila.length}
            </p>
          </div>
          <div className="text-right">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Comigo</p>
            <p className="text-xl font-mono font-bold text-cyan-600">{meusAtivos.length}</p>
          </div>
          {meusAClassificar.length > 0 && (
            <div className="text-right">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">A classificar</p>
              <p className="text-xl font-mono font-bold text-amber-600">{meusAClassificar.length}</p>
            </div>
          )}
        </div>
      </header>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        <section className="space-y-4 lg:col-span-5">
          <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-500">
            Aguardando ({fila.length})
          </h2>

          <div className="space-y-3">
            {fila.length === 0 ? (
              <Card className="border-2 border-dashed bg-transparent p-8 text-center">
                <p className="text-sm text-slate-400">Fila vazia. Bom trabalho!</p>
              </Card>
            ) : (
              fila.map((c) => (
                <Card key={c.id} className="border-none p-4 shadow-sm ring-1 ring-slate-200 dark:ring-slate-800">
                  <div className="flex flex-col gap-4">
                    <div className="flex items-start justify-between">
                      <div className="min-w-0">
                        <div className="mb-1 flex items-center gap-2">
                          <span
                            className="min-w-0 truncate font-mono text-[10px] font-bold text-cyan-600"
                            title={exibirProtocolo(c.protocolo)}
                          >
                            {exibirProtocolo(c.protocolo)}
                          </span>
                          <TempoEspera data={c.created_at} />
                          {!c.funcionario_rede_id && (
                            <span className="shrink-0 rounded-full bg-violet-100 px-2 py-0.5 text-[9px] font-medium text-violet-700 dark:bg-violet-950/50 dark:text-violet-300">
                              Sem vínculo
                            </span>
                          )}
                        </div>
                        <h3 className="truncate font-bold text-slate-900 dark:text-slate-100">
                          {c.cliente_nome || 'Cliente'}
                        </h3>
                        <p className="font-mono text-xs text-slate-500">{c.wa_id}</p>
                        {c.empresa_nome && (
                          <p className="mt-1 truncate text-[10px] font-medium text-slate-500 dark:text-slate-400">
                            {c.empresa_nome}
                          </p>
                        )}
                        {c.setor_nome && (
                          <p className="mt-1 text-[10px] font-medium text-slate-500 dark:text-slate-400">
                            Setor {c.setor_nome}
                          </p>
                        )}
                      </div>
                      <div className="h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]" />
                    </div>

                    <div className="flex items-center gap-2 border-t pt-3 dark:border-slate-800">
                      <Link
                        to={whatsappConversaLink(c.id, WHATSAPP_LIST_PATHS.atendendo, 'atendendo')}
                        className="flex-1 rounded-lg bg-slate-100 py-2 text-center text-xs font-bold text-slate-600 transition-colors hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                      >
                        Visualizar
                      </Link>
                      <Button
                        onClick={() => void assumir(c.id)}
                        className="flex-1 bg-amber-500 text-white hover:bg-amber-600"
                      >
                        Atender
                      </Button>
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        </section>

        <section className="space-y-8 lg:col-span-7">
          {meusAClassificar.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-widest text-amber-700 dark:text-amber-400">
                A classificar demanda ({meusAClassificar.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                {meusAClassificar.map((c) => (
                  <Link
                    key={c.id}
                    to={whatsappConversaLink(c.id, WHATSAPP_LIST_PATHS.atendendo, 'atendendo')}
                    className="group"
                  >
                    <Card className="h-full border-none p-5 shadow-sm ring-1 ring-amber-300 transition-all group-hover:ring-amber-500 dark:ring-amber-800">
                      <div className="flex h-full flex-col justify-between gap-4">
                        <div>
                          <div className="mb-2 flex items-start justify-between gap-2">
                            <span
                              className="min-w-0 truncate text-[10px] font-bold text-amber-700 dark:text-amber-400"
                              title={exibirProtocolo(c.protocolo)}
                            >
                              {exibirProtocolo(c.protocolo)}
                            </span>
                            <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-bold uppercase text-amber-800 dark:bg-amber-950/50 dark:text-amber-200">
                              Pendente
                            </span>
                          </div>
                          <h3 className="font-bold text-slate-900 transition-colors group-hover:text-amber-700 dark:text-slate-100">
                            {c.cliente_nome || 'Cliente'}
                          </h3>
                          <p className="mt-1 font-mono text-xs text-slate-400">{c.wa_id}</p>
                          <p className="mt-2 text-[10px] font-medium text-amber-800/80 dark:text-amber-200/80">
                            Encerrado por inatividade — falta registar a demanda
                          </p>
                        </div>
                        <div className="flex items-center justify-end border-t pt-3 dark:border-slate-800">
                          <span className="text-xs font-bold text-amber-700 dark:text-amber-400">
                            Classificar →
                          </span>
                        </div>
                      </div>
                    </Card>
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-500">
              Em atendimento comigo ({meusAtivos.length})
            </h2>

            <div className="grid gap-4 md:grid-cols-2">
              {meusAtivos.length === 0 ? (
                <div className="rounded-xl border-2 border-dashed p-12 text-center md:col-span-2">
                  <p className="text-sm italic text-slate-400">Você não tem atendimentos em curso.</p>
                </div>
              ) : (
                meusAtivos.map((c) => (
                  <Link
                    key={c.id}
                    to={whatsappConversaLink(c.id, WHATSAPP_LIST_PATHS.atendendo, 'atendendo')}
                    className="group"
                  >
                    <Card className="h-full border-none p-5 shadow-sm ring-1 ring-slate-200 transition-all group-hover:ring-cyan-500 dark:ring-slate-800">
                      <div className="flex h-full flex-col justify-between gap-4">
                        <div>
                          <div className="mb-2 flex items-start justify-between">
                            <span
                              className="min-w-0 truncate text-[10px] font-bold text-cyan-600"
                              title={exibirProtocolo(c.protocolo)}
                            >
                              {exibirProtocolo(c.protocolo)}
                            </span>
                            <span className="relative flex h-2 w-2">
                              <span className="absolute h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                              <span className="relative h-2 w-2 rounded-full bg-emerald-500" />
                            </span>
                          </div>
                          <h3 className="font-bold text-slate-900 transition-colors group-hover:text-cyan-600 dark:text-slate-100">
                            {c.cliente_nome || 'Cliente'}
                          </h3>
                          {!c.funcionario_rede_id && (
                            <span className="mt-1 inline-flex rounded-full bg-violet-100 px-2 py-0.5 text-[9px] font-medium text-violet-700 dark:bg-violet-950/50 dark:text-violet-300">
                              Sem vínculo
                            </span>
                          )}
                          <p className="mt-1 font-mono text-xs text-slate-400">{c.wa_id}</p>
                          <p className="mt-2 text-[10px] font-medium text-slate-500 dark:text-slate-400">
                            {rotuloResponsavelChat(c)}
                            {c.setor_nome ? ` • ${c.setor_nome}` : ''}
                          </p>
                        </div>
                        <div className="flex items-center justify-end border-t pt-3 dark:border-slate-800">
                          <span className="text-xs font-bold text-cyan-600">Continuar →</span>
                        </div>
                      </div>
                    </Card>
                  </Link>
                ))
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
