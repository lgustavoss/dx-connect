import { useEffect } from 'react'

import { consumeWhatsappListScroll, type WhatsappListOrigin } from '../lib/whatsappListReturn'

/** Restaura scroll da listagem ao voltar da conversa (#454). */
export function useWhatsappListScrollRestore(
  origin: WhatsappListOrigin,
  returnPath: string,
  ready: boolean,
) {
  useEffect(() => {
    if (!ready) return
    const y = consumeWhatsappListScroll(origin, returnPath)
    if (y == null) return
    requestAnimationFrame(() => window.scrollTo({ top: y, left: 0 }))
  }, [origin, returnPath, ready])
}
