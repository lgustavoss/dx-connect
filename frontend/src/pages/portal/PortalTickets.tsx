import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { portalCliente, type PortalCliente } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useToast } from '../../components/ui/Toast'
import { useMesaPanelHistory } from '../../hooks/useMesaPanelHistory'
import { popMesaPanelState } from '../../lib/mesaHistory'
import {
  gravarPortalTicketAtivoSession,
  lerPortalTicketAtivoSession,
  PORTAL_TICKET_ATIVO_EVENT,
} from '../../lib/portalAtivo'
import { PortalTicketDetalhe } from './PortalTicketDetalhe'
import {
  PortalPageHeader,
  PortalSegmentedControl,
  portalCardClass,
  portalInputClass,
  portalPrimaryBtnClass,
  portalSecondaryBtnClass,
} from './portalUi'

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
  if (s === 'fechado' || s === 'resolvido') return 'bg-slate-100 text-slate-600'
  if (s === 'aguardando_cliente') return 'bg-amber-50 text-amber-800 ring-1 ring-amber-200/60'
  if (s === 'em_atendimento') return 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200/60'
  return 'bg-sky-50 text-sky-800 ring-1 ring-sky-200/50'
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
  const [ticketAtivoId, setTicketAtivoId] = useState<number | null>(() => lerPortalTicketAtivoSession())

  const abrirTicket = useCallback((id: number) => {
    gravarPortalTicketAtivoSession(id)
    setTicketAtivoId(id)
  }, [])

  const fecharTicket = useCallback((opts?: { fromPopstate?: boolean }) => {
    gravarPortalTicketAtivoSession(null)
    setTicketAtivoId(null)
    if (opts?.fromPopstate) return
    popMesaPanelState()
  }, [])

  useMesaPanelHistory('portal-ticket', ticketAtivoId != null, () => {
    fecharTicket({ fromPopstate: true })
  })

  useEffect(() => {
    const sync = () => setTicketAtivoId(lerPortalTicketAtivoSession())
    window.addEventListener(PORTAL_TICKET_ATIVO_EVENT, sync)
    return () => window.removeEventListener(PORTAL_TICKET_ATIVO_EVENT, sync)
  }, [])

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [situacao, buscaDebounced])

  if (ticketAtivoId != null) {
    return <PortalTicketDetalhe ticketIdProp={ticketAtivoId} onVoltar={fecharTicket} />
  }

  return (
    <div className="space-y-6">
      <PortalPageHeader
        title="Meus chamados"
        subtitle="Acompanhe o andamento das suas solicitações."
        action={
          <Link to="/portal/tickets/novo" className={portalPrimaryBtnClass} style={{ backgroundColor: 'var(--portal-primary)' }}>
            Abrir chamado
          </Link>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <PortalSegmentedControl
          value={situacao}
          onChange={setSituacao}
          options={[
            { value: 'abertos', label: 'Abertos' },
            { value: 'fechados', label: 'Encerrados' },
            { value: 'todos', label: 'Todos' },
          ]}
        />
        <input
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar protocolo ou assunto…"
          className={`${portalInputClass} flex-1`}
        />
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-200/60" />
          ))}
        </div>
      ) : erro ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-800">{erro}</div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white px-5 py-12 text-center">
          <p className="text-base font-medium text-slate-900">Nenhum chamado por aqui</p>
          <p className="mt-1 text-sm text-slate-500">Abra o primeiro chamado ou consulte a base de ajuda.</p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Link to="/portal/tickets/novo" className={portalPrimaryBtnClass} style={{ backgroundColor: 'var(--portal-primary)' }}>
              Abrir chamado
            </Link>
            <Link to="/portal/ajuda" className={portalSecondaryBtnClass}>
              Ver ajuda
            </Link>
          </div>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((t) => (
            <li key={t.id}>
              <button type="button" onClick={() => abrirTicket(t.id)} className={`block w-full text-left ${portalCardClass}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-mono text-xs font-semibold tracking-wide text-[var(--portal-primary)]">
                      {t.protocolo}
                    </p>
                    <h2 className="mt-1 truncate text-base font-semibold text-slate-900">{t.assunto}</h2>
                    <p className="mt-1 truncate text-sm text-slate-500">
                      {t.empresa_nome || 'Empresa'} · {t.setor_nome || 'Atendimento'}
                    </p>
                  </div>
                  <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${statusTone(t.status_slug)}`}>
                    {t.status_nome || '—'}
                  </span>
                </div>
                <p className="mt-3 text-xs text-slate-400">
                  Atualizado {formatData(t.ultima_mensagem_em || t.updated_at || t.created_at)}
                </p>
              </button>
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
