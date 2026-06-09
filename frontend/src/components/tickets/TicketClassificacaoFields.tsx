import { useEffect, useMemo, useState } from 'react'
import { ApiError, ticketClassificacao, type TicketClassificacao } from '../../api/client'
import { Select } from '../ui/Select'
import { Input } from '../ui/Input'

export type ClassificacaoFormValue = {
  naturezaId: number | ''
  motivoId: number | ''
  motivoOutroTexto: string
}

type Props = {
  value: ClassificacaoFormValue
  onChange: (next: ClassificacaoFormValue) => void
  disabled?: boolean
  motivoLabel?: string
}

export function TicketClassificacaoFields({
  value,
  onChange,
  disabled,
  motivoLabel = 'Motivo',
}: Props) {
  const [naturezas, setNaturezas] = useState<TicketClassificacao.Natureza[]>([])
  const [motivos, setMotivos] = useState<TicketClassificacao.Motivo[]>([])
  const [loadingMotivos, setLoadingMotivos] = useState(false)

  useEffect(() => {
    ticketClassificacao
      .listNaturezas({ limit: 100 })
      .then(({ items }) => setNaturezas(items))
      .catch((err) => {
        if (!(err instanceof ApiError && err.status === 403)) {
          setNaturezas([])
        }
      })
  }, [])

  useEffect(() => {
    if (value.naturezaId === '') {
      setMotivos([])
      return
    }
    setLoadingMotivos(true)
    ticketClassificacao
      .listMotivos({ natureza_id: Number(value.naturezaId), limit: 100 })
      .then(({ items }) => setMotivos(items))
      .catch(() => setMotivos([]))
      .finally(() => setLoadingMotivos(false))
  }, [value.naturezaId])

  const motivoSelecionado = useMemo(
    () => motivos.find((m) => m.id === value.motivoId),
    [motivos, value.motivoId],
  )
  const exigeOutroTexto = (motivoSelecionado?.slug ?? '').toLowerCase() === 'outros'

  return (
    <div className="space-y-3">
      <Select
        label="Natureza"
        value={value.naturezaId}
        onChange={(v) =>
          onChange({
            naturezaId: v === '' ? '' : Number(v),
            motivoId: '',
            motivoOutroTexto: '',
          })
        }
        options={naturezas.map((n) => ({ value: n.id, label: n.nome }))}
        includeEmpty
        emptyLabel="— Selecione a natureza —"
        disabled={disabled || naturezas.length === 0}
      />
      <Select
        label={motivoLabel}
        value={value.motivoId}
        onChange={(v) =>
          onChange({
            ...value,
            motivoId: v === '' ? '' : Number(v),
            motivoOutroTexto: '',
          })
        }
        options={motivos.map((m) => ({ value: m.id, label: m.nome }))}
        includeEmpty
        emptyLabel={
          value.naturezaId === ''
            ? '— Selecione a natureza primeiro —'
            : loadingMotivos
              ? 'Carregando motivos…'
              : '— Selecione o motivo —'
        }
        disabled={disabled || value.naturezaId === '' || loadingMotivos}
      />
      {exigeOutroTexto ? (
        <Input
          label="Descreva o atendimento"
          value={value.motivoOutroTexto}
          onChange={(e) => onChange({ ...value, motivoOutroTexto: e.target.value })}
          disabled={disabled}
          maxLength={255}
          placeholder="Obrigatório para motivo Outros"
        />
      ) : null}
    </div>
  )
}

export function classificacaoFromTicket(ticket: {
  natureza_id?: number | null
  motivo_id?: number | null
  motivo_outro_texto?: string | null
}): ClassificacaoFormValue {
  return {
    naturezaId: ticket.natureza_id ?? '',
    motivoId: ticket.motivo_id ?? '',
    motivoOutroTexto: ticket.motivo_outro_texto ?? '',
  }
}

export function patchClassificacaoFromForm(
  form: ClassificacaoFormValue,
): { motivo_id: number; motivo_outro_texto?: string } | null {
  if (form.motivoId === '') return null
  const patch: { motivo_id: number; motivo_outro_texto?: string } = {
    motivo_id: Number(form.motivoId),
  }
  const outro = form.motivoOutroTexto.trim()
  if (outro) patch.motivo_outro_texto = outro
  return patch
}
