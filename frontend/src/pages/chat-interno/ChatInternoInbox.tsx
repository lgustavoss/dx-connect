import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { atendentes, chatInterno, type Atendentes, type ChatInterno } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { useEventStream } from '../../contexts/EventStreamContext'
import { useAuth } from '../../contexts/AuthContext'
import { MODAL_OVERLAY, MODAL_PANEL_COMPACT } from '../../lib/modalPanel'
import {
  formatarHoraRelativa,
  previewTexto,
  type FiltroInboxChatInterno,
} from '../../lib/chatInternoUtils'

const FILTROS: { id: FiltroInboxChatInterno; label: string }[] = [
  { id: 'todas', label: 'Todas' },
  { id: 'direta', label: 'Diretas' },
  { id: 'setor', label: 'Setores' },
]

function tabClass(active: boolean) {
  return `rounded-lg px-4 py-2 text-sm font-bold transition-all ${
    active
      ? 'bg-white text-violet-600 shadow-sm dark:bg-slate-700 dark:text-violet-400'
      : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
  }`
}

export function ChatInternoInbox() {
  const toast = useToast()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { subscribe, useFallback } = useEventStream()
  const [conversas, setConversas] = useState<ChatInterno.ConversaInbox[]>([])
  const [filtro, setFiltro] = useState<FiltroInboxChatInterno>('todas')
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(false)
  const isFirstLoad = useRef(true)

  const [modalAberto, setModalAberto] = useState(false)
  const [buscaAtendente, setBuscaAtendente] = useState('')
  const [resultados, setResultados] = useState<Atendentes.Atendente[]>([])
  const [buscando, setBuscando] = useState(false)
  const [criando, setCriando] = useState(false)

  const carregar = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    setErro(false)
    try {
      const rows = await chatInterno.listarConversas()
      setConversas(rows)
    } catch (err) {
      setErro(true)
      if (!silent) toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as conversas.'))
    } finally {
      setLoading(false)
      isFirstLoad.current = false
    }
  }, [toast])

  useEffect(() => {
    void carregar()
  }, [carregar])

  useEffect(() => {
    const refresh = () => void carregar(true)
    const unsubMsg = subscribe('chat.interno.mensagem', refresh)
    const unsubContagem = subscribe('notificacao.contagem', refresh)
    return () => {
      unsubMsg()
      unsubContagem()
    }
  }, [subscribe, carregar])

  useEffect(() => {
    const intervalMs = useFallback ? 10_000 : 8_000
    const timer = setInterval(() => void carregar(true), intervalMs)
    return () => clearInterval(timer)
  }, [carregar, useFallback])

  useEffect(() => {
    if (!modalAberto) return
    const q = buscaAtendente.trim()
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
  }, [buscaAtendente, modalAberto, user?.id])

  const filtradas = useMemo(() => {
    if (filtro === 'todas') return conversas
    return conversas.filter((c) => c.tipo === filtro)
  }, [conversas, filtro])

  async function iniciarConversa(atendenteId: number) {
    setCriando(true)
    try {
      const conv = await chatInterno.criarDireta(atendenteId)
      setModalAberto(false)
      setBuscaAtendente('')
      setResultados([])
      await carregar(true)
      navigate(`/chat-interno/${conv.id}`)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível iniciar a conversa.'))
    } finally {
      setCriando(false)
    }
  }

  if (loading && isFirstLoad.current) {
    return (
      <div className="flex h-48 items-center justify-center text-sm font-medium text-slate-400 animate-pulse">
        Carregando conversas…
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <nav className="inline-flex max-w-full items-center overflow-x-auto rounded-xl bg-slate-100 p-1.5 dark:bg-slate-800/60 ring-1 ring-slate-200 dark:ring-slate-800">
          {FILTROS.map((f) => (
            <button key={f.id} type="button" className={tabClass(filtro === f.id)} onClick={() => setFiltro(f.id)}>
              {f.label}
            </button>
          ))}
        </nav>
        <Button type="button" onClick={() => setModalAberto(true)}>
          Nova conversa
        </Button>
      </div>

      {erro && conversas.length === 0 ? (
        <Card className="border-dashed p-8 text-center">
          <p className="text-sm text-rose-600 dark:text-rose-400">Não foi possível carregar o inbox.</p>
          <Button type="button" className="mt-4" variant="secondary" onClick={() => void carregar()}>
            Tentar novamente
          </Button>
        </Card>
      ) : filtradas.length === 0 ? (
        <Card className="border-dashed p-10 text-center">
          <p className="text-sm text-slate-500">
            {filtro === 'todas'
              ? 'Nenhuma conversa ainda. Inicie um chat direto ou acesse o canal do seu setor.'
              : `Nenhuma conversa do tipo «${filtro}».`}
          </p>
        </Card>
      ) : (
        <ul className="space-y-2">
          {filtradas.map((c) => (
            <li key={c.id}>
              <Link
                to={`/chat-interno/${c.id}`}
                className="flex items-center gap-3 rounded-2xl border border-slate-200/90 bg-white px-4 py-3 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-800/80 dark:bg-slate-900/50 dark:hover:bg-slate-800/80"
              >
                <div
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${
                    c.tipo === 'setor' ? 'bg-amber-500' : 'bg-violet-600'
                  }`}
                >
                  {c.tipo === 'setor' ? 'S' : c.titulo.slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate font-semibold text-slate-900 dark:text-slate-100">{c.titulo}</p>
                    {c.tipo === 'setor' && (
                      <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                        Canal
                      </span>
                    )}
                  </div>
                  <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                    {previewTexto(c.ultima_mensagem_corpo, 60)}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <span className="text-[11px] text-slate-400">{formatarHoraRelativa(c.ultima_mensagem_em)}</span>
                  {c.nao_lidas_count > 0 && (
                    <span className="rounded-full bg-violet-600 px-2 py-0.5 text-xs font-bold text-white">
                      {c.nao_lidas_count > 99 ? '99+' : c.nao_lidas_count}
                    </span>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {modalAberto && (
        <div className={MODAL_OVERLAY} role="dialog" aria-modal="true" onClick={() => setModalAberto(false)}>
          <div className={MODAL_PANEL_COMPACT} onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Nova conversa direta</h2>
            <p className="mt-1 text-sm text-slate-500">Busque um atendente por nome ou e-mail.</p>
            <input
              type="search"
              autoFocus
              value={buscaAtendente}
              onChange={(e) => setBuscaAtendente(e.target.value)}
              placeholder="Nome ou e-mail…"
              className="mt-4 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
            />
            <ul className="mt-3 max-h-56 space-y-1 overflow-y-auto">
              {buscando && <li className="px-2 py-3 text-sm text-slate-400">Buscando…</li>}
              {!buscando && buscaAtendente.trim().length >= 2 && resultados.length === 0 && (
                <li className="px-2 py-3 text-sm text-slate-400">Nenhum atendente encontrado.</li>
              )}
              {resultados.map((a) => (
                <li key={a.id}>
                  <button
                    type="button"
                    disabled={criando}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
                    onClick={() => void iniciarConversa(a.id)}
                  >
                    <span className="font-medium text-slate-900 dark:text-slate-100">{a.nome}</span>
                    <span className="block text-xs text-slate-500">{a.email}</span>
                  </button>
                </li>
              ))}
            </ul>
            <div className="mt-4 flex justify-end">
              <Button type="button" variant="secondary" onClick={() => setModalAberto(false)}>
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
