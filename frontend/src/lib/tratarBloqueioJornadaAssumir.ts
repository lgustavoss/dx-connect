import { ApiError, ponto } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'

type ToastLike = {
  showError: (msg: string) => void
  showSuccess?: (msg: string) => void
  showWarning?: (msg: string) => void
}

/** Trata 403 de jornada/HE ao assumir WhatsApp; opcionalmente solicita HE. */
export async function tratarBloqueioJornadaAoAssumir(
  err: unknown,
  toast: ToastLike,
): Promise<boolean> {
  if (!(err instanceof ApiError) || err.status !== 403) return false
  const detail = String((err.body as { detail?: string } | null)?.detail ?? err.message ?? '')
  const isJornada =
    /jornada/i.test(detail) || /hora extra/i.test(detail) || /pegar novos chats/i.test(detail)
  if (!isJornada) return false
  toast.showError(detail || 'Sua jornada terminou. Peça hora extra a um administrador.')
  try {
    await ponto.solicitarHoraExtra({ motivo: 'Pedido ao tentar atender WhatsApp após a jornada.' })
    toast.showSuccess?.('Pedido de hora extra enviado aos administradores.')
  } catch (e2) {
    // Pedido pode já existir — só avisa.
    if (!(e2 instanceof ApiError && e2.status === 400)) {
      toast.showWarning?.(mensagemFalhaParaToast(e2, 'Não foi possível registrar o pedido de HE.'))
    }
  }
  return true
}
