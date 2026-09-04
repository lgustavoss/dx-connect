import { useCallback, useState } from 'react'
import {
  reativarAlertaFilaAudio,
  useFilaAguardandoMuted,
  useFilaAudioNeedsGesture,
  usePendenciasResumo,
} from '../hooks/useAlertaFilaSemResponsavel'
import { Button } from './ui/Button'

type Props = {
  enabled: boolean
}

/**
 * App em foco com gente na fila, mas o browser/WebView bloqueou autoplay.
 * Um toque desbloqueia o áudio e retoma o loop — evita precisar recarregar a página.
 */
export function AlertaFilaAudioBanner({ enabled }: Props) {
  const needsGesture = useFilaAudioNeedsGesture()
  const muted = useFilaAguardandoMuted()
  const resumo = usePendenciasResumo(enabled)
  const fila = resumo.wpp_fila_count + resumo.portal_fila_count
  const [busy, setBusy] = useState(false)

  const ativar = useCallback(() => {
    setBusy(true)
    try {
      reativarAlertaFilaAudio()
    } finally {
      window.setTimeout(() => setBusy(false), 400)
    }
  }, [])

  if (!enabled || muted || fila <= 0 || !needsGesture) return null

  return (
    <div
      role="region"
      aria-label="Ativar alerta sonoro da fila"
      className="flex shrink-0 flex-col gap-2 border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-slate-800 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-slate-100 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="min-w-0 space-y-0.5">
        <p className="font-semibold text-slate-900 dark:text-white">Ativar alerta sonoro da fila</p>
        <p className="text-xs text-slate-600 dark:text-slate-300 sm:text-sm">
          Há {fila === 1 ? '1 chat aguardando' : `${fila} chats aguardando`}. O navegador bloqueou o som —
          toque no botão para ouvir o alerta sem recarregar a página.
        </p>
      </div>
      <Button type="button" variant="primary" className="h-9 shrink-0 px-4" loading={busy} onClick={ativar}>
        Ativar som
      </Button>
    </div>
  )
}
