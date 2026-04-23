import { useEffect, useState } from 'react'
import { whatsappService } from '../Services/WhatsappService'
import { type WhatsappChats } from '../api/client'

const PAGE = 30

export function useWhatsappHistorico() {
  const [items, setItems] = useState<WhatsappChats.Chat[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)

  async function load(from: number) {
    setLoading(true)
    try {
      const { items, total } = await whatsappService.getHistorico({
        offset: from,
        limit: PAGE
      })
      setItems(items)
      setTotal(total)
      setOffset(from)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load(0)
  }, [])

  return {
    items,
    total,
    offset,
    loading,
    load,
    PAGE
  }
}