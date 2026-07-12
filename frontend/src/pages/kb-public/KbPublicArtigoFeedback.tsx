import { useCallback, useEffect, useState } from 'react'
import { kbPublic } from '../../api/client'
import { useKbPublicBranding } from './KbPublicContext'

const STORAGE_PREFIX = 'kb-feedback:'

function feedbackStorageKey(slug: string) {
  return `${STORAGE_PREFIX}${slug}`
}

function lerVotoLocal(slug: string): boolean | null {
  try {
    const raw = localStorage.getItem(feedbackStorageKey(slug))
    if (raw === '1') return true
    if (raw === '0') return false
  } catch {
    /* storage indisponível */
  }
  return null
}

function salvarVotoLocal(slug: string, util: boolean) {
  try {
    localStorage.setItem(feedbackStorageKey(slug), util ? '1' : '0')
  } catch {
    /* storage indisponível */
  }
}

type Props = {
  slug: string
}

export function KbPublicArtigoFeedback({ slug }: Props) {
  const branding = useKbPublicBranding()
  const [voto, setVoto] = useState<boolean | null>(() => lerVotoLocal(slug))
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    setVoto(lerVotoLocal(slug))
    setErro(null)
  }, [slug])

  const enviar = useCallback(
    async (util: boolean) => {
      if (voto != null || enviando) return
      setEnviando(true)
      setErro(null)
      try {
        const res = await kbPublic.submitArticleFeedback(slug, { util })
        setVoto(res.util)
        salvarVotoLocal(slug, res.util)
      } catch {
        setErro('Não foi possível registrar sua avaliação. Tente novamente em instantes.')
      } finally {
        setEnviando(false)
      }
    },
    [enviando, slug, voto],
  )

  if (!branding.feedback_habilitado) {
    return null
  }

  if (voto != null) {
    return (
      <p className="text-center text-sm opacity-70" role="status">
        Obrigado pelo feedback{voto ? ' — marcou como útil' : ''}.
      </p>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-5 text-center dark:border-slate-700 dark:bg-slate-900/40">
      <p className="text-sm font-medium" style={{ color: branding.cor_texto_corpo }}>
        Este manual foi útil?
      </p>
      <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
        <button
          type="button"
          disabled={enviando}
          onClick={() => void enviar(true)}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-teal-300 hover:text-teal-800 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
          style={{ borderColor: enviando ? undefined : branding.cor_primaria + '55' }}
        >
          Sim
        </button>
        <button
          type="button"
          disabled={enviando}
          onClick={() => void enviar(false)}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-800 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300"
        >
          Não
        </button>
      </div>
      {erro ? <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">{erro}</p> : null}
    </div>
  )
}
