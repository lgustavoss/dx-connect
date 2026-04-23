import { useCallback, useEffect, useState } from 'react'
import { type WhatsappChats } from '../api/client'

export function useWhatsappChat(chatId: number) {
  const [chat, setChat] = useState<WhatsappChats.Chat | null>(null)
  const [mensagens, setMensagens] = useState<WhatsappChats.Mensagem[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!chatId) return
    const [c, m] = await Promise.all([
      whatsappService.getChat(chatId),
      whatsappService.getMensagens(chatId)
    ])
    setChat(c)
    setMensagens(m)
  }, [chatId])

  useEffect(() => {
    setLoading(true)
    load().finally(() => setLoading(false))
  }, [load])

  return {
    chat,
    mensagens,
    loading,
    reload: load,

    // ações (já prontas pra próxima etapa)
    enviar: (texto: string) => whatsappService.enviar(chatId, texto),
    encerrar: () => whatsappService.encerrar(chatId),
    assumir: () => whatsappService.assumir(chatId),
    marcarVisto: () => whatsappService.marcarVisto(chatId),
  }
}