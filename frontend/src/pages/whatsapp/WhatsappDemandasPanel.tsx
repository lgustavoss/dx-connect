import { useCallback, useEffect, useState } from 'react'
import {
  ticketClassificacao,
  whatsappChats,
  type TicketClassificacao,
  type WhatsappChats,
} from '../../api/client'
import { Button } from '../../components/ui/Button'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useAuth } from '../../contexts/AuthContext'

type Props = {
  chatId: number
  podeRegistrar: boolean
  onDemandasChange?: (count: number) => void
}

const DESFECHO_ROTULO: Record<string, string> = {
  resolvido_sessao: 'Resolvido na sessão',
  escalado_ticket: 'Escalado para ticket',
}

export function WhatsappDemandasPanel({ chatId, podeRegistrar, onDemandasChange }: Props) {
  const toast = useToast()
  const { user } = useAuth()
  const [demandas, setDemandas] = useState<WhatsappChats.Demanda[]>([])
  const [loading, setLoading] = useState(true)
  const [naturezaId, setNaturezaId] = useState<number | ''>('')
  const [motivoId, setMotivoId] = useState<number | ''>('')
  const [naturezas, setNaturezas] = useState<TicketClassificacao.Natureza[]>([])
  const [motivos, setMotivos] = useState<TicketClassificacao.Motivo[]>([])
  const [salvando, setSalvando] = useState(false)
  const [expandido, setExpandido] = useState(false)

  const carregar = useCallback(async () => {
    try {
      const rows = await whatsappChats.demandas(chatId)
      setDemandas(rows)
      onDemandasChange?.(rows.length)
    } catch {
      setDemandas([])
      onDemandasChange?.(0)
    }
  }, [chatId, onDemandasChange])

  useEffect(() => {
    setLoading(true)
    void carregar().finally(() => setLoading(false))
  }, [carregar])

  useEffect(() => {
    ticketClassificacao
      .listNaturezas({ limit: 100 })
      .then(({ items }) => setNaturezas(items))
      .catch(() => setNaturezas([]))
  }, [])

  useEffect(() => {
    if (naturezaId === '') {
      setMotivos([])
      setMotivoId('')
      return
    }
    ticketClassificacao
      .listMotivos({ natureza_id: Number(naturezaId), limit: 100 })
      .then(({ items }) => setMotivos(items))
      .catch(() => setMotivos([]))
  }, [naturezaId])

  async function registrar() {
    if (naturezaId === '') {
      toast.showWarning('Selecione a natureza da demanda.')
      return
    }
    setSalvando(true)
    try {
      const row = await whatsappChats.registrarDemanda(chatId, {
        natureza_id: Number(naturezaId),
        motivo_id: motivoId === '' ? null : Number(motivoId),
      })
      setDemandas((prev) => {
        const next = [...prev, row]
        onDemandasChange?.(next.length)
        return next
      })
      setNaturezaId('')
      setMotivoId('')
      setExpandido(false)
      toast.showSuccess('Demanda registrada.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível registrar a demanda.'))
    } finally {
      setSalvando(false)
    }
  }

  async function excluir(demandaId: number) {
    if (!confirm('Remover este registro de demanda?')) return
    try {
      await whatsappChats.excluirDemanda(chatId, demandaId)
      setDemandas((prev) => {
        const next = prev.filter((d) => d.id !== demandaId)
        onDemandasChange?.(next.length)
        return next
      })
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível excluir a demanda.'))
    }
  }

  if (loading) {
    return (
      <div className="border-b border-slate-100 px-4 py-2 text-xs text-slate-400 dark:border-slate-800">
        Carregando demandas…
      </div>
    )
  }

  return (
    <div className="border-b border-slate-100 bg-slate-50/80 px-4 py-2 dark:border-slate-800 dark:bg-slate-900/40">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Demandas ({demandas.length})
          </span>
          {demandas.slice(0, 3).map((d) => (
            <span
              key={d.id}
              className="inline-flex max-w-[12rem] truncate rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              title={d.motivo_nome ? `${d.natureza_nome} · ${d.motivo_nome}` : d.natureza_nome ?? undefined}
            >
              {d.natureza_nome}
              {d.motivo_nome ? ` · ${d.motivo_nome}` : ''}
            </span>
          ))}
          {demandas.length > 3 && (
            <span className="text-[10px] text-slate-400">+{demandas.length - 3}</span>
          )}
        </div>
        {podeRegistrar && (
          <Button
            type="button"
            variant="ghost"
            className="h-7 px-2 text-[10px]"
            onClick={() => setExpandido((v) => !v)}
          >
            {expandido ? 'Cancelar' : '+ Registrar demanda'}
          </Button>
        )}
      </div>

      {expandido && podeRegistrar && (
        <div className="mt-2 flex flex-wrap items-end gap-2 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
          <div className="min-w-[10rem] flex-1">
            <Select
              label="Natureza"
              value={naturezaId}
              onChange={(v) => {
                setNaturezaId(v === '' ? '' : Number(v))
                setMotivoId('')
              }}
              options={naturezas.map((n) => ({ value: n.id, label: n.nome }))}
              includeEmpty
              emptyLabel="Selecione"
              disabled={salvando}
            />
          </div>
          <div className="min-w-[10rem] flex-1">
            <Select
              label="Motivo (opcional)"
              value={motivoId}
              onChange={(v) => setMotivoId(v === '' ? '' : Number(v))}
              options={motivos.map((m) => ({ value: m.id, label: m.nome }))}
              includeEmpty
              emptyLabel={naturezaId === '' ? '—' : 'Opcional'}
              disabled={salvando || naturezaId === ''}
            />
          </div>
          <Button type="button" className="h-9 shrink-0" onClick={() => void registrar()} loading={salvando}>
            Registrar
          </Button>
        </div>
      )}

      {demandas.length > 0 && (
        <ul className="mt-2 space-y-1">
          {demandas.map((d) => {
            const podeExcluir =
              user?.role === 'admin' || (user?.id != null && d.atendente_id === user.id)
            return (
              <li
                key={d.id}
                className="flex items-start justify-between gap-2 rounded-lg border border-slate-100 bg-white px-2 py-1.5 text-xs dark:border-slate-800 dark:bg-slate-950/50"
              >
                <div className="min-w-0">
                  <p className="font-medium text-slate-800 dark:text-slate-100">
                    {d.natureza_nome}
                    {d.motivo_nome ? ` · ${d.motivo_nome}` : ''}
                  </p>
                  <p className="text-[10px] text-slate-500">
                    {DESFECHO_ROTULO[d.desfecho] ?? d.desfecho}
                    {d.atendente_nome ? ` · ${d.atendente_nome}` : ''}
                  </p>
                </div>
                {podeExcluir && d.desfecho === 'resolvido_sessao' && podeRegistrar && (
                  <button
                    type="button"
                    className="shrink-0 text-[10px] text-red-500 hover:underline"
                    onClick={() => void excluir(d.id)}
                  >
                    Remover
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
