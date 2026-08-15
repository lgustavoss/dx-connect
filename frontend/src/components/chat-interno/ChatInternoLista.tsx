import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../ui/Button'
import { useChatHub } from '../../contexts/ChatHubContext'
import { useChatInterno } from '../../contexts/ChatInternoContext'
import { formatarHoraRelativa, previewTexto } from '../../lib/chatInternoUtils'
import { CHAT_HUB_PATHS, chatAtivoIgual } from '../../lib/chatHubPaths'
import { ChatInternoNovaConversaModal } from './ChatInternoNovaConversaModal'
import { CHAT_INTERNO_FILTRO_VAZIO, ChatInternoFiltroTipo } from './ChatInternoFiltroTipo'

export function ChatInternoLista() {
  const { filtradas, filtro, loading, erro, carregar } = useChatInterno()
  const { busca, chatAtivo, abrirChat } = useChatHub()
  const [modalAberto, setModalAberto] = useState(false)

  const lista = useMemo(() => {
    const q = busca.trim().toLowerCase()
    if (!q) return filtradas
    return filtradas.filter((c) => {
      const titulo = c.titulo.toLowerCase()
      const preview = (c.ultima_mensagem_corpo || '').toLowerCase()
      return titulo.includes(q) || preview.includes(q)
    })
  }, [filtradas, busca])

  return (
    <>
      <div className="shrink-0 border-b border-slate-200 px-3 py-2.5 dark:border-slate-800">
        <div className="mb-2.5 flex items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Chat da equipe
          </p>
          <Button type="button" className="px-2 py-1 text-xs" onClick={() => setModalAberto(true)}>
            + Nova
          </Button>
        </div>
        <ChatInternoFiltroTipo />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <p className="p-4 text-center text-sm text-slate-400 animate-pulse">Carregando…</p>
        ) : erro && lista.length === 0 ? (
          <div className="p-4 text-center">
            <p className="text-sm text-rose-600 dark:text-rose-400">Erro ao carregar.</p>
            <Button type="button" variant="secondary" className="mt-3 text-xs" onClick={() => void carregar()}>
              Tentar novamente
            </Button>
          </div>
        ) : lista.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-400">{CHAT_INTERNO_FILTRO_VAZIO[filtro]}</p>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {lista.map((c) => {
              const ativa = chatAtivoIgual(chatAtivo, 'interno', c.id)
              return (
                <li key={c.id}>
                  <Link
                    to={CHAT_HUB_PATHS.interno}
                    onClick={() => abrirChat('interno', c.id)}
                    className={`flex gap-3 px-3 py-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-900/50 ${
                      ativa ? 'bg-cyan-50/80 dark:bg-cyan-950/30' : ''
                    }`}
                  >
                    <div
                      className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${
                        c.tipo === 'setor'
                          ? 'bg-amber-500'
                          : c.tipo === 'grupo'
                            ? 'bg-violet-600'
                            : 'bg-cyan-600'
                      }`}
                    >
                      {c.tipo === 'setor' ? 'S' : c.tipo === 'grupo' ? 'G' : c.titulo.slice(0, 1).toUpperCase()}
                      {c.nao_lidas_count > 0 && (
                        <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-cyan-600 ring-2 ring-white dark:ring-slate-950" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <p
                          className={`truncate text-sm ${
                            c.nao_lidas_count > 0 ? 'font-bold text-slate-900 dark:text-white' : 'font-medium text-slate-800 dark:text-slate-200'
                          }`}
                        >
                          {c.titulo}
                          {c.silenciado ? (
                            <span className="ml-1.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">
                              silenciado
                            </span>
                          ) : null}
                        </p>
                        <span className="shrink-0 text-[10px] text-slate-400">
                          {formatarHoraRelativa(c.ultima_mensagem_em)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <p
                          className={`min-w-0 flex-1 truncate text-xs ${
                            c.nao_lidas_count > 0 ? 'font-medium text-slate-700 dark:text-slate-300' : 'text-slate-500'
                          }`}
                        >
                          {previewTexto(c.ultima_mensagem_corpo, 48)}
                        </p>
                        {c.nao_lidas_count > 0 && (
                          <span className="shrink-0 rounded-full bg-cyan-600 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                            {c.nao_lidas_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <ChatInternoNovaConversaModal open={modalAberto} onClose={() => setModalAberto(false)} />
    </>
  )
}
