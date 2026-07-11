import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { atendentes, chatInterno } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useAuth } from '../../contexts/AuthContext'
import { useChatInterno } from '../../contexts/ChatInternoContext'
import { Button } from '../ui/Button'
import { useToast } from '../ui/Toast'
import { MODAL_OVERLAY, MODAL_PANEL_COMPACT } from '../../lib/modalPanel'

type Props = {
  open: boolean
  onClose: () => void
}

export function ChatInternoNovaConversaModal({ open, onClose }: Props) {
  const toast = useToast()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { carregar } = useChatInterno()
  const [busca, setBusca] = useState('')
  const [resultados, setResultados] = useState<Awaited<ReturnType<typeof atendentes.list>>['items']>([])
  const [buscando, setBuscando] = useState(false)
  const [criando, setCriando] = useState(false)

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
      setBuscando(true)
      try {
        const { items } = await atendentes.list({ busca: q, limit: 20, incluir_inativos: false })
        setResultados(items.filter((a) => a.id !== user?.id))
      } catch {
        setResultados([])
      } finally {
        setBuscando(false)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [busca, open, user?.id])

  async function iniciar(atendenteId: number) {
    setCriando(true)
    try {
      const conv = await chatInterno.criarDireta(atendenteId)
      onClose()
      await carregar(true)
      navigate(`/chat/interno/${conv.id}`)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível iniciar a conversa.'))
    } finally {
      setCriando(false)
    }
  }

  if (!open) return null

  return (
    <div className={MODAL_OVERLAY} role="dialog" aria-modal="true" onClick={onClose}>
      <div className={MODAL_PANEL_COMPACT} onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Nova conversa direta</h2>
        <p className="mt-1 text-sm text-slate-500">Busque um atendente por nome ou e-mail.</p>
        <input
          type="search"
          autoFocus
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Nome ou e-mail…"
          className="mt-4 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
        />
        <ul className="mt-3 max-h-56 space-y-1 overflow-y-auto">
          {buscando && <li className="px-2 py-3 text-sm text-slate-400">Buscando…</li>}
          {!buscando && busca.trim().length >= 2 && resultados.length === 0 && (
            <li className="px-2 py-3 text-sm text-slate-400">Nenhum atendente encontrado.</li>
          )}
          {resultados.map((a) => (
            <li key={a.id}>
              <button
                type="button"
                disabled={criando}
                className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
                onClick={() => void iniciar(a.id)}
              >
                <span className="font-medium text-slate-900 dark:text-slate-100">{a.nome}</span>
                <span className="block text-xs text-slate-500">{a.email}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </div>
    </div>
  )
}
