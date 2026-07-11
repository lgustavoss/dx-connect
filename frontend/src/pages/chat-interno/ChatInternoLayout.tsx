import { Outlet, useMatch } from 'react-router-dom'
import { ChatInternoProvider } from '../../contexts/ChatInternoContext'
import { ChatInternoSidebar } from '../../components/chat-interno/ChatInternoSidebar'

function ChatInternoShell() {
  const matchConversa = useMatch('/chat-interno/:conversaId')
  const emThread = Boolean(matchConversa?.params.conversaId)
  const matchSetor = useMatch('/chat-interno/setor/:setorId')
  const emSetorRedirect = Boolean(matchSetor)

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-slate-50 dark:bg-slate-950">
      <div className="flex min-h-0 flex-1">
        <ChatInternoSidebar
          className={`shrink-0 md:w-72 lg:w-80 ${
            emThread || emSetorRedirect ? 'hidden md:flex' : 'flex w-full'
          }`}
        />

        <main
          className={`min-h-0 min-w-0 flex-1 flex-col border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950 md:border-l ${
            emThread || emSetorRedirect ? 'flex' : 'hidden md:flex'
          }`}
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export function ChatInternoLayout() {
  return (
    <ChatInternoProvider>
      <ChatInternoShell />
    </ChatInternoProvider>
  )
}
