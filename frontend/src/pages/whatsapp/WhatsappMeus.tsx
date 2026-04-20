import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { whatsappChats, type WhatsappChats } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

export function WhatsappMeus() {
  const toast = useToast()
  const [items, setItems] = useState<WhatsappChats.Chat[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const rows = await whatsappChats.meus()
        if (!cancelled) setItems(rows)
      } catch (err) {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar seus chats.'))
          setItems([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
  }

  if (items.length === 0) {
    return (
      <Card className="p-6 text-center text-slate-600 dark:text-slate-400">
        Você não tem chats em atendimento no momento.
      </Card>
    )
  }

  return (
    <ul className="space-y-3">
      {items.map((c) => (
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
              className="inline-flex items-center justify-center rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
            >
              Continuar
            </Link>
          </Card>
        </li>
      ))}
    </ul>
  )
}
