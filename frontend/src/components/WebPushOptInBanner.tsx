import { useCallback, useEffect, useState } from 'react'
import { notificacoes, webPush } from '../api/client'
import { Button } from './ui/Button'
import { syncWebPushSubscription } from '../hooks/useWebPush'
import { webPushRequerPwaIos } from '../lib/pwaDisplay'

const LS_DISMISS = 'deskrudder-web-push-optin-dismissed'

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

type Props = { enabled: boolean }

/** Convite para alertas com a PWA fechada (#694). */
export function WebPushOptInBanner({ enabled }: Props) {
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState<'ok' | 'negado' | 'sem_vapid' | 'ios_pwa' | null>(null)

  const reavaliar = useCallback(async () => {
    if (!enabled || typeof window === 'undefined') {
      setVisible(false)
      return
    }
    if (readDismissed()) {
      setVisible(false)
      return
    }
    if (webPushRequerPwaIos()) {
      setVisible(true)
      setFeedback('ios_pwa')
      return
    }
    if (!('Notification' in window) || !('PushManager' in window)) {
      setVisible(false)
      return
    }
    try {
      const [vapid, prefs] = await Promise.all([webPush.vapid(), notificacoes.preferenciasGet()])
      if (!vapid.configurado || prefs.push_habilitado) {
        setVisible(false)
        return
      }
      if (Notification.permission === 'denied') {
        setVisible(false)
        return
      }
      setVisible(true)
    } catch {
      setVisible(false)
    }
  }, [enabled])

  useEffect(() => {
    void reavaliar()
  }, [reavaliar])

  if (!enabled || feedback === 'ok') {
    if (feedback === 'ok') {
      return (
        <div
          role="status"
          className="shrink-0 border-b border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100"
        >
          Alertas no telemóvel activos — vais ser avisado mesmo com a app fechada.
        </div>
      )
    }
    return null
  }

  if (!visible && feedback !== 'negado' && feedback !== 'sem_vapid' && feedback !== 'ios_pwa') return null

  if (feedback === 'ios_pwa') {
    return (
      <div
        role="status"
        className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-indigo-200 bg-indigo-50 px-4 py-2.5 text-sm text-slate-800 dark:border-indigo-900/40 dark:bg-indigo-950/30 dark:text-slate-100"
      >
        <p className="min-w-0 flex-1">
          No iPhone/iPad, os alertas com a app fechada só funcionam depois de <strong>Adicionar ao Ecrã Início</strong>{' '}
          (Safari 16.4 ou posterior). Abre o atalho e activa os alertas aí.
        </p>
        <Button
          type="button"
          variant="ghost"
          className="h-8 shrink-0 px-2 text-xs"
          onClick={() => {
            writeDismissed()
            setVisible(false)
            setFeedback(null)
          }}
        >
          Entendi
        </Button>
      </div>
    )
  }

  if (feedback === 'negado') {
    return (
      <div
        role="status"
        className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-950 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100"
      >
        <p className="min-w-0 flex-1">
          Notificações bloqueadas neste browser. Permite-as nas definições do site para alertas com a app fechada.
        </p>
        <Button type="button" variant="ghost" className="h-8 shrink-0 px-2 text-xs" onClick={() => setFeedback(null)}>
          Fechar
        </Button>
      </div>
    )
  }

  if (feedback === 'sem_vapid') return null

  return (
    <div
      role="region"
      aria-label="Ativar alertas no telemóvel"
      className="flex shrink-0 flex-col gap-2 border-b border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-slate-800 dark:border-indigo-900/40 dark:bg-indigo-950/30 dark:text-slate-100 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="min-w-0 space-y-0.5">
        <p className="font-semibold text-slate-900 dark:text-white">Alertas com a app fechada?</p>
        <p className="text-xs text-slate-600 dark:text-slate-300 sm:text-sm">
          Recebe avisos da fila e de mensagens nos teus atendimentos mesmo fora do painel. Podes desligar em
          Notificações.
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="ghost"
          className="h-9 px-3"
          disabled={busy}
          onClick={() => {
            writeDismissed()
            setVisible(false)
          }}
        >
          Agora não
        </Button>
        <Button
          type="button"
          variant="primary"
          className="h-9 px-4"
          loading={busy}
          onClick={() => {
            void (async () => {
              setBusy(true)
              try {
                const r = await syncWebPushSubscription({ ativar: true })
                if (r === 'ok') {
                  writeDismissed()
                  setVisible(false)
                  setFeedback('ok')
                  window.setTimeout(() => setFeedback(null), 5000)
                } else if (r === 'negado') {
                  setFeedback('negado')
                } else if (r === 'ios_pwa') {
                  setFeedback('ios_pwa')
                } else {
                  setFeedback('sem_vapid')
                  setVisible(false)
                }
              } finally {
                setBusy(false)
              }
            })()
          }}
        >
          Ativar
        </Button>
      </div>
    </div>
  )
}
