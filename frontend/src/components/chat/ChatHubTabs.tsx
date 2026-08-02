import { Link, useLocation } from 'react-router-dom'
import { useChatInterno } from '../../contexts/ChatInternoContext'
import { useChatHub } from '../../contexts/ChatHubContext'
import { CHAT_HUB_PATHS, chatHubModoDePath } from '../../lib/chatHubPaths'
import { ChatFilaSomToggle } from './ChatFilaSomToggle'

type TabDef = {
  id: keyof typeof CHAT_HUB_PATHS
  to: string
  label: string
  icon: React.ReactNode
  badge?: number
}

export function ChatHubTabs() {
  const { pathname, search } = useLocation()
  const modo = chatHubModoDePath(pathname, search)
  const { filaCount, atendendoCount } = useChatHub()
  const { conversas } = useChatInterno()
  const internoNaoLidas = conversas.reduce((acc, c) => acc + c.nao_lidas_count, 0)

  const tabs: TabDef[] = [
    {
      id: 'atendendo',
      to: CHAT_HUB_PATHS.atendendo,
      label: 'Atendendo',
      badge: atendendoCount,
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      ),
    },
    {
      id: 'espera',
      to: CHAT_HUB_PATHS.espera,
      label: 'Aguardando',
      badge: filaCount,
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
      ),
    },
    {
      id: 'contatos',
      to: CHAT_HUB_PATHS.contatos,
      label: 'Contatos',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      ),
    },
    {
      id: 'interno',
      to: CHAT_HUB_PATHS.interno,
      label: 'Interno',
      badge: internoNaoLidas,
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <rect width="18" height="11" x="3" y="11" rx="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      ),
    },
  ]

  return (
    <nav className="flex shrink-0 border-b border-slate-200 dark:border-slate-800" aria-label="Modos de chat">
      {tabs.map((tab) => {
        const ativo = modo === tab.id
        const tabClass = `relative flex flex-1 flex-col items-center gap-1 border-b-2 px-0.5 py-2.5 text-[10px] font-semibold transition-colors ${
          ativo
            ? 'border-cyan-500 text-cyan-600 dark:text-cyan-400'
            : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
        }`

        if (tab.id === 'espera') {
          return (
            <div key={tab.id} className="relative flex flex-1 items-stretch">
              <Link to={tab.to} title={tab.label} className={tabClass}>
                <span className={ativo ? 'text-cyan-600 dark:text-cyan-400' : ''}>{tab.icon}</span>
                <span className="hidden sm:inline">{tab.label}</span>
                {tab.badge != null && tab.badge > 0 && (
                  <span className="absolute right-5 top-1 min-w-[1rem] rounded-full bg-cyan-600 px-1 text-center text-[9px] font-bold leading-4 text-white sm:right-6">
                    {tab.badge > 99 ? '99+' : tab.badge}
                  </span>
                )}
              </Link>
              <div className="absolute right-0 top-1/2 z-10 -translate-y-1/2 pr-0.5">
                <ChatFilaSomToggle />
              </div>
            </div>
          )
        }

        return (
          <Link key={tab.id} to={tab.to} title={tab.label} className={tabClass}>
            <span className={ativo ? 'text-cyan-600 dark:text-cyan-400' : ''}>{tab.icon}</span>
            <span className="hidden sm:inline">{tab.label}</span>
            {tab.badge != null && tab.badge > 0 && (
              <span className="absolute right-0.5 top-1 min-w-[1rem] rounded-full bg-cyan-600 px-1 text-center text-[9px] font-bold leading-4 text-white">
                {tab.badge > 99 ? '99+' : tab.badge}
              </span>
            )}
          </Link>
        )
      })}
    </nav>
  )
}
