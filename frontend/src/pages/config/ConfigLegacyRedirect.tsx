import { Navigate, useLocation } from 'react-router-dom'
import { CONFIG_LEGACY_REDIRECTS } from './configNav'

/** Mantém bookmarks e links antigos a funcionar (#833, #865). */
export function ConfigLegacyRedirect() {
  const { pathname } = useLocation()
  const exact = CONFIG_LEGACY_REDIRECTS.find((r) => r.from === pathname)
  if (exact) return <Navigate to={exact.to} replace />

  const prefixRules: Array<[string, string]> = [
    ['/configuracoes/sistema/email', '/configuracoes/canais/email'],
    ['/configuracoes/sistema/whatsapp', '/configuracoes/canais/whatsapp'],
    ['/configuracoes/sistema/base-conhecimento', '/configuracoes/canais/base-conhecimento'],
    ['/configuracoes/sistema/auditoria', '/configuracoes/administracao/auditoria'],
    ['/configuracoes/sistema', '/configuracoes/empresa'],
    ['/configuracoes/cadastros/custos', '/configuracoes/comercial/custos'],
    ['/configuracoes/cadastros/funil-crm', '/configuracoes/comercial/funil-crm'],
    ['/configuracoes/cadastros/propostas', '/configuracoes/comercial/propostas'],
    ['/configuracoes/cadastros/contratos', '/configuracoes/comercial/contratos'],
    ['/configuracoes/cadastros/implantacao', '/configuracoes/comercial/implantacao'],
    ['/configuracoes/cadastros/tipos-negocio', '/configuracoes/comercial/tipos-negocio'],
    ['/configuracoes/cadastros/pdv', '/configuracoes/postos-pdv/pdv'],
    ['/configuracoes/cadastros', '/configuracoes'],
    ['/configuracoes/empresa-catalogos/tipos-negocio', '/configuracoes/comercial/tipos-negocio'],
    ['/configuracoes/empresa-catalogos/pdv', '/configuracoes/postos-pdv/pdv'],
    ['/configuracoes/empresa-catalogos', '/configuracoes/empresa'],
    ['/configuracoes/equipa/status-ticket', '/configuracoes/tickets/status-ticket'],
    ['/configuracoes/equipa/natureza-motivo', '/configuracoes/tickets/natureza-motivo'],
    ['/configuracoes/equipa/respostas-prontas', '/configuracoes/tickets/respostas-prontas'],
    ['/configuracoes/equipa/roteamento', '/configuracoes/tickets/roteamento'],
    ['/configuracoes/equipa/sla', '/configuracoes/tickets/sla'],
    ['/configuracoes/equipa', '/configuracoes/equipe'],
    ['/configuracoes/atendimento/status-ticket', '/configuracoes/tickets/status-ticket'],
    ['/configuracoes/atendimento/natureza-motivo', '/configuracoes/tickets/natureza-motivo'],
    ['/configuracoes/atendimento/respostas-prontas', '/configuracoes/tickets/respostas-prontas'],
    ['/configuracoes/atendimento/roteamento', '/configuracoes/tickets/roteamento'],
    ['/configuracoes/atendimento/sla', '/configuracoes/tickets/sla'],
    ['/configuracoes/atendimento', '/configuracoes/equipe'],
  ]
  for (const [from, to] of prefixRules) {
    if (pathname === from || pathname.startsWith(`${from}/`)) {
      return <Navigate to={pathname.replace(from, to)} replace />
    }
  }
  return <Navigate to="/configuracoes" replace />
}
