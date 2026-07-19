import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { portalCliente, type PortalCliente } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useToast } from '../../components/ui/Toast'
import { Button } from '../../components/ui/Button'

function formatData(iso?: string | null) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function statusTone(slug?: string | null) {
  const s = (slug || '').toLowerCase()
  if (s === 'fechado' || s === 'resolvido') return 'bg-slate-100 text-slate-700'
  if (s === 'aguardando_cliente') return 'bg-amber-50 text-amber-800'
  if (s === 'em_atendimento') return 'bg-teal-50 text-teal-800'
  return 'bg-sky-50 text-sky-800'
}

export function PortalTickets() {
  const [situacao, setSituacao] = useState<'abertos' | 'fechados' | 'todos'>('abertos')
  const [busca, setBusca] = useState('')
  const [buscaDebounced, setBuscaDebounced] = useState('')
  const [items, setItems] = useState<PortalCliente.TicketListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    const t = window.setTimeout(() => setBuscaDebounced(busca.trim()), 300)
    return () => window.clearTimeout(t)
  }, [busca])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setErro(null)
    portalCliente
      .listTickets({ situacao, busca: buscaDebounced || undefined, limit: 50 })
      .then((res) => {
        if (cancelled) return
        setItems(res.items)
        setTotal(res.total)
      })
      .catch((err) => {
        if (cancelled) return
        const msg = mensagemFalhaParaToast(err, 'Não foi possível carregar os chamados.')
        setErro(msg)
        toast.showError(msg)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- toast estável o suficiente; evita loop
  }, [situacao, buscaDebounced])

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Meus chamados</h1>
          <p className="mt-1 text-sm text-slate-600">Acompanhe o andamento das suas solicitações.</p>
        </div>
        <Link to="/portal/tickets/novo">
          <Button type="button">Abrir chamado</Button>
        </Link>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          {(
            [
              ['abertos', 'Abertos'],
              ['fechados', 'Encerrados'],
              ['todos', 'Todos'],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setSituacao(key)}
              className={[
                'flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors sm:flex-none',
                situacao === key
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:bg-slate-50',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>
        <input
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar protocolo ou assunto…"
          className="w-full flex-1 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm shadow-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/25"
        />
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-2xl bg-slate-100" />
          ))}
        </div>
      ) : erro ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-6 text-sm text-rose-800">
          {erro}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/70 px-5 py-10 text-center">
          <p className="text-base font-medium text-slate-900">Nenhum chamado por aqui</p>
          <p className="mt-1 text-sm text-slate-600">
            Abra o primeiro chamado ou consulte a base de ajuda antes.
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Link to="/portal/tickets/novo">
              <Button type="button">Abrir chamado</Button>
            </Link>
            <Link
              to="/portal/ajuda"
              className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Ver ajuda
            </Link>
          </div>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((t) => (
            <li key={t.id}>
              <Link
                to={`/portal/tickets/${t.id}`}
                className="block rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm transition hover:border-teal-300 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-mono text-xs font-semibold tracking-wide text-teal-700">
                      {t.protocolo}
                    </p>
                    <h2 className="mt-1 truncate text-base font-semibold text-slate-900">{t.assunto}</h2>
                    <p className="mt-1 truncate text-sm text-slate-500">
                      {t.empresa_nome || 'Empresa'} · {t.setor_nome || 'Atendimento'}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${statusTone(t.status_slug)}`}
                  >
                    {t.status_nome || '—'}
                  </span>
                </div>
                <p className="mt-3 text-xs text-slate-400">
                  Atualizado {formatData(t.ultima_mensagem_em || t.updated_at || t.created_at)}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {!loading && items.length > 0 ? (
        <p className="text-center text-xs text-slate-400">
          {total} chamado{total === 1 ? '' : 's'}
        </p>
      ) : null}
    </div>
  )
}
