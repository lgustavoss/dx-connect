import { useCallback, useEffect, useState } from 'react'
import { isMarketingHost } from '../lib/marketingHost'
import { isSaasControlPlaneFrontend } from '../lib/saasControlPlane'
import { isIosSafari, isStandaloneDisplay } from '../lib/pwaDisplay'
import { Button } from './ui/Button'

const LS_DISMISS = 'deskrudder-pwa-install-dismissed'

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

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
    /* ignore */
  }
}

type Props = {
  enabled: boolean
}

/**
 * Convite para instalar o painel na tela inicial (PWA, #691).
 * Chrome/Edge: `beforeinstallprompt`. iOS Safari: instrução Partilhar → Adicionar.
 */
export function PwaInstallBanner({ enabled }: Props) {
  const [dismissed, setDismissed] = useState(readDismissed)
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!enabled) return
    const onPrompt = (e: Event) => {
      e.preventDefault()
      setDeferred(e as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', onPrompt)
    return () => window.removeEventListener('beforeinstallprompt', onPrompt)
  }, [enabled])

  const agoraNao = useCallback(() => {
    writeDismissed()
    setDismissed(true)
  }, [])

  const instalar = useCallback(async () => {
    if (!deferred) return
    setBusy(true)
    try {
      await deferred.prompt()
      await deferred.userChoice
      writeDismissed()
      setDismissed(true)
      setDeferred(null)
    } finally {
      setBusy(false)
    }
  }, [deferred])

  if (!enabled || dismissed) return null
  if (typeof window === 'undefined') return null
  if (isStandaloneDisplay()) return null
  if (isMarketingHost() || isSaasControlPlaneFrontend()) return null

  const ios = isIosSafari()
  if (!deferred && !ios) return null

  return (
    <div
      role="region"
      aria-label="Adicionar à tela inicial"
      className="flex shrink-0 flex-col gap-2 border-b border-teal-200 bg-teal-50 px-4 py-3 text-sm text-slate-800 dark:border-teal-900/40 dark:bg-teal-950/30 dark:text-slate-100 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="min-w-0 space-y-0.5">
        <p className="font-semibold text-slate-900 dark:text-white">Adicionar à tela inicial</p>
        <p className="text-xs text-slate-600 dark:text-slate-300 sm:text-sm">
          {ios
            ? 'No Safari, toque em Partilhar e depois em Adicionar ao Ecrã Início — o DeskRudder abre como app neste endereço.'
            : 'Instale o DeskRudder neste telemóvel para abrir o painel sem a barra do browser.'}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Button type="button" variant="ghost" className="h-9 px-3" onClick={agoraNao} disabled={busy}>
          Agora não
        </Button>
        {deferred ? (
          <Button type="button" variant="primary" className="h-9 px-4" loading={busy} onClick={() => void instalar()}>
            Instalar
          </Button>
        ) : null}
      </div>
    </div>
  )
}
