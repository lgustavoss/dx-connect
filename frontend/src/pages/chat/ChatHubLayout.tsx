import { Outlet, useLocation } from 'react-router-dom'
import { ChatHubTabs } from '../../components/chat/ChatHubTabs'
import { ChatHubSearch } from '../../components/chat/ChatHubSearch'
import { ChatInternoLista } from '../../components/chat-interno/ChatInternoLista'
import { useChatHub } from '../../contexts/ChatHubContext'
import { chatHubModoDePath } from '../../lib/chatHubPaths'
import { ChatListaAtendendo } from './ChatListaAtendendo'
import { ChatListaEspera } from './ChatListaEspera'
import { ChatListaContatos } from './ChatListaContatos'

function ChatHubLista() {
  const { pathname, search } = useLocation()
  const modo = chatHubModoDePath(pathname, search)

  switch (modo) {
    case 'espera':
      return <ChatListaEspera />
    case 'interno':
      return <ChatInternoLista />
    case 'contatos':
      return <ChatListaContatos />
    default:
      return <ChatListaAtendendo />
  }
}

export function ChatHubLayout() {
  const { pathname, search } = useLocation()
  const { chatAtivo } = useChatHub()
  const modo = chatHubModoDePath(pathname, search)
  /** Conversa aberta vem do estado, não da URL (#654). */
  const emConversa = Boolean(chatAtivo) || /\/chat\/interno\/setor\/\d+/.test(pathname)

  return (
    <div className="flex h-full min-h-0 w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
      <aside
        className={`flex h-full min-h-0 shrink-0 flex-col border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950 md:w-72 lg:w-80 md:border-r ${
          emConversa ? 'hidden w-full md:flex' : 'flex w-full'
        }`}
      >
        <ChatHubTabs />
        <ChatHubSearch
          placeholder={
            modo === 'contatos'
              ? 'Buscar contacto, empresa ou telefone'
              : 'Pesquise por conversas'
          }
        />
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <ChatHubLista />
        </div>
      </aside>

      {/* #747: `flex` só quando o painel deve aparecer — senão `hidden` perde para `flex` no CSS. */}
      <main
        className={`h-full min-h-0 min-w-0 flex-1 flex-col bg-slate-50 dark:bg-slate-950 ${
          emConversa ? 'flex' : 'hidden md:flex'
        }`}
      >
        <Outlet />
      </main>
    </div>
  )
}
