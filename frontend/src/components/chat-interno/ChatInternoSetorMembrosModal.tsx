import { useEffect, useState } from 'react'
import { chatInterno, type ChatInterno } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useAuth } from '../../contexts/AuthContext'
import { useToast } from '../ui/Toast'
import { MODAL_OVERLAY, MODAL_PANEL_SCROLLABLE } from '../../lib/modalPanel'

type Props = {
  open: boolean
  setorId: number
  tituloSetor?: string
  onClose: () => void
}

/** Modal read-only: membros do canal de setor + quem está online (#S202608-0008 / #941). */
export function ChatInternoSetorMembrosModal({ open, setorId, tituloSetor, onClose }: Props) {
  const { user } = useAuth()
  const toast = useToast()
  const [carregando, setCarregando] = useState(false)
  const [dados, setDados] = useState<ChatInterno.MembrosCanalSetorLista | null>(null)

  useEffect(() => {
    if (!open) return
    setCarregando(true)
    setDados(null)
    let cancelado = false
    void chatInterno
      .listarMembrosCanalSetor(setorId)
      .then((lista) => {
        if (!cancelado) setDados(lista)
      })
      .catch((err) => {
        if (cancelado) return
        toast.showError(mensagemFalhaParaToast(err))
        onClose()
      })
      .finally(() => {
        if (!cancelado) setCarregando(false)
      })
    return () => {
      cancelado = true
    }
  }, [open, setorId]) // toast/onClose estáveis o suficiente para o fetch do modal

  if (!open) return null

  const titulo = dados?.setor_nome || tituloSetor || 'Canal do setor'
  const onlineCount = dados?.online_count ?? 0
  const total = dados?.total ?? 0

  return (
    <div className={MODAL_OVERLAY} role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className={`${MODAL_PANEL_SCROLLABLE} max-w-md`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="setor-membros-titulo"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <div className="min-w-0">
            <h2 id="setor-membros-titulo" className="text-lg font-bold text-slate-900 dark:text-white">
              {titulo}
            </h2>
            <p className="mt-0.5 text-sm text-slate-500">
              {carregando
                ? 'Carregando membros…'
                : `${total} ${total === 1 ? 'membro' : 'membros'}${total > 0 ? ` · ${onlineCount} online` : ''}`}
            </p>
          </div>
          <button
            type="button"
            className="flex size-9 shrink-0 items-center justify-center rounded-lg text-xl text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            onClick={onClose}
            aria-label="Fechar"
          >
            &times;
          </button>
        </div>
        <div className="dx-scrollbar max-h-[min(60dvh,24rem)] overflow-y-auto px-5 py-4">
          {carregando ? (
            <p className="py-6 text-center text-sm text-slate-400 animate-pulse">Carregando…</p>
          ) : !dados || dados.items.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-500">
              Nenhum usuário vinculado a este setor.
            </p>
          ) : (
            <ul className="space-y-2">
              {dados.items.map((m) => {
                const isSelf = m.atendente_id === user?.id
                return (
                  <li
                    key={m.atendente_id}
                    className="flex items-center gap-3 rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-700"
                  >
                    <span
                      className={`size-2.5 shrink-0 rounded-full ${
                        m.online ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'
                      }`}
                      title={m.online ? 'Online' : 'Offline'}
                      aria-hidden
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                        {m.nome}
                        {isSelf ? <span className="ml-1 font-normal text-slate-500">(você)</span> : null}
                      </p>
                      <p className="text-xs text-slate-500">{m.online ? 'Online' : 'Offline'}</p>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
