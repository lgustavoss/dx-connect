import type { ReactNode } from 'react'
import { PortalBrandingProvider } from '../../contexts/PortalBrandingContext'

export function PortalBrandingRoot({ children }: { children: ReactNode }) {
  return <PortalBrandingProvider>{children}</PortalBrandingProvider>
}
