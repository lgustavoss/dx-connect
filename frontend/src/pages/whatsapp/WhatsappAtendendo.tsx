import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, whatsappChats, type WhatsappChats } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

export function WhatsappAtendendo() {
  const toast = useToast()
  const [fila, setFila] = useState<WhatsappChats.Chat[]>([])
  const [meus, setMeus] = useState<WhatsappChats.Chat[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rowsFila, rowsMeus] = await Promise.all([whatsappChats.fila(), whatsappChats.meus()])
      setFila(rowsFila)
      setMeus(rowsMeus)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar os chats.'))
      setFila([])
      setMeus([])
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    void load()
  }, [load])

  async function assumir(id: number) {
    try {
      await whatsappChats.assumir(id)
      toast.showSuccess('Chat assumido.')
      await load()
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 400
          ? (err.body as { detail?: string })?.detail || 'Não foi possível assumir.'
          : mensagemFalhaParaToast(err)
      toast.showWarning(msg)
    }
  }

  if (loading) {
    return (
      <div className="space-y-8 animate-pulse">
        <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
        <div className="space-y-3">
          <div className="h-20 bg-slate-100 dark:bg-slate-800/50 rounded-xl" />
          <div className="h-20 bg-slate-100 dark:bg-slate-800/50 rounded-xl" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-2 duration-500">
      
      {/* Seção: Na Fila */}
      <section className="space-y-4">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-500">Na Fila</h2>
            {fila.length > 0 && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-100 px-1.5 text-[10px] font-bold text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                {fila.length}
              </span>
            )}
          </div>
          <Button variant="ghost" onClick={() => void load()} className="text-[10px] uppercase tracking-tighter opacity-50 hover:opacity-100">
            Atualizar fila
          </Button>
        </div>

        {fila.length === 0 ? (
          <Card className="flex flex-col items-center justify-center border-none bg-slate-50/50 py-10 text-center dark:bg-slate-900/20">
            <p className="text-sm font-medium text-slate-500">Tudo limpo! Nenhum chat aguardando.</p>
          </Card>
        ) : (
          <ul className="grid gap-3">
            {fila.map((c) => (
              <li key={c.id}>
                <Card className="group flex flex-col gap-4 border-none p-4 shadow-sm ring-1 ring-slate-200 transition-all hover:ring-amber-200 dark:ring-slate-800 dark:hover:ring-amber-900/50 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-4">
                    <div className="mt-1 flex h-2 w-2 shrink-0 animate-pulse rounded-full bg-amber-500" />
                    <div className="min-w-0">
                      <p className="font-mono text-xs font-bold text-cyan-700 dark:text-cyan-400">{c.protocolo}</p>
                      <p className="mt-0.5 truncate font-semibold text-slate-900 dark:text-slate-100">
                        {c.cliente_nome || 'Cliente'} <span className="mx-1 text-slate-300 dark:text-slate-700">•</span> 
                        <span className="font-mono text-xs font-normal text-slate-500">{c.wa_id}</span>
                      </p>
                      <p className="mt-1 text-[10px] text-slate-400 uppercase font-medium">
                        Aguardando desde {c.created_at ? new Date(c.created_at).toLocaleTimeString('pt-BR') : '—'}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/whatsapp/c/${c.id}`}
                      className="rounded-lg px-3 py-1.5 text-xs font-bold text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                    >
                      Visualizar
                    </Link>
                    <Button 
                      type="button" 
                      onClick={() => assumir(c.id)}
                      className="bg-amber-600 shadow-md shadow-amber-600/10 hover:bg-amber-700 dark:bg-amber-700 dark:hover:bg-amber-600"
                    >
                      Assumir chat
                    </Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Seção: Meus Atendimentos */}
      <section className="space-y-4">
        <div className="flex items-center gap-2 px-1">
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-500">Meus Atendimentos</h2>
          {meus.length > 0 && (
            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-cyan-100 px-1.5 text-[10px] font-bold text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400">
              {meus.length}
            </span>
          )}
        </div>

        {meus.length === 0 ? (
          <Card className="flex flex-col items-center justify-center border-dashed border-2 py-10 text-center">
            <p className="text-sm font-medium text-slate-400 italic">Você não tem chats ativos no momento.</p>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {meus.map((c) => (
              <li key={c.id} className="list-none">
                <Card className="group relative flex flex-col justify-between overflow-hidden border-none p-5 shadow-sm ring-1 ring-slate-200 transition-all hover:shadow-lg hover:ring-cyan-500 dark:ring-slate-800 dark:hover:ring-cyan-700">
                  <div className="mb-4">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold text-cyan-600 dark:text-cyan-400">{c.protocolo}</span>
                      <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
                    </div>
                    <h3 className="mt-1 font-bold text-slate-900 dark:text-slate-100">{c.cliente_nome || 'Cliente'}</h3>
                    <p className="font-mono text-xs text-slate-500">{c.wa_id}</p>
                  </div>

                  <Link
                    to={`/whatsapp/c/${c.id}`}
                    className="flex items-center justify-center gap-2 rounded-xl bg-cyan-50 py-2.5 text-sm font-bold text-cyan-700 transition-all group-hover:bg-cyan-600 group-hover:text-white dark:bg-cyan-950/30 dark:text-cyan-400 dark:group-hover:bg-cyan-700"
                  >
                    Continuar Atendimento
                    <span className="transition-transform group-hover:translate-x-1">→</span>
                  </Link>
                </Card>
              </li>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}