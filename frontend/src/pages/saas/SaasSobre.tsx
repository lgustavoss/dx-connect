import { useEffect, useState } from 'react'
import { saasReleaseNotes, system, type System } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ReleaseNotesView } from '../../components/release/ReleaseNotesView'
import { useToast } from '../../components/ui/Toast'
import { SAAS_LICENCAS_PATH } from '../../lib/saasControlPlane'

/** Novidades do control-plane SaaS (#675). */
export function SaasSobre() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [info, setInfo] = useState<System.Info | null>(null)
  const [notes, setNotes] = useState<System.ReleaseNotes | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([system.info(), saasReleaseNotes.get()])
      .then(([i, n]) => {
        if (!cancelled) {
          setInfo(i)
          setNotes(n)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as novidades do SaaS.'))
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
      backTo={SAAS_LICENCAS_PATH}
      backLabel="Voltar às licenças"
      title="Sobre / Novidades"
      brandCaption="Painel admin SaaS — licenças, planos e provisionamento."
      description="Atualizações do control-plane DeskRudder (ops). Notas do helpdesk nas instâncias dos clientes ficam em Sobre no painel de atendimento."
      versionLabel={versionLabel}
      notes={notes}
      loading={loading}
      showBrandLogo
    />
  )
}
