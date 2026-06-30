import { useEffect, useState } from 'react'
import { ticketClassificacao, type Kb, type TicketClassificacao } from '../../api/client'
import { Button } from '../ui/Button'
import { Select } from '../ui/Select'

export type MotivoLinkDraft = {
  key: string
  tipo: 'motivo' | 'natureza'
  targetId: number | ''
  ordem: number
}

type Props = {
  links: MotivoLinkDraft[]
  onChange: (links: MotivoLinkDraft[]) => void
  disabled?: boolean
}

function novoKey() {
  return `link-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function draftFromApiLinks(items: Kb.MotivoLinkItem[]): MotivoLinkDraft[] {
  return items.map((item, idx) => ({
    key: `link-${item.id ?? idx}`,
    tipo: item.motivo_id != null ? 'motivo' : 'natureza',
    targetId: item.motivo_id ?? item.natureza_id ?? '',
    ordem: item.ordem ?? idx,
  }))
}

export function draftToApiLinks(links: MotivoLinkDraft[]): Kb.MotivoLinkItem[] {
  return links
    .filter((l) => l.targetId !== '')
    .map((l, idx) => ({
      ordem: l.ordem ?? idx,
      ...(l.tipo === 'motivo'
        ? { motivo_id: Number(l.targetId), natureza_id: null }
        : { natureza_id: Number(l.targetId), motivo_id: null }),
    }))
}

export function KbArtigoMotivoLinksFields({ links, onChange, disabled }: Props) {
  const [naturezas, setNaturezas] = useState<TicketClassificacao.Natureza[]>([])
  const [motivos, setMotivos] = useState<TicketClassificacao.Motivo[]>([])

  useEffect(() => {
    ticketClassificacao
      .listNaturezas({ limit: 100 })
      .then(({ items }) => setNaturezas(items))
      .catch(() => setNaturezas([]))
    ticketClassificacao
      .listMotivos({ limit: 200 })
      .then(({ items }) => setMotivos(items))
      .catch(() => setMotivos([]))
  }, [])

  function adicionar() {
    onChange([...links, { key: novoKey(), tipo: 'motivo', targetId: '', ordem: links.length }])
  }

  function atualizar(key: string, patch: Partial<MotivoLinkDraft>) {
    onChange(
      links.map((l) => {
        if (l.key !== key) return l
        const next = { ...l, ...patch }
        if (patch.tipo && patch.tipo !== l.tipo) next.targetId = ''
        return next
      }),
    )
  }

  function remover(key: string) {
    onChange(links.filter((l) => l.key !== key))
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Vincule este manual a naturezas ou motivos de ticket. Até 5 sugestões aparecem ao classificar chamados ou
        registrar demandas.
      </p>
      {links.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Nenhum vínculo configurado.</p>
      ) : (
        <ul className="space-y-2">
          {links.map((link) => (
            <li
              key={link.key}
              className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-900/40 sm:flex-row sm:items-end"
            >
              <Select
                label="Tipo"
                value={link.tipo}
                onChange={(v) => atualizar(link.key, { tipo: v as 'motivo' | 'natureza' })}
                options={[
                  { value: 'motivo', label: 'Motivo específico' },
                  { value: 'natureza', label: 'Toda a natureza' },
                ]}
                disabled={disabled}
              />
              {link.tipo === 'natureza' ? (
                <Select
                  label="Natureza"
                  value={link.targetId}
                  onChange={(v) => atualizar(link.key, { targetId: v === '' ? '' : Number(v) })}
                  options={naturezas.map((n) => ({ value: n.id, label: n.nome }))}
                  includeEmpty
                  emptyLabel="Selecione"
                  disabled={disabled}
                  className="min-w-0 flex-1"
                />
              ) : (
                <Select
                  label="Motivo"
                  value={link.targetId}
                  onChange={(v) => atualizar(link.key, { targetId: v === '' ? '' : Number(v) })}
                  options={motivos.map((m) => {
                    const nat = naturezas.find((n) => n.id === m.natureza_id)
                    return { value: m.id, label: nat ? `${nat.nome} › ${m.nome}` : m.nome }
                  })}
                  includeEmpty
                  emptyLabel="Selecione"
                  disabled={disabled}
                  className="min-w-0 flex-1"
                />
              )}
              <Button type="button" variant="secondary" onClick={() => remover(link.key)} disabled={disabled}>
                Remover
              </Button>
            </li>
          ))}
        </ul>
      )}
      <Button type="button" variant="secondary" onClick={adicionar} disabled={disabled || links.length >= 20}>
        Adicionar vínculo
      </Button>
    </div>
  )
}
