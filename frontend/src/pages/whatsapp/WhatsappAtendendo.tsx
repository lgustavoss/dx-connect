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
    return <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
  }

  return (
    <div className="space-y-10">
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Na fila
        </h2>
        {fila.length === 0 ? (
          <Card className="p-6 text-center text-slate-600 dark:text-slate-400">
            Nenhum chat aguardando atendente.
          </Card>
        ) : (
          <ul className="space-y-3">
            {fila.map((c) => (
              <li key={c.id}>
                <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="font-mono text-sm font-semibold text-cyan-700 dark:text-cyan-400">{c.protocolo}</p>
                    <p className="mt-1 truncate text-sm text-slate-800 dark:text-slate-200">
                      {c.cliente_nome || 'Cliente'} · <span className="font-mono text-xs">{c.wa_id}</span>
                    </p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      Aguardando desde {c.created_at ? new Date(c.created_at).toLocaleString('pt-BR') : '—'}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Link
                      to={`/whatsapp/c/${c.id}`}
                      className="inline-flex items-center justify-center rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
                    >
                      Abrir
                    </Link>
                    <Button type="button" onClick={() => assumir(c.id)}>
                      Assumir
                    </Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Meus atendimentos
        </h2>
        {meus.length === 0 ? (
          <Card className="p-6 text-center text-slate-600 dark:text-slate-400">
            Você não tem chats em atendimento no momento.
          </Card>
        ) : (
          <ul className="space-y-3">
            {meus.map((c) => (
              <li key={c.id}>
                <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="font-mono text-sm font-semibold text-cyan-700 dark:text-cyan-400">{c.protocolo}</p>
                    <p className="mt-1 truncate text-sm text-slate-800 dark:text-slate-200">
                      {c.cliente_nome || 'Cliente'} · <span className="font-mono text-xs">{c.wa_id}</span>
                    </p>
                  </div>
                  <Link
                    to={`/whatsapp/c/${c.id}`}
                    className="inline-flex shrink-0 items-center justify-center rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
                  >
                    Continuar
                  </Link>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
