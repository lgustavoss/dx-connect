import { useEffect, useMemo, useState } from 'react'
import { setores, type Setores } from '../../api/client'
import { coletarTodasPaginas } from '../../api/collectPages'
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
  const [erroCarga, setErroCarga] = useState(false)

  useEffect(() => {
    if (!open) return
    setSetorId('')
    setErroCarga(false)
    setCarregando(true)
    let cancelado = false
    // list max limit=100; o bug era `limit: 200` → 422 e lista vazia. GET /setores/{id} é só admin.
    void coletarTodasPaginas<Setores.Setor>((o, l) =>
      setores.list({ incluir_inativos: false, offset: o, limit: l }),
    )
      .then((items) => {
        if (cancelado) return
        setLista(items)
      })
      .catch(() => {
        if (cancelado) return
        setLista([])
        setErroCarga(true)
      })
      .finally(() => {
        if (!cancelado) setCarregando(false)
      })
    return () => {
      cancelado = true
    }
  }, [open])

  const opcoes = useMemo(() => {
    const ids = new Set(setorIds)
    return lista
      .filter((s) => ids.has(s.id) && s.ativo !== false)
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
      .map((s) => ({ value: s.id, label: s.nome }))
  }, [lista, setorIds])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[180] flex items-end justify-center bg-black/50 p-0 backdrop-blur-sm md:items-center md:p-4"
      role="dialog"
      aria-modal
      aria-labelledby="assumir-setor-titulo"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-t-2xl bg-white p-5 shadow-xl md:rounded-2xl dark:bg-slate-900"
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
            disabled={carregando || loading || opcoes.length === 0}
          />
          {!carregando && erroCarga && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
              Não foi possível carregar os setores. Feche e tente de novo.
            </p>
          )}
          {!carregando && !erroCarga && opcoes.length === 0 && (
            <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
              Nenhum setor ativo encontrado no seu vínculo. Peça a um admin para rever os setores do
              seu usuário.
            </p>
          )}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="cancel" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button
            type="button"
            loading={loading}
            disabled={setorId === '' || carregando || opcoes.length === 0}
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
