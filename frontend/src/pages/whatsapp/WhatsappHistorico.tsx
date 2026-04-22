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

  // Estado de Carregamento (Skeleton)
  if (loading && items.length === 0) {
    return (
      <div className="space-y-4 animate-pulse">
        {[1, 2, 3].map((n) => (
          <div key={n} className="h-24 w-full rounded-xl bg-slate-100 dark:bg-slate-800/50" />
        ))}
      </div>
    )
  }

  // Estado Vazio
  if (items.length === 0) {
    return (
      <Card className="flex flex-col items-center justify-center p-12 text-center border-dashed border-2">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800">
          📂
        </div>
        <h3 className="mt-4 text-sm font-semibold text-slate-900 dark:text-slate-100">Nenhum chat encerrado</h3>
        <p className="mt-1 text-sm text-slate-500">O histórico de conversas finalizadas aparecerá aqui.</p>
      </Card>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header do Histórico */}
      <div className="flex items-end justify-between px-1">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Histórico</h2>
          <p className="text-sm text-slate-500">Gerencie e revise atendimentos finalizados.</p>
        </div>
        <div className="hidden text-right sm:block">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Total de registros</p>
          <p className="text-lg font-mono font-bold text-cyan-600 dark:text-cyan-400">{total}</p>
        </div>
      </div>

      {/* Lista de Chats */}
      <ul className="grid gap-3">
        {items.map((c) => (
          <li key={c.id}>
            <Card className="group relative flex flex-col gap-4 overflow-hidden border-none p-5 shadow-sm ring-1 ring-slate-200 transition-all hover:shadow-md hover:ring-cyan-200 dark:shadow-none dark:ring-slate-800 dark:hover:ring-cyan-900/50 sm:flex-row sm:items-center sm:justify-between">
              {/* Indicador lateral sutil no hover */}
              <div className="absolute inset-y-0 left-0 w-1 bg-cyan-500 opacity-0 transition-opacity group-hover:opacity-100" />
              
              <div className="flex min-w-0 items-center gap-4">
                {/* Avatar / Ícone */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500 group-hover:bg-cyan-50 group-hover:text-cyan-600 dark:bg-slate-800 dark:group-hover:bg-cyan-900/30">
                  <span className="text-xs font-bold uppercase">{c.cliente_nome?.charAt(0) || 'C'}</span>
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="truncate font-bold text-slate-900 dark:text-slate-100">
                      {c.cliente_nome || 'Cliente'}
                    </p>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                      {c.wa_id}
                    </span>
                  </div>
                  
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                    <p className="font-mono text-xs font-semibold text-cyan-700 dark:text-cyan-400">
                      {c.protocolo}
                    </p>
                    <span className="text-slate-300 dark:text-slate-700">|</span>
                    <p className="text-xs text-slate-500">
                      Encerrado em {c.encerramento_at ? new Date(c.encerramento_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-3">
                <Link
                  to={`/whatsapp/c/${c.id}`}
                  className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm ring-1 ring-slate-200 transition-all hover:bg-slate-50 hover:text-cyan-600 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700 dark:hover:bg-slate-800 dark:hover:text-cyan-400"
                >
                  Revisar Chat
                  <span className="text-slate-400">→</span>
                </Link>
              </div>
            </Card>
          </li>
        ))}
      </ul>

      {/* Paginação Estilizada */}
      <div className="flex flex-col items-center justify-between gap-4 border-t border-slate-100 pt-6 dark:border-slate-800 sm:flex-row">
        <p className="text-sm text-slate-500">
          Mostrando <span className="font-bold text-slate-900 dark:text-slate-200">{offset + 1}</span> a{' '}
          <span className="font-bold text-slate-900 dark:text-slate-200">{Math.min(offset + items.length, total)}</span> de{' '}
          <span className="font-bold text-slate-900 dark:text-slate-200">{total}</span> atendimentos
        </p>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={offset <= 0 || loading}
            onClick={() => void load(Math.max(0, offset - PAGE))}
            className="flex items-center gap-2 px-4 shadow-none disabled:opacity-30"
          >
            ← Anterior
          </Button>
          
          <div className="flex h-8 min-w-[32px] items-center justify-center rounded-md bg-slate-100 px-2 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
            Página {Math.floor(offset / PAGE) + 1}
          </div>

          <Button
            type="button"
            variant="secondary"
            disabled={offset + items.length >= total || loading}
            onClick={() => void load(offset + PAGE)}
            className="flex items-center gap-2 px-4 shadow-none disabled:opacity-30"
          >
            Próxima →
          </Button>
        </div>
      </div>
    </div>
  )
}