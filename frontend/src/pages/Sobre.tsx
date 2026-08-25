import { useEffect, useState } from 'react'
import { system, type System } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { APP_DESCRIPTION, APP_NAME } from '../brand'
import { ReleaseNotesView } from '../components/release/ReleaseNotesView'
import { useToast } from '../components/ui/Toast'

/** Página Sobre do DeskRudder — só notas de produto (#674 / #920). */
export function Sobre() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [info, setInfo] = useState<System.Info | null>(null)
  const [notes, setNotes] = useState<System.ReleaseNotes | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([system.info(), system.releaseNotes()])
      .then(([i, n]) => {
        if (!cancelled) {
          setInfo(i)
          setNotes(n)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar informações da versão.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [toast])

  const versionLabel =
    info?.version_display ??
    notes?.current_version_display ??
    (import.meta.env.VITE_APP_VERSION_DISPLAY as string | undefined) ??
    (import.meta.env.VITE_APP_VERSION as string | undefined) ??
    null

  return (
    <ReleaseNotesView
      backTo="/"
      title="Sobre"
      brandCaption={APP_DESCRIPTION}
      description={`Consulte a versão em uso e o que mudou nas atualizações do ${APP_NAME} nesta instância (helpdesk). Melhorias de DevOps não aparecem aqui.`}
      versionLabel={versionLabel}
      notes={notes}
      loading={loading}
    />
  )
}
