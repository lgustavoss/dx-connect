import type { ReactNode } from 'react'
import { WhatsappConversa } from '../whatsapp/WhatsappConversa'
import { ChatInternoThread } from '../chat-interno/ChatInternoThread'
import { useChatHub } from '../../contexts/ChatHubContext'
import { PortalConversa } from './PortalConversa'

type Props = {
  placeholder: ReactNode
}

/** Painel direito do hub: conversa ativa via estado, sem id na URL (#654). */
export function ChatHubPainel({ placeholder }: Props) {
  const { chatAtivo } = useChatHub()
  if (chatAtivo?.canal === 'whatsapp') {
    return <WhatsappConversa chatIdProp={chatAtivo.id} />
  }
  if (chatAtivo?.canal === 'portal') {
    return <PortalConversa chatIdProp={chatAtivo.id} />
  }
  if (chatAtivo?.canal === 'interno') {
    return <ChatInternoThread conversaIdProp={chatAtivo.id} />
  }
  return <>{placeholder}</>
}
