import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { portalCliente, type PortalCliente } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useToast } from '../../components/ui/Toast'
import {
  PortalPageHeader,
  PortalSegmentedControl,
  portalCardClass,
  portalInputClass,
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

function estadoLabel(estado: string) {
  const s = (estado || '').toLowerCase()
  if (s === 'encerrado') return 'Encerrado'
  if (s === 'em_atendimento') return 'Em atendimento'
  if (s === 'aguardando_atendente') return 'Aguardando'
  if (s === 'aguardando_avaliacao') return 'Aguardando avaliação'
  if (s === 'classificacao_demanda_pendente') return 'Em classificação'
  return estado || '—'
}

function estadoTone(estado: string) {
  const s = (estado || '').toLowerCase()
  if (s === 'encerrado') return 'bg-slate-100 text-slate-600 ring-1 ring-slate-200/80'
  if (s === 'em_atendimento') return 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200/60'
  if (s === 'aguardando_atendente') return 'bg-sky-50 text-sky-800 ring-1 ring-sky-200/50'
  return 'bg-amber-50 text-amber-800 ring-1 ring-amber-200/60'
}

export function PortalChats() {
  const [situacao, setSituacao] = useState<'abertos' | 'encerrados' | 'todos'>('abertos')
  const [busca, setBusca] = useState('')
  const [buscaDebounced, setBuscaDebounced] = useState('')
  const [items, setItems] = useState<PortalCliente.WhatsappChatListItem[]>([])
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
      .listChats({ situacao, busca: buscaDebounced || undefined, limit: 50 })
      .then((res) => {
        if (cancelled) return
        setItems(res.items)
        setTotal(res.total)
      })
      .catch((err) => {
        if (cancelled) return
        const msg = mensagemFalhaParaToast(err, 'Não foi possível carregar os atendimentos.')
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

  return (
    <div className="space-y-6">
      <PortalPageHeader
        title="Atendimentos WhatsApp"
        subtitle="Acompanhe as conversas de suporte vinculadas a você."
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <PortalSegmentedControl
          value={situacao}
          onChange={setSituacao}
          options={[
            { value: 'abertos', label: 'Abertos' },
            { value: 'encerrados', label: 'Encerrados' },
            { value: 'todos', label: 'Todos' },
          ]}
        />
        <input
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar por protocolo…"
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
          <p className="text-base font-medium text-slate-900">Nenhum atendimento</p>
          <p className="mt-1 text-sm text-slate-500">Não há conversas com os filtros atuais.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((c) => (
            <li key={c.id}>
              <Link to={`/portal/chats/${c.id}`} className={`block ${portalCardClass}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-mono text-xs font-semibold tracking-wide text-[var(--portal-primary)]">
                      {c.protocolo}
                    </p>
                    <p className="mt-1 truncate text-base font-medium text-slate-900">
                      {c.ultima_mensagem_preview || 'Sem mensagens'}
                    </p>
                    <p className="mt-1 truncate text-sm text-slate-500">
                      {[c.empresa_nome, c.setor_nome].filter(Boolean).join(' · ') || '—'}
                    </p>
                  </div>
                  <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${estadoTone(c.estado)}`}>
                    {estadoLabel(c.estado)}
                  </span>
                </div>
                <p className="mt-3 text-xs text-slate-400">{formatData(c.ultima_mensagem_em || c.created_at)}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {!loading && items.length > 0 ? (
        <p className="text-center text-xs text-slate-400">
          {total > items.length ? `Mostrando ${items.length} de ${total}` : `${total} atendimento${total === 1 ? '' : 's'}`}
        </p>
      ) : null}
    </div>
  )
}
