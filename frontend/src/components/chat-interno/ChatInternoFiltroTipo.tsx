import { useMemo } from 'react'
import { useChatInterno } from '../../contexts/ChatInternoContext'
import type { FiltroInboxChatInterno } from '../../lib/chatInternoUtils'

type FiltroDef = {
  id: FiltroInboxChatInterno
  label: string
  titulo: string
  icon: React.ReactNode
}

const FILTROS: FiltroDef[] = [
  {
    id: 'todas',
    label: 'Todas',
    titulo: 'Todas as conversas',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    id: 'direta',
    label: 'Diretas',
    titulo: 'Conversas 1:1 com colegas',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  {
    id: 'grupo',
    label: 'Grupos',
    titulo: 'Grupos personalizados da equipe',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    id: 'setor',
    label: 'Setores',
    titulo: 'Canais de comunicado por setor',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="m3 11 18-5v12L3 13v-2z" />
        <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
      </svg>
    ),
  },
]

function contagemPorTipo(conversas: { tipo: string; nao_lidas_count: number }[]) {
  const diretas = conversas.filter((c) => c.tipo === 'direta')
  const grupos = conversas.filter((c) => c.tipo === 'grupo')
  const setores = conversas.filter((c) => c.tipo === 'setor')
  return {
    todas: conversas.length,
    direta: diretas.length,
    grupo: grupos.length,
    setor: setores.length,
    naoLidasTodas: conversas.reduce((acc, c) => acc + c.nao_lidas_count, 0),
    naoLidasDireta: diretas.reduce((acc, c) => acc + c.nao_lidas_count, 0),
    naoLidasGrupo: grupos.reduce((acc, c) => acc + c.nao_lidas_count, 0),
    naoLidasSetor: setores.reduce((acc, c) => acc + c.nao_lidas_count, 0),
  }
}

type Props = {
  className?: string
}

export function ChatInternoFiltroTipo({ className = '' }: Props) {
  const { conversas, filtro, setFiltro } = useChatInterno()

  const stats = useMemo(() => contagemPorTipo(conversas), [conversas])

  const naoLidasDe = (id: FiltroInboxChatInterno) => {
    if (id === 'direta') return stats.naoLidasDireta
    if (id === 'grupo') return stats.naoLidasGrupo
    if (id === 'setor') return stats.naoLidasSetor
    return stats.naoLidasTodas
  }

  const totalDe = (id: FiltroInboxChatInterno) => {
    if (id === 'direta') return stats.direta
    if (id === 'grupo') return stats.grupo
    if (id === 'setor') return stats.setor
    return stats.todas
  }

  return (
    <nav
      role="tablist"
      aria-label="Filtrar conversas internas"
      className={`grid grid-cols-4 gap-1 rounded-xl border border-slate-200/90 bg-slate-100/80 p-1 dark:border-slate-700/80 dark:bg-slate-900/50 ${className}`}
    >
      {FILTROS.map((f) => {
        const ativo = filtro === f.id
        const total = totalDe(f.id)
        const naoLidas = naoLidasDe(f.id)

        return (
          <button
            key={f.id}
            type="button"
            role="tab"
            aria-selected={ativo}
            title={f.titulo}
            onClick={() => setFiltro(f.id)}
            className={`relative flex min-h-[52px] flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-2 transition-all touch-manipulation ${
              ativo
                ? 'bg-white text-cyan-700 shadow-sm ring-1 ring-cyan-200/70 dark:bg-slate-800 dark:text-cyan-300 dark:ring-cyan-700/40'
                : 'text-slate-500 hover:bg-white/70 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800/60 dark:hover:text-slate-200'
            }`}
          >
            <span className={ativo ? 'text-cyan-600 dark:text-cyan-400' : 'opacity-80'}>{f.icon}</span>
            <span className="text-[10px] font-bold leading-none tracking-tight">{f.label}</span>
            {total > 0 ? (
              <span
                className={`mt-0.5 inline-flex min-w-[1.125rem] items-center justify-center rounded-full px-1 text-[9px] font-bold tabular-nums leading-4 ${
                  ativo
                    ? naoLidas > 0
                      ? 'bg-cyan-600 text-white'
                      : 'bg-cyan-100 text-cyan-700 dark:bg-cyan-950/60 dark:text-cyan-300'
                    : naoLidas > 0
                      ? 'bg-cyan-600/90 text-white'
                      : 'bg-slate-200/90 text-slate-500 dark:bg-slate-700 dark:text-slate-400'
                }`}
              >
                {naoLidas > 0 ? (naoLidas > 99 ? '99+' : naoLidas) : total}
              </span>
            ) : (
              <span className="mt-0.5 text-[9px] font-medium text-slate-400 dark:text-slate-500">0</span>
            )}
          </button>
        )
      })}
    </nav>
  )
}

export const CHAT_INTERNO_FILTRO_VAZIO: Record<FiltroInboxChatInterno, string> = {
  todas: 'Nenhuma conversa ainda.',
  direta: 'Nenhuma conversa direta.',
  grupo: 'Nenhum grupo criado.',
  setor: 'Nenhum canal de setor.',
}
