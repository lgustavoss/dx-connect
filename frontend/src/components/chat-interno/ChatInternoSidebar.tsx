import { useState } from 'react'
import { Link, useMatch } from 'react-router-dom'
import { Button } from '../ui/Button'
import { useChatInterno } from '../../contexts/ChatInternoContext'
import { formatarHoraRelativa, previewTexto } from '../../lib/chatInternoUtils'
import { ChatInternoNovaConversaModal } from './ChatInternoNovaConversaModal'
import { CHAT_INTERNO_FILTRO_VAZIO, ChatInternoFiltroTipo } from './ChatInternoFiltroTipo'

type Props = {
  className?: string
}

export function ChatInternoSidebar({ className = '' }: Props) {
  const { filtradas, filtro, loading, erro, carregar } = useChatInterno()
  const [modalAberto, setModalAberto] = useState(false)
  const match = useMatch('/chat-interno/:conversaId')
  const conversaAtivaId = match?.params.conversaId ? Number(match.params.conversaId) : null

  const totalNaoLidas = filtradas.reduce((acc, c) => acc + c.nao_lidas_count, 0)

  return (
    <aside
      className={`flex h-full min-h-0 flex-col border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950 ${className}`}
    >
      <div className="shrink-0 border-b border-slate-200 p-3 dark:border-slate-800 md:p-4">
        <div className="mb-3 hidden items-center gap-2 md:flex">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-600 text-white">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M17 8h1a4 4 0 0 1 0 8h-1" />
              <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
            </svg>
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-bold text-slate-900 dark:text-white">Chat interno</h1>
            <p className="truncate text-[11px] text-slate-500">Equipe e comunicados por setor</p>
          </div>
        </div>
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-bold text-slate-900 dark:text-white">Conversas</h2>
            {totalNaoLidas > 0 && (
              <p className="text-[11px] font-medium text-cyan-600 dark:text-cyan-400">
                {totalNaoLidas} não {totalNaoLidas === 1 ? 'lida' : 'lidas'}
              </p>
            )}
          </div>
          <Button type="button" className="shrink-0 px-2.5 py-1.5 text-xs" onClick={() => setModalAberto(true)}>
            + Nova
          </Button>
        </div>
        <ChatInternoFiltroTipo className="mt-3" />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <p className="p-4 text-center text-sm text-slate-400 animate-pulse">Carregando…</p>
        ) : erro && filtradas.length === 0 ? (
          <div className="p-4 text-center">
            <p className="text-sm text-rose-600 dark:text-rose-400">Erro ao carregar.</p>
            <Button type="button" variant="secondary" className="mt-3 text-xs" onClick={() => void carregar()}>
              Tentar novamente
            </Button>
          </div>
        ) : filtradas.length === 0 ? (
          <p className="p-4 text-center text-sm text-slate-500">
            {CHAT_INTERNO_FILTRO_VAZIO[filtro]}
          </p>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800/80">
            {filtradas.map((c) => {
              const ativa = conversaAtivaId === c.id
              const naoLidas = c.nao_lidas_count > 0
              return (
                <li key={c.id}>
                  <Link
                    to={`/chat-interno/${c.id}`}
                    className={`flex items-center gap-3 px-3 py-3 transition-colors ${
                      ativa
                        ? 'bg-cyan-50 dark:bg-cyan-950/40'
                        : naoLidas
                          ? 'bg-cyan-50/40 hover:bg-cyan-50/70 dark:bg-cyan-950/20 dark:hover:bg-cyan-950/30'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-900/60'
                    }`}
                  >
                    <div
                      className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${
                        c.tipo === 'setor' ? 'bg-amber-500' : 'bg-cyan-600'
                      }`}
                    >
                      {c.tipo === 'setor' ? 'S' : c.titulo.slice(0, 1).toUpperCase()}
                      {naoLidas && !ativa && (
                        <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-cyan-600 ring-2 ring-white dark:ring-slate-950" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <p
                          className={`truncate text-sm ${
                            naoLidas ? 'font-bold text-slate-900 dark:text-white' : 'font-semibold text-slate-800 dark:text-slate-100'
                          }`}
                        >
                          {c.titulo}
                        </p>
                        <span className="shrink-0 text-[10px] text-slate-400">
                          {formatarHoraRelativa(c.ultima_mensagem_em)}
                        </span>
                      </div>
                      <div className="mt-0.5 flex items-center gap-2">
                        <p
                          className={`min-w-0 flex-1 truncate text-xs ${
                            naoLidas ? 'font-medium text-slate-700 dark:text-slate-200' : 'text-slate-500'
                          }`}
                        >
                          {previewTexto(c.ultima_mensagem_corpo, 48)}
                        </p>
                        {naoLidas && (
                          <span className="shrink-0 rounded-full bg-cyan-600 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                            {c.nao_lidas_count > 99 ? '99+' : c.nao_lidas_count}
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
    </aside>
  )
}
