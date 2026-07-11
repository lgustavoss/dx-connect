import { Outlet } from 'react-router-dom'
import { ChatHubProvider } from '../../contexts/ChatHubContext'
import { ChatInternoProvider } from '../../contexts/ChatInternoContext'

export function ChatHubShell() {
  return (
    <ChatHubProvider>
      <ChatInternoProvider>
        <Outlet />
      </ChatInternoProvider>
    </ChatHubProvider>
  )
}
