import { useEffect, useState } from 'react'
import { ticketClassificacao, type TicketClassificacao } from '../../api/client'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'

export type DemandaFormValues = {
  naturezaId: number | ''
  motivoId: number | ''
  descricaoCurta: string
}

type Props = {
  values: DemandaFormValues
  onChange: (values: DemandaFormValues) => void
  disabled?: boolean
  idPrefix?: string
}

export function WhatsappDemandaFormFields({ values, onChange, disabled, idPrefix = 'dem' }: Props) {
  const [naturezas, setNaturezas] = useState<TicketClassificacao.Natureza[]>([])
  const [motivos, setMotivos] = useState<TicketClassificacao.Motivo[]>([])

  useEffect(() => {
    ticketClassificacao
      .listNaturezas({ limit: 100 })
      .then(({ items }) => setNaturezas(items))
      .catch(() => setNaturezas([]))
  }, [])

  useEffect(() => {
    if (values.naturezaId === '') {
      setMotivos([])
      return
    }
    ticketClassificacao
      .listMotivos({ natureza_id: Number(values.naturezaId), limit: 100 })
      .then(({ items }) => setMotivos(items))
      .catch(() => setMotivos([]))
  }, [values.naturezaId])

  return (
    <div className="space-y-3">
      <Select
        label="Natureza"
        value={values.naturezaId}
        onChange={(v) =>
          onChange({
            ...values,
            naturezaId: v === '' ? '' : Number(v),
            motivoId: '',
          })
        }
        options={naturezas.map((n) => ({ value: n.id, label: n.nome }))}
        includeEmpty
        emptyLabel="Selecione a natureza"
        disabled={disabled}
      />
      <Select
        label="Motivo (opcional)"
        value={values.motivoId}
        onChange={(v) => onChange({ ...values, motivoId: v === '' ? '' : Number(v) })}
        options={motivos.map((m) => ({ value: m.id, label: m.nome }))}
        includeEmpty
        emptyLabel={values.naturezaId === '' ? '—' : 'Opcional'}
        disabled={disabled || values.naturezaId === ''}
      />
      <Input
        label="Descrição curta (opcional)"
        value={values.descricaoCurta}
        onChange={(e) => onChange({ ...values, descricaoCurta: e.target.value })}
        disabled={disabled}
        id={`${idPrefix}-desc`}
        placeholder="Resumo do que foi tratado"
      />
    </div>
  )
}

export function demandaFormPayload(values: DemandaFormValues) {
  return {
    natureza_id: Number(values.naturezaId),
    motivo_id: values.motivoId === '' ? null : Number(values.motivoId),
    descricao_curta: values.descricaoCurta.trim() || null,
  }
}

export function demandaFormFromDemanda(d: {
  natureza_id: number
  motivo_id?: number | null
  descricao_curta?: string | null
}): DemandaFormValues {
  return {
    naturezaId: d.natureza_id,
    motivoId: d.motivo_id ?? '',
    descricaoCurta: d.descricao_curta ?? '',
  }
}

export const DEMANDA_FORM_VAZIO: DemandaFormValues = {
  naturezaId: '',
  motivoId: '',
  descricaoCurta: '',
}
