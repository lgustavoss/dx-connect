import { useCallback, useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, whatsappChats, type WhatsappChats } from '../../api/client'
import { refetchPendenciasResumo } from '../../hooks/useAlertaFilaSemResponsavel'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { exibirProtocolo } from '../../lib/exibirProtocolo'

// Componente para cálculo de tempo de espera
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
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
      minutos > 10 ? 'bg-red-100 text-red-600 animate-pulse' : 'bg-slate-100 text-slate-500 dark:bg-slate-800'
    }`}>
      {minutos === 0 ? 'Agora' : `${minutos} min`}
    </span>
  )
}

export function WhatsappAtendendo() {
  const toast = useToast()
  const [fila, setFila] = useState<WhatsappChats.Chat[]>([])
  const [meus, setMeus] = useState<WhatsappChats.Chat[]>([])
  const [loading, setLoading] = useState(true)
  const isFirstLoad = useRef(true)

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const [rowsFila, rowsMeus] = await Promise.all([
        whatsappChats.fila(), 
        whatsappChats.meus()
      ])
      setFila(rowsFila)
      setMeus(rowsMeus)
    } catch (err) {
      if (!silent) toast.showError(mensagemFalhaParaToast(err, 'Erro ao sincronizar dados.'))
    } finally {
      setLoading(false)
      isFirstLoad.current = false
    }
  }, [toast])

  // Refresh automático a cada 10 segundos
  useEffect(() => {
    void load() 
    const timer = setInterval(() => void load(true), 10000)
    return () => clearInterval(timer)
  }, [load])

  async function assumir(id: number) {
    try {
      await whatsappChats.assumir(id)
      toast.showSuccess('Chat assumido com sucesso!')
      await load(true)
      void refetchPendenciasResumo()
    } catch (err) {
      const msg = err instanceof ApiError && err.status === 400
          ? (err.body as { detail?: string })?.detail || 'Erro ao assumir.'
          : mensagemFalhaParaToast(err)
      toast.showWarning(msg)
    }
  }

  if (loading && isFirstLoad.current) {
    return <div className="flex h-64 items-center justify-center text-sm font-medium text-slate-400 animate-pulse">Carregando central de atendimento...</div>
  }

  return (
    <div className="flex flex-col space-y-8 animate-in fade-in duration-500">
      
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-4 border-b pb-6 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Fila de Atendimento</h1>
          <p className="text-sm text-slate-500">Monitore a fila e gerencie seus chats em tempo real.</p>
        </div>
        <div className="flex gap-6">
          <div className="text-right">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Na Fila</p>
            <p className={`text-xl font-mono font-bold ${fila.length > 0 ? 'text-amber-500' : 'text-slate-300'}`}>{fila.length}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Meus Chats</p>
            <p className="text-xl font-mono font-bold text-cyan-600">{meus.length}</p>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        
        {/* Coluna da Fila */}
        <section className="lg:col-span-5 space-y-4">
          <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-500">
            Aguardando ({fila.length})
          </h2>

          <div className="space-y-3">
            {fila.length === 0 ? (
              <Card className="border-dashed border-2 bg-transparent p-8 text-center">
                <p className="text-sm text-slate-400">Fila vazia. Bom trabalho!</p>
              </Card>
            ) : (
              fila.map((c) => (
                <Card key={c.id} className="border-none p-4 shadow-sm ring-1 ring-slate-200 dark:ring-slate-800">
                  <div className="flex flex-col gap-4">
                    <div className="flex items-start justify-between">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className="min-w-0 truncate font-mono text-[10px] font-bold text-cyan-600"
                            title={exibirProtocolo(c.protocolo)}
                          >
                            {exibirProtocolo(c.protocolo)}
                          </span>
                          <TempoEspera data={c.created_at} />
                        </div>
                        <h3 className="truncate font-bold text-slate-900 dark:text-slate-100">{c.cliente_nome || 'Cliente'}</h3>
                        <p className="font-mono text-xs text-slate-500">{c.wa_id}</p>
                      </div>
                      <div className="h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]" />
                    </div>

                    {/* Grupo de Botões da Fila */}
                    <div className="flex items-center gap-2 border-t pt-3 dark:border-slate-800">
                      <Link 
                        to={`/whatsapp/c/${c.id}`}
                        className="flex-1 text-center rounded-lg bg-slate-100 py-2 text-xs font-bold text-slate-600 hover:bg-slate-200 transition-colors dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                      >
                        Visualizar
                      </Link>
                      <Button 
                        onClick={() => void assumir(c.id)}
                        className="flex-1 bg-amber-500 hover:bg-amber-600 text-white"
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

        {/* Coluna de Ativos */}
        <section className="lg:col-span-7 space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-500">
            Em atendimento comigo ({meus.length})
          </h2>

          <div className="grid gap-4 md:grid-cols-2">
            {meus.length === 0 ? (
              <div className="md:col-span-2 rounded-xl border-2 border-dashed p-12 text-center">
                <p className="text-sm text-slate-400 italic">Você não tem atendimentos em curso.</p>
              </div>
            ) : (
              meus.map((c) => (
                <Link key={c.id} to={`/whatsapp/c/${c.id}`} className="group">
                  <Card className="h-full border-none p-5 shadow-sm ring-1 ring-slate-200 transition-all group-hover:ring-cyan-500 dark:ring-slate-800">
                    <div className="flex flex-col h-full justify-between gap-4">
                      <div>
                        <div className="flex justify-between items-start mb-2">
                          <span
                            className="min-w-0 truncate text-[10px] font-bold text-cyan-600"
                            title={exibirProtocolo(c.protocolo)}
                          >
                            {exibirProtocolo(c.protocolo)}
                          </span>
                          <span className="relative flex h-2 w-2">
                            <span className="absolute h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                            <span className="relative h-2 w-2 rounded-full bg-emerald-500"></span>
                          </span>
                        </div>
                        <h3 className="font-bold text-slate-900 dark:text-slate-100 group-hover:text-cyan-600 transition-colors">
                          {c.cliente_nome || 'Cliente'}
                        </h3>
                        <p className="text-xs text-slate-400 font-mono mt-1">{c.wa_id}</p>
                      </div>
                      
                      <div className="flex items-center justify-end border-t pt-3 dark:border-slate-800">
                         <span className="text-xs font-bold text-cyan-600">
                           Continuar →
                         </span>
                      </div>
                    </div>
                  </Card>
                </Link>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}