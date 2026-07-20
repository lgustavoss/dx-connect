import { portalCliente } from '../../api/client'
import { usePortalBranding } from '../../contexts/PortalBrandingContext'

type Props = {
  className?: string
}

export function PortalBrandLogo({ className = 'h-10 w-auto max-w-[12rem] object-contain' }: Props) {
  const branding = usePortalBranding()

  if (branding.logo_url) {
    return (
      <img
        src={portalCliente.logoAssetUrl()}
        alt={branding.nome_exibicao}
        className={className}
      />
    )
  }

  return (
    <span
      className="block truncate text-lg font-semibold tracking-tight"
      style={{ color: branding.cor_header }}
    >
      {branding.nome_exibicao}
    </span>
  )
}
