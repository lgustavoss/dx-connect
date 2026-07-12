import { useEffect, useState } from 'react'
import { atendentes, chatInterno, type ChatInterno } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useAuth } from '../../contexts/AuthContext'
import { Button } from '../ui/Button'
import { useToast } from '../ui/Toast'
import { MODAL_OVERLAY, MODAL_PANEL_COMPACT } from '../../lib/modalPanel'

type Props = {
  open: boolean
  conversaId: number
  participantes: ChatInterno.ParticipanteGrupo[]
  onClose: () => void
  onAtualizado: (conversa: ChatInterno.Conversa) => void
}

export function ChatInternoGrupoMembrosModal({
  open,
  conversaId,
  participantes,
  onClose,
  onAtualizado,
}: Props) {
  const toast = useToast()
  const { user } = useAuth()
  const [lista, setLista] = useState(participantes)
  const [busca, setBusca] = useState('')
  const [resultados, setResultados] = useState<Awaited<ReturnType<typeof atendentes.list>>['items']>([])
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    if (open) setLista(participantes)
  }, [open, participantes])

  useEffect(() => {
    if (!open) {
      setBusca('')
      setResultados([])
      return
    }
    const q = busca.trim()
    if (q.length < 2) {
      setResultados([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const { items } = await atendentes.list({ busca: q, limit: 15, incluir_inativos: false })
        const ids = new Set(lista.map((p) => p.atendente_id))
        setResultados(items.filter((a) => a.id !== user?.id && !ids.has(a.id)))
      } catch {
        setResultados([])
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [busca, open, lista, user?.id])

  async function aplicar(patch: Parameters<typeof chatInterno.atualizarParticipantesGrupo>[1]) {
    setSalvando(true)
    try {
      const conv = await chatInterno.atualizarParticipantesGrupo(conversaId, patch)
      setLista(conv.participantes ?? [])
      onAtualizado(conv)
      toast.showSuccess('Membros atualizados.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível atualizar os membros.'))
    } finally {
      setSalvando(false)
    }
  }

  if (!open) return null

  return (
    <div className={MODAL_OVERLAY} role="dialog" aria-modal="true" onClick={onClose}>
      <div className={MODAL_PANEL_COMPACT} onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Membros do grupo</h2>
        <ul className="mt-4 max-h-40 space-y-1 overflow-y-auto">
          {lista.map((p) => (
            <li
              key={p.atendente_id}
              className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700"
            >
              <div>
                <span className="font-medium text-slate-900 dark:text-slate-100">{p.nome}</span>
                <span className="ml-2 text-xs text-slate-500">{p.papel === 'admin' ? 'Admin' : 'Membro'}</span>
              </div>
              <div className="flex shrink-0 gap-1">
                {p.papel === 'membro' && (
                  <button
                    type="button"
                    disabled={salvando}
                    className="text-xs text-violet-600 hover:underline"
                    onClick={() => void aplicar({ promover_admin: [p.atendente_id] })}
                  >
                    Tornar admin
                  </button>
                )}
                {p.papel === 'admin' && p.atendente_id !== user?.id && (
                  <button
                    type="button"
                    disabled={salvando}
                    className="text-xs text-slate-500 hover:underline"
                    onClick={() => void aplicar({ rebaixar_admin: [p.atendente_id] })}
                  >
                    Rebaixar
                  </button>
                )}
                {p.atendente_id !== user?.id && (
                  <button
                    type="button"
                    disabled={salvando}
                    className="text-xs text-rose-600 hover:underline"
                    onClick={() => void aplicar({ remover: [p.atendente_id] })}
                  >
                    Remover
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>

        <input
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar atendente para adicionar…"
          className="mt-4 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
        />
        <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto">
          {resultados.map((a) => (
            <li key={a.id}>
              <button
                type="button"
                disabled={salvando}
                className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
                onClick={() => void aplicar({ adicionar: [a.id] })}
              >
                {a.nome}
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-4 flex justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </div>
    </div>
  )
}
