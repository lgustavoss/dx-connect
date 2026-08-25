import { useEffect, useMemo, useState } from 'react'
import { setores, type Setores } from '../../api/client'
import { coletarTodasPaginas } from '../../api/collectPages'
import { Button } from '../ui/Button'

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
      className="fixed inset-0 z-[180] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal
      aria-labelledby="assumir-setor-titulo"
      onClick={onClose}
    >
      <div
        className="flex max-h-[min(85dvh,var(--vv-height,85dvh))] w-full max-w-md flex-col overflow-hidden rounded-2xl bg-white shadow-xl dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="shrink-0 px-5 pt-5">
          <h2 id="assumir-setor-titulo" className="text-lg font-bold text-slate-900 dark:text-white">
            Escolher setor
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Você atende em mais de um setor. Selecione o setor deste atendimento — ele aparece no
            prefixo das mensagens no WhatsApp do cliente.
          </p>
        </div>
        <div className="dx-scrollbar mt-4 min-h-0 flex-1 overflow-y-auto px-5">
          <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Setor</p>
          {carregando ? (
            <p className="py-3 text-sm text-slate-500">Carregando…</p>
          ) : erroCarga ? (
            <p className="py-2 text-sm text-red-600 dark:text-red-400">
              Não foi possível carregar os setores. Feche e tente de novo.
            </p>
          ) : opcoes.length === 0 ? (
            <p className="py-2 text-sm text-amber-700 dark:text-amber-300">
              Nenhum setor ativo encontrado no seu vínculo. Peça a um admin para rever os setores do
              seu usuário.
            </p>
          ) : (
            <div
              role="radiogroup"
              aria-label="Setor do atendimento"
              className="flex flex-col gap-2 pb-1"
            >
              {opcoes.map((o) => {
                const selected = setorId === o.value
                return (
                  <button
                    key={o.value}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    disabled={loading}
                    onClick={() => setSetorId(o.value)}
                    className={`flex min-h-11 w-full items-center rounded-xl px-3 py-2.5 text-left text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/40 disabled:opacity-50 ${
                      selected
                        ? 'bg-slate-900 font-medium text-white dark:bg-cyan-600 dark:text-white'
                        : 'bg-slate-50 text-slate-800 ring-1 ring-slate-200/90 hover:bg-slate-100 dark:bg-slate-800/60 dark:text-slate-100 dark:ring-slate-700 dark:hover:bg-slate-800'
                    }`}
                  >
                    <span className="min-w-0 flex-1 break-words">{o.label}</span>
                  </button>
                )
              })}
            </div>
          )}
        </div>
        <div className="flex shrink-0 justify-end gap-2 border-t border-slate-100 px-5 py-4 dark:border-slate-800">
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
