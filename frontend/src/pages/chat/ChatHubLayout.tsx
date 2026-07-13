import { Outlet, useLocation } from 'react-router-dom'

import { ChatHubTabs } from '../../components/chat/ChatHubTabs'

import { ChatHubSearch } from '../../components/chat/ChatHubSearch'

import { ChatInternoLista } from '../../components/chat-interno/ChatInternoLista'

import { chatHubModoDePath } from '../../lib/chatHubPaths'

import { ChatListaAtendendo } from './ChatListaAtendendo'

import { ChatListaEspera } from './ChatListaEspera'



function ChatHubLista() {

  const { pathname } = useLocation()

  const modo = chatHubModoDePath(pathname)



  switch (modo) {

    case 'espera':

      return <ChatListaEspera />

    case 'interno':

      return <ChatInternoLista />

    default:

      return <ChatListaAtendendo />

  }

}



export function ChatHubLayout() {

  const { pathname } = useLocation()

  const emConversa =

    /\/chat\/c\/\d+/.test(pathname) ||

    /\/chat\/portal\/\d+/.test(pathname) ||

    /\/chat\/interno\/\d+/.test(pathname) ||

    /\/chat\/interno\/setor\/\d+/.test(pathname)



  return (

    <div className="flex h-full min-h-0 w-full overflow-hidden bg-slate-50 dark:bg-slate-950">

      <aside

        className={`flex h-full min-h-0 shrink-0 flex-col border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950 md:w-72 lg:w-80 md:border-r ${

          emConversa ? 'hidden w-full md:flex' : 'flex w-full'

        }`}

      >

        <ChatHubTabs />

        <ChatHubSearch />

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">

          <ChatHubLista />

        </div>

      </aside>



      <main

        className={`flex h-full min-h-0 min-w-0 flex-1 flex-col bg-slate-50 dark:bg-slate-950 ${

          emConversa ? '' : 'hidden md:flex'

        }`}

      >

        <Outlet />

      </main>

    </div>

  )

}

