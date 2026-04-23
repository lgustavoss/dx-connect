import { useCallback, useEffect, useState } from 'react'
import { type WhatsappChats } from '../api/client'
import { whatsappService } from '../Services/WhatsappService'

export function useWhatsappAtendendo() {
  const [fila, setFila] = useState<WhatsappChats.Chat[]>([])
  const [meus, setMeus] = useState<WhatsappChats.Chat[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [f, m] = await Promise.all([
        whatsappService.getFila(),
        whatsappService.getMeus()
      ])
      setFila(f)
      setMeus(m)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return {
    fila,
    meus,
    loading,
    reload: load
  }
}