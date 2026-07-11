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

type Modo = 'direta' | 'grupo'

export function ChatInternoNovaConversaModal({ open, onClose }: Props) {
  const toast = useToast()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { carregar } = useChatInterno()
  const [modo, setModo] = useState<Modo>('direta')
  const [busca, setBusca] = useState('')
  const [tituloGrupo, setTituloGrupo] = useState('')
  const [selecionados, setSelecionados] = useState<number[]>([])
  const [resultados, setResultados] = useState<Awaited<ReturnType<typeof atendentes.list>>['items']>([])
  const [buscando, setBuscando] = useState(false)
  const [criando, setCriando] = useState(false)

  useEffect(() => {
    if (!open) {
      setModo('direta')
      setBusca('')
      setTituloGrupo('')
      setSelecionados([])
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

  function toggleSelecionado(id: number) {
    setSelecionados((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function iniciarDireta(atendenteId: number) {
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

  async function criarGrupo() {
    const titulo = tituloGrupo.trim()
    if (!titulo || selecionados.length === 0) return
    setCriando(true)
    try {
      const conv = await chatInterno.criarGrupo(titulo, selecionados)
      onClose()
      await carregar(true)
      navigate(`/chat/interno/${conv.id}`)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível criar o grupo.'))
    } finally {
      setCriando(false)
    }
  }

  if (!open) return null

  return (
    <div className={MODAL_OVERLAY} role="dialog" aria-modal="true" onClick={onClose}>
      <div className={MODAL_PANEL_COMPACT} onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Nova conversa</h2>
        <div className="mt-3 flex gap-1 rounded-lg border border-slate-200 bg-slate-100 p-1 dark:border-slate-700 dark:bg-slate-900">
          <button
            type="button"
            onClick={() => setModo('direta')}
            className={`flex-1 rounded-md px-2 py-1.5 text-xs font-semibold ${
              modo === 'direta'
                ? 'bg-white text-cyan-700 shadow-sm dark:bg-slate-800 dark:text-cyan-300'
                : 'text-slate-500'
            }`}
          >
            Direta
          </button>
          <button
            type="button"
            onClick={() => setModo('grupo')}
            className={`flex-1 rounded-md px-2 py-1.5 text-xs font-semibold ${
              modo === 'grupo'
                ? 'bg-white text-violet-700 shadow-sm dark:bg-slate-800 dark:text-violet-300'
                : 'text-slate-500'
            }`}
          >
            Grupo
          </button>
        </div>

        {modo === 'direta' ? (
          <>
            <p className="mt-2 text-sm text-slate-500">Busque um atendente por nome ou e-mail.</p>
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
                    onClick={() => void iniciarDireta(a.id)}
                  >
                    <span className="font-medium text-slate-900 dark:text-slate-100">{a.nome}</span>
                    <span className="block text-xs text-slate-500">{a.email}</span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <>
            <p className="mt-2 text-sm text-slate-500">Nome do grupo e participantes (máx. 50).</p>
            <input
              type="text"
              autoFocus
              value={tituloGrupo}
              onChange={(e) => setTituloGrupo(e.target.value)}
              placeholder="Nome do grupo"
              maxLength={120}
              className="mt-4 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
            />
            <input
              type="search"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Adicionar atendentes…"
              className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
            />
            {selecionados.length > 0 && (
              <p className="mt-2 text-xs text-slate-500">{selecionados.length} selecionado(s)</p>
            )}
            <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
              {buscando && <li className="px-2 py-2 text-sm text-slate-400">Buscando…</li>}
              {resultados.map((a) => {
                const marcado = selecionados.includes(a.id)
                return (
                  <li key={a.id}>
                    <button
                      type="button"
                      className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800 ${
                        marcado ? 'ring-1 ring-violet-400' : ''
                      }`}
                      onClick={() => toggleSelecionado(a.id)}
                    >
                      <span
                        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                          marcado ? 'border-violet-600 bg-violet-600 text-white' : 'border-slate-300'
                        }`}
                      >
                        {marcado ? '✓' : ''}
                      </span>
                      <span>
                        <span className="font-medium text-slate-900 dark:text-slate-100">{a.nome}</span>
                        <span className="block text-xs text-slate-500">{a.email}</span>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
            <div className="mt-4 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={onClose}>
                Cancelar
              </Button>
              <Button
                type="button"
                disabled={criando || !tituloGrupo.trim() || selecionados.length === 0}
                onClick={() => void criarGrupo()}
              >
                Criar grupo
              </Button>
            </div>
          </>
        )}

        {modo === 'direta' && (
          <div className="mt-4 flex justify-end">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
