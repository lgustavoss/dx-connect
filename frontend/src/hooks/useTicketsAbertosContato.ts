import { useCallback, useEffect, useState } from 'react'
import { tickets } from '../api/client'

/** Contagem de tickets abertos do contato (API #1012). */
export function useTicketsAbertosContato(funcionarioRedeId: number | null | undefined) {
  const [total, setTotal] = useState<number | null>(null)
  const [reloadSeq, setReloadSeq] = useState(0)

  const reload = useCallback(() => {
    setReloadSeq((n) => n + 1)
  }, [])

  useEffect(() => {
    if (funcionarioRedeId == null) {
      setTotal(null)
      return
    }
    let cancelled = false
    tickets
      .list({ funcionario_rede_id: funcionarioRedeId, situacao: 'abertos', limit: 1 })
      .then(({ total: t }) => {
        if (!cancelled) setTotal(t)
      })
      .catch(() => {
        if (!cancelled) setTotal(null)
      })
    return () => {
      cancelled = true
    }
  }, [funcionarioRedeId, reloadSeq])

  return { total, reload }
}
