import { useCallback, useEffect, useState } from 'react'
import {
  ativarAlertasEmSegundoPlano,
  getNotificationPermission,
  type AlertasDesktopResultado,
} from '../hooks/useAlertaFilaSemResponsavel'
import { isCapacitorNative } from '../lib/capacitorNative'
import { Button } from './ui/Button'

const LS_DISMISS = 'dxconnect.notificacoes.desktop_prompt_dismissed'

function readDismissed(): boolean {
  try {
    return localStorage.getItem(LS_DISMISS) === '1'
  } catch {
    return false
  }
}

function writeDismissed() {
  try {
    localStorage.setItem(LS_DISMISS, '1')
  } catch {
    // ignore
  }
}

type Props = {
  enabled: boolean
}

/**
 * Pede permissão de notificações do SO para alertar fila com aba/app em 2º plano (#652).
 * O clique em «Ativar» é o gesto que desbloqueia áudio + permission prompt (browser e APK).
 */
export function AlertaDesktopPermissaoBanner({ enabled }: Props) {
  const nativo = isCapacitorNative()
  const [perm, setPerm] = useState<AlertasDesktopResultado>(() => getNotificationPermission())
  const [dismissed, setDismissed] = useState(readDismissed)
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState<'ok' | 'denied' | null>(null)

  useEffect(() => {
    if (!enabled) return
    setPerm(getNotificationPermission())
  }, [enabled])

  const ativar = useCallback(async () => {
    setBusy(true)
    setFeedback(null)
    try {
      const result = await ativarAlertasEmSegundoPlano()
      setPerm(result)
      if (result === 'granted') {
        setFeedback('ok')
        writeDismissed()
        setDismissed(true)
        window.setTimeout(() => setFeedback(null), 5000)
      } else if (result === 'denied') {
        setFeedback('denied')
      }
    } finally {
      setBusy(false)
    }
  }, [])

  const agoraNao = useCallback(() => {
    writeDismissed()
    setDismissed(true)
  }, [])

  if (!enabled) return null
  // No APK a permissão nativa pode estar em default mesmo com Notification.permission diferente
  if (!nativo && perm === 'unsupported') return null
  if (perm === 'granted' && feedback !== 'ok') return null
  if (dismissed && feedback !== 'ok' && feedback !== 'denied') return null
  if (perm === 'denied' && feedback !== 'denied') return null
  if (perm === 'granted' && feedback === 'ok') {
    return (
      <div
        role="status"
        className="shrink-0 border-b border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100"
      >
        {nativo
          ? 'Alertas do sistema ativos — você será avisado com o app em segundo plano ou fechado.'
          : 'Alertas do sistema ativos — você será avisado com a aba em segundo plano, navegador minimizado ou app fechada.'}
      </div>
    )
  }

  if (feedback === 'denied' || perm === 'denied') {
    return (
      <div
        role="status"
        className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-950 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100"
      >
        <p className="min-w-0 flex-1">
          {nativo
            ? 'Notificações bloqueadas neste aparelho. Permita notificações nas configurações do app para receber alertas com o DeskRudder em segundo plano.'
            : 'Notificações bloqueadas neste navegador. Para receber alertas com a aba em segundo plano, permita notificações nas configurações do site.'}
        </p>
        <Button type="button" variant="ghost" className="h-8 shrink-0 px-2 text-xs" onClick={agoraNao}>
          Fechar
        </Button>
      </div>
    )
  }

  return (
    <div
      role="region"
      aria-label="Ativar alertas em segundo plano"
      className="flex shrink-0 flex-col gap-2 border-b border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-slate-800 dark:border-cyan-900/40 dark:bg-cyan-950/30 dark:text-slate-100 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="min-w-0 space-y-0.5">
        <p className="font-semibold text-slate-900 dark:text-white">
          {nativo ? 'Ativar alertas com o app em segundo plano ou fechado?' : 'Ativar alertas fora desta aba?'}
        </p>
        <p className="text-xs text-slate-600 dark:text-slate-300 sm:text-sm">
          {nativo
            ? 'Com a permissão do Android, o DeskRudder avisa a fila mesmo com o app minimizado ou fechado (push).'
            : 'Com a permissão do navegador, o DeskRudder avisa a fila mesmo com outra aba, navegador minimizado ou app fechada (PWA).'}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Button type="button" variant="ghost" className="h-9 px-3" onClick={agoraNao} disabled={busy}>
          Agora não
        </Button>
        <Button type="button" variant="primary" className="h-9 px-4" loading={busy} onClick={() => void ativar()}>
          Ativar alertas
        </Button>
      </div>
    </div>
  )
}
