import { ApiError } from '../api/client'

type ToastLike = {
  showError: (msg: string) => void
  showSuccess?: (msg: string) => void
  showWarning?: (msg: string) => void
}

/** Trata 403 de jornada ao assumir WhatsApp (#1135 — sem pedido de HE). */
export async function tratarBloqueioJornadaAoAssumir(
  err: unknown,
  toast: ToastLike,
): Promise<boolean> {
  if (!(err instanceof ApiError) || err.status !== 403) return false
  const detail = String((err.body as { detail?: string } | null)?.detail ?? err.message ?? '')
  const isJornada =
    /jornada/i.test(detail) ||
    /ponto em aberto/i.test(detail) ||
    /pegar novos chats/i.test(detail) ||
    /hora extra/i.test(detail)
  if (!isJornada) return false
  toast.showError(
    detail ||
      'Sua jornada prevista terminou. Mantenha o ponto em aberto para pegar chats no WhatsApp.',
  )
  return true
}
