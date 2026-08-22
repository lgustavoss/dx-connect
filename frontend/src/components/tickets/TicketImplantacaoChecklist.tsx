import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, tickets, type Tickets } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useAuth } from '../../contexts/AuthContext'
import { useToast } from '../ui/Toast'
import { CheckboxField } from '../ui/CheckboxField'
import { Input } from '../ui/Input'

const CHAVE_PDVS = 'cadastrar_pdvs'

export function TicketImplantacaoChecklist({
  ticketId,
  empresaId,
  fechado,
}: {
  ticketId: number
  empresaId: number | null
  fechado: boolean
}) {
  const toast = useToast()
  const { isAdmin } = useAuth()
  const [data, setData] = useState<Tickets.Checklist | null>(null)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [obsDraft, setObsDraft] = useState<Record<number, string>>({})

  const load = useCallback(() => {
    tickets
      .getChecklist(ticketId)
      .then((c) => {
        setData(c)
        const next: Record<number, string> = {}
        for (const it of c.itens) next[it.id] = it.observacao || ''
        setObsDraft(next)
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 403) return
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar o checklist.'))
      })
  }, [ticketId, toast])

  useEffect(() => {
    load()
  }, [load])

  if (!data?.aplicavel) return null

  const soLeitura = fechado && !isAdmin

  const patch = async (itemId: number, body: Tickets.ChecklistItemPatch) => {
    setSavingId(itemId)
    try {
      const next = await tickets.patchChecklistItem(ticketId, itemId, body)
      setData(next)
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível atualizar o item.'))
    } finally {
      setSavingId(null)
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-3 sm:p-4 dark:border-slate-800 dark:bg-slate-900/40">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Checklist de implantação</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            {data.progresso_pct}% concluído
            {data.itens_obrigatorios_pendentes > 0
              ? ` · ${data.itens_obrigatorios_pendentes} obrigatório(s) pendente(s)`
              : ' · itens obrigatórios concluídos'}
          </p>
        </div>
        <div
          className="h-2 w-32 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"
          role="progressbar"
          aria-valuenow={data.progresso_pct}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div className="h-full bg-cyan-600 dark:bg-cyan-500" style={{ width: `${data.progresso_pct}%` }} />
        </div>
      </div>
      <ul className="mt-3 space-y-3">
        {data.itens.map((item) => (
          <li
            key={item.id}
            className="rounded-lg border border-slate-100 p-2.5 dark:border-slate-800"
          >
            <CheckboxField
              checked={item.concluido}
              disabled={soLeitura || savingId === item.id}
              onChange={(e) => void patch(item.id, { concluido: e.target.checked })}
            >
              {item.titulo}
              {item.obrigatorio ? (
                <span className="ml-1 text-[10px] font-semibold uppercase text-amber-700 dark:text-amber-400">
                  obrigatório
                </span>
              ) : null}
            </CheckboxField>
            {item.descricao ? (
              <p className="mt-1 pl-7 text-xs text-slate-500 dark:text-slate-400">{item.descricao}</p>
            ) : null}
            {item.chave === CHAVE_PDVS ? (
              <p className="mt-1 pl-7 text-xs text-slate-600 dark:text-slate-300">
                PDVs ativos: {data.pdvs_ativos ?? 0}
                {isAdmin && empresaId ? (
                  <>
                    {' · '}
                    <Link
                      to={`/empresas/${empresaId}?aba=pdvs`}
                      className="font-medium text-cyan-700 underline dark:text-cyan-400"
                    >
                      Abrir cadastro de PDVs
                    </Link>
                  </>
                ) : (
                  <span className="text-slate-500"> · o admin cadastra os PDVs na empresa</span>
                )}
              </p>
            ) : null}
            {item.concluido && item.concluido_por_nome ? (
              <p className="mt-1 pl-7 text-[11px] text-slate-400">Marcado por {item.concluido_por_nome}</p>
            ) : null}
            <div className="mt-2 pl-7">
              <Input
                label="Observação"
                value={obsDraft[item.id] ?? ''}
                disabled={soLeitura}
                onChange={(e) => setObsDraft((p) => ({ ...p, [item.id]: e.target.value }))}
                onBlur={() => {
                  const val = (obsDraft[item.id] ?? '').trim()
                  if (val === (item.observacao || '')) return
                  void patch(item.id, { observacao: val || null })
                }}
              />
            </div>
          </li>
        ))}
      </ul>
      {fechado && !isAdmin ? (
        <p className="mt-2 text-xs text-slate-500">Ticket fechado — só um admin altera o checklist.</p>
      ) : fechado && isAdmin ? (
        <p className="mt-2 text-xs text-slate-500">Ticket fechado — como admin ainda podes ajustar o checklist.</p>
      ) : data.itens_obrigatorios_pendentes > 0 ? (
        <p className="mt-2 text-xs text-slate-500">O ticket só pode ser fechado quando os itens obrigatórios estiverem concluídos.</p>
      ) : null}
    </section>
  )
}
