import { useCallback, useEffect, useState } from 'react'
import { tickets, type Tickets } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { exibirProtocolo } from '../lib/exibirProtocolo'
import { Input } from './ui/Input'
import { useToast } from './ui/Toast'

type Props = {
  /** Ticket atual — nunca aparece na lista. */
  ticketAtualId: number
  /** IDs adicionais a omitir (já vinculados, filhos, etc.). */
  excluirIds?: number[]
  /** Restringe a listagem (ex.: duplicado = mesma rede e empresa). */
  filtroEmpresaId?: number | null
  filtroRedeId?: number | null
  label?: string
  hint?: string
  disabled?: boolean
  loadingExterno?: boolean
  onSelecionar: (ticket: Tickets.Ticket) => void
}

export function TicketBuscaPicker({
  ticketAtualId,
  excluirIds = [],
  filtroEmpresaId,
  filtroRedeId,
  label = 'Buscar ticket em aberto',
  hint = 'Liste tickets abertos; filtre por protocolo, assunto ou empresa.',
  disabled,
  loadingExterno,
  onSelecionar,
}: Props) {
  const toast = useToast()
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [itens, setItens] = useState<Tickets.Ticket[]>([])
  const [loading, setLoading] = useState(false)

  const omitir = useCallback(
    (id: number) => id === ticketAtualId || excluirIds.includes(id),
    [excluirIds, ticketAtualId],
  )

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 300)
    return () => clearTimeout(t)
  }, [busca])

  const filtrosAtivos = filtroEmpresaId != null || filtroRedeId != null

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    tickets
      .list({
        situacao: 'abertos',
        busca: debouncedBusca || undefined,
        empresa_id: filtroEmpresaId ?? undefined,
        rede_id: filtroRedeId ?? undefined,
        limit: 20,
        ordenar_por: 'protocolo',
        ordem: 'desc',
      })
      .then((r) => {
        if (cancelled) return
        setItens(r.items.filter((t) => !omitir(t.id)))
      })
      .catch((err) => {
        if (cancelled) return
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível buscar tickets.'))
        setItens([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [debouncedBusca, filtroEmpresaId, filtroRedeId, omitir, toast])

  const bloqueado = disabled || loadingExterno

  return (
    <div className="min-w-0">
      <Input
        label={label}
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        placeholder="Protocolo, assunto ou empresa…"
        disabled={bloqueado}
      />
      {hint ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p> : null}
      <div
        className="mt-2 max-h-52 overflow-y-auto rounded-lg border border-slate-200/90 bg-white dark:border-slate-700/80 dark:bg-slate-950/40"
        role="listbox"
        aria-label="Tickets em aberto"
      >
        {loading ? (
          <p className="px-3 py-4 text-center text-sm text-slate-500 dark:text-slate-400">Carregando…</p>
        ) : itens.length === 0 ? (
          <p className="px-3 py-4 text-center text-sm text-slate-500 dark:text-slate-400">
            {debouncedBusca
              ? 'Nenhum ticket em aberto encontrado.'
              : filtrosAtivos
                ? 'Nenhum outro ticket em aberto na mesma rede e empresa.'
                : 'Nenhum ticket em aberto disponível para vincular.'}
          </p>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {itens.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  role="option"
                  disabled={bloqueado}
                  onClick={() => onSelecionar(t)}
                  className="flex w-full flex-col gap-0.5 px-3 py-2.5 text-left transition-colors hover:bg-cyan-50/80 disabled:opacity-50 dark:hover:bg-cyan-950/30"
                >
                  <span className="font-mono text-xs font-semibold text-cyan-800 dark:text-cyan-300">
                    {exibirProtocolo(t.protocolo)}
                  </span>
                  <span className="line-clamp-2 text-sm text-slate-800 dark:text-slate-100">{t.assunto}</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {[t.empresa_nome, t.setor_nome, t.status_nome].filter(Boolean).join(' · ') || `Ticket #${t.id}`}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
