import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { whatsappChats, type WhatsappChats } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

const PAGE = 30

export function WhatsappHistorico() {
  const toast = useToast()
  const [items, setItems] = useState<WhatsappChats.Chat[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)

  async function load(from: number) {
    setLoading(true)
    try {
      const { items: rows, total: t } = await whatsappChats.encerrados({ offset: from, limit: PAGE })
      setItems(rows)
      setTotal(t)
      setOffset(from)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o histórico.'))
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load(0)
  }, [])

  if (loading && items.length === 0) {
    return <p className="text-slate-500 dark:text-slate-400">Carregando histórico…</p>
  }

  if (items.length === 0) {
    return (
      <Card className="p-6 text-center text-slate-600 dark:text-slate-400">Nenhum chat encerrado encontrado.</Card>
    )
  }

  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {items.map((c) => (
          <li key={c.id}>
            <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="font-mono text-sm font-semibold text-slate-700 dark:text-slate-300">{c.protocolo}</p>
                <p className="mt-1 truncate text-sm text-slate-800 dark:text-slate-200">
                  {c.cliente_nome || 'Cliente'} · <span className="font-mono text-xs">{c.wa_id}</span>
                </p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Encerrado em {c.encerramento_at ? new Date(c.encerramento_at).toLocaleString('pt-BR') : '—'}
                </p>
              </div>
              <Link
                to={`/whatsapp/c/${c.id}`}
                className="inline-flex items-center justify-center rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
              >
                Ver conversa
              </Link>
            </Card>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-600 dark:text-slate-400">
        <span>
          Mostrando {offset + 1}–{offset + items.length} de {total}
        </span>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={offset <= 0 || loading}
            onClick={() => load(Math.max(0, offset - PAGE))}
          >
            Anterior
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={offset + items.length >= total || loading}
            onClick={() => load(offset + PAGE)}
          >
            Próxima
          </Button>
        </div>
      </div>
    </div>
  )
}
