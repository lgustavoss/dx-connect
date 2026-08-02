import { useEffect, useMemo, useState } from 'react'
import { setores, type Setores } from '../../api/client'
import { Button } from '../ui/Button'
import { Select } from '../ui/Select'

type Props = {
  open: boolean
  setorIds: number[]
  loading?: boolean
  onClose: () => void
  onConfirm: (setorId: number) => void
}

/** Modal para escolher o setor ao assumir WhatsApp com atendente multi-setor (#628). */
export function AssumirWhatsappSetorModal({
  open,
  setorIds,
  loading = false,
  onClose,
  onConfirm,
}: Props) {
  const [lista, setLista] = useState<Setores.Setor[]>([])
  const [setorId, setSetorId] = useState<number | ''>('')
  const [carregando, setCarregando] = useState(false)

  useEffect(() => {
    if (!open) return
    setSetorId('')
    setCarregando(true)
    void setores
      .list({ limit: 200 })
      .then((page) => setLista(page.items || []))
      .catch(() => setLista([]))
      .finally(() => setCarregando(false))
  }, [open])

  const opcoes = useMemo(() => {
    const ids = new Set(setorIds)
    return lista
      .filter((s) => ids.has(s.id) && s.ativo !== false)
      .map((s) => ({ value: s.id, label: s.nome }))
  }, [lista, setorIds])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[180] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal
      aria-labelledby="assumir-setor-titulo"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="assumir-setor-titulo" className="text-lg font-bold text-slate-900 dark:text-white">
          Escolher setor
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Você atende em mais de um setor. Selecione o setor deste atendimento — ele aparece no
          prefixo das mensagens no WhatsApp do cliente.
        </p>
        <div className="mt-4">
          <Select
            label="Setor"
            value={setorId}
            onChange={(v) => setSetorId(v === '' ? '' : Number(v))}
            options={opcoes}
            placeholder={carregando ? 'Carregando…' : 'Selecione o setor'}
            includeEmpty
            emptyLabel="Selecione…"
            disabled={carregando || loading}
          />
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button
            type="button"
            loading={loading}
            disabled={setorId === '' || carregando}
            onClick={() => {
              if (setorId === '') return
              onConfirm(setorId)
            }}
          >
            Atender
          </Button>
        </div>
      </div>
    </div>
  )
}
