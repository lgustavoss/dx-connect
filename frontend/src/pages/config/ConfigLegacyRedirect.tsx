import { Navigate, useLocation } from 'react-router-dom'
import { CONFIG_LEGACY_REDIRECTS } from './configNav'

/** Mantém bookmarks e links antigos a funcionar (#833). */
export function ConfigLegacyRedirect() {
  const { pathname } = useLocation()
  const exact = CONFIG_LEGACY_REDIRECTS.find((r) => r.from === pathname)
  if (exact) return <Navigate to={exact.to} replace />

  const prefixRules: Array<[string, string]> = [
    ['/configuracoes/atendimento', '/configuracoes/equipa'],
    ['/configuracoes/sistema/email', '/configuracoes/canais/email'],
    ['/configuracoes/sistema/whatsapp', '/configuracoes/canais/whatsapp'],
    ['/configuracoes/sistema/base-conhecimento', '/configuracoes/canais/base-conhecimento'],
    ['/configuracoes/sistema/auditoria', '/configuracoes/administracao/auditoria'],
    ['/configuracoes/sistema', '/configuracoes/empresa-catalogos'],
    ['/configuracoes/cadastros/custos', '/configuracoes/comercial/custos'],
    ['/configuracoes/cadastros/funil-crm', '/configuracoes/comercial/funil-crm'],
    ['/configuracoes/cadastros/propostas', '/configuracoes/comercial/propostas'],
    ['/configuracoes/cadastros/contratos', '/configuracoes/comercial/contratos'],
    ['/configuracoes/cadastros/implantacao', '/configuracoes/comercial/implantacao'],
    ['/configuracoes/cadastros', '/configuracoes/empresa-catalogos'],
  ]
  for (const [from, to] of prefixRules) {
    if (pathname === from || pathname.startsWith(`${from}/`)) {
      return <Navigate to={pathname.replace(from, to)} replace />
    }
  }
  return <Navigate to="/configuracoes" replace />
}
