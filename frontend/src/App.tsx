import { BrowserRouter, Routes, Route, Navigate, Outlet, useParams, useLocation } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { AuthSessao } from './pages/AuthSessao'
import { EsqueciSenha } from './pages/EsqueciSenha'
import { RedefinirSenha } from './pages/RedefinirSenha'
import { AvaliarTicket } from './pages/AvaliarTicket'
import { LandingPage } from './pages/marketing/LandingPage'
import { PrivacidadePage } from './pages/marketing/PrivacidadePage'
import { TrialPage } from './pages/marketing/TrialPage'
import { Dashboard } from './pages/Dashboard'
import { DashboardTickets } from './pages/DashboardTickets'
import { DashboardChats } from './pages/DashboardChats'
import { RelatoriosTickets } from './pages/RelatoriosTickets'
import { RelatoriosChats } from './pages/RelatoriosChats'
import { PresencaOnline } from './pages/PresencaOnline'
import { MeuPonto } from './pages/MeuPonto'
import { PontoEquipe } from './pages/PontoEquipe'
import { Tickets } from './pages/Tickets'
import { TicketNovo } from './pages/TicketNovo'
import { ConfigPropostaTemplates } from './pages/ConfigPropostaTemplates'
import { ConfigContratoTemplates } from './pages/ConfigContratoTemplates'
import { ConfigImplantacaoChecklist } from './pages/ConfigImplantacaoChecklist'
import { CrmLeads } from './pages/CrmLeads'
import { CrmNegociacaoDetalhe } from './pages/CrmNegociacaoDetalhe'
import { CrmContratos } from './pages/CrmContratos'
import { Faturamento } from './pages/Faturamento'
import { ConfigCrmFunil } from './pages/ConfigCrmFunil'
import { Redes } from './pages/Redes'
import { RedeDetalhe } from './pages/RedeDetalhe'
import { RedeForm } from './pages/RedeForm'
import { Empresas } from './pages/Empresas'
import { RustdeskPeers } from './pages/RustdeskPeers'
import { EmpresaForm } from './pages/EmpresaForm'
import { EmpresaDetalhe } from './pages/EmpresaDetalhe'
import { Setores } from './pages/Setores'
import { SetorForm } from './pages/SetorForm'
import { SetorDetalhe } from './pages/SetorDetalhe'
import { Atendentes } from './pages/Atendentes'
import { GruposPermissao } from './pages/GruposPermissao'
import { GrupoPermissaoForm } from './pages/GrupoPermissaoForm'
import { GrupoPermissaoDetalhe } from './pages/GrupoPermissaoDetalhe'
import { temPermissao } from './lib/permissoes'
import { todasPermissoesConfig } from './pages/config/configNav'
import { AtendenteForm } from './pages/AtendenteForm'
import { AtendenteDetalhe } from './pages/AtendenteDetalhe'
import { FuncionariosRede } from './pages/FuncionariosRede'
import { FuncionarioRedeDetalhe } from './pages/FuncionarioRedeDetalhe'
import { FuncionarioRedeForm } from './pages/FuncionarioRedeForm'
import { StatusTicketPage } from './pages/StatusTicket'
import { TicketNaturezaMotivoPage } from './pages/TicketNaturezaMotivo'
import { StatusTicketForm } from './pages/StatusTicketForm'
import { StatusTicketDetalhe } from './pages/StatusTicketDetalhe'
import { RespostasProntasPage } from './pages/RespostasProntas'
import { KbArtigosPage } from './pages/KbArtigos'
import { KbArtigoForm } from './pages/KbArtigoForm'
import { KbConsultaSection } from './pages/KbConsulta'
import { KbPortalSettingsPage } from './pages/KbPortalSettings'
import { AjudaLayout } from './pages/AjudaLayout'
import { KbCategoriasPage } from './pages/KbCategorias'
import { RoteamentoRegrasPage } from './pages/RoteamentoRegras'
import { SlaPoliticasPage } from './pages/SlaPoliticas'
import { SlaCalendariosPage } from './pages/SlaCalendarios'
import { SlaConfigLayout } from './pages/SlaConfigLayout'
import { RespostaProntaForm } from './pages/RespostaProntaForm'
import { RespostaProntaDetalhe } from './pages/RespostaProntaDetalhe'
import { Auditoria } from './pages/Auditoria'
import { TiposNegocio } from './pages/TiposNegocio'
import { TipoNegocioForm } from './pages/TipoNegocioForm'
import { TipoNegocioDetalhe } from './pages/TipoNegocioDetalhe'
import { ConfigWhatsapp } from './pages/ConfigWhatsapp'
import { ConfigPdvCatalogos } from './pages/ConfigPdvCatalogos'
import { ConfigComercialCustos } from './pages/ConfigComercialCustos'
import { ConfigEmpresaEmail } from './pages/ConfigEmpresaEmail'
import { ConfigHubPage } from './pages/config/ConfigHubPage'
import { ConfigDomainIndexRedirect, ConfigDomainLayout } from './pages/config/ConfigDomainLayout'
import { ConfigLegacyRedirect } from './pages/config/ConfigLegacyRedirect'
import { WhatsappLayout } from './pages/whatsapp/WhatsappLayout'
import { WhatsappHistorico } from './pages/whatsapp/WhatsappHistorico'
import { WhatsappConversa } from './pages/whatsapp/WhatsappConversa'
import { WhatsappAvaliacoes } from './pages/whatsapp/WhatsappAvaliacoes'
import { ChatInternoSetorCanal } from './pages/chat-interno/ChatInternoSetorCanal'
import { ChatHubShell } from './pages/chat/ChatHubShell'
import { ChatHubLayout } from './pages/chat/ChatHubLayout'
import { ChatHubPainel } from './pages/chat/ChatHubPainel'
import { ChatHubPlaceholder } from './pages/chat/ChatHubPlaceholder'
import { AlterarSenha } from './pages/AlterarSenha'
import { MinhaConta } from './pages/MinhaConta'
import { NotificacoesPreferencias } from './pages/NotificacoesPreferencias'
import { Sobre } from './pages/Sobre'
import { SolicitacaoMelhoriaNovaPage } from './pages/SolicitacaoMelhoriaNova'
import { MinhasSolicitacoesPage } from './pages/MinhasSolicitacoes'
import { SolicitacoesMelhoriaAdminPage } from './pages/SolicitacoesMelhoriaAdmin'
import { AcessoNegado } from './pages/AcessoNegado'
import { SaasLicencas } from './pages/saas/SaasLicencas'
import { SaasLicencaForm } from './pages/saas/SaasLicencaForm'
import { SaasLicencaDetalhe } from './pages/saas/SaasLicencaDetalhe'
import { SaasPlanos } from './pages/saas/SaasPlanos'
import { SaasPlanoForm } from './pages/saas/SaasPlanoForm'
import { SaasModulos } from './pages/saas/SaasModulos'
import { SaasLeads } from './pages/saas/SaasLeads'
import { SaasLeadDetalhe } from './pages/saas/SaasLeadDetalhe'
import { SaasSolicitacoes } from './pages/saas/SaasSolicitacoes'
import { SaasSolicitacaoDetalhe } from './pages/saas/SaasSolicitacaoDetalhe'
import { SaasLayout } from './pages/saas/SaasLayout'
import { SaasSobre } from './pages/saas/SaasSobre'
import { SaasConta } from './pages/saas/SaasConta'
import { SaasUsuarios } from './pages/saas/SaasUsuarios'
import { SaasUsuarioForm } from './pages/saas/SaasUsuarioForm'
import { SaasSetoresPage } from './pages/saas/SaasSetores'
import { SaasSetorForm } from './pages/saas/SaasSetorForm'
import { SaasAlertas } from './pages/saas/SaasAlertas'
import { KbPublicLayout } from './pages/kb-public/KbPublicLayout'
import { KbPublicHome } from './pages/kb-public/KbPublicHome'
import { KbPublicArtigo } from './pages/kb-public/KbPublicArtigo'
import { PortalBrandingRoot } from './pages/portal/PortalBrandingRoot'
import { PortalLayout } from './pages/portal/PortalLayout'
import { PortalLogin } from './pages/portal/PortalLogin'
import { PortalTrocarSenha } from './pages/portal/PortalTrocarSenha'
import { PortalTickets } from './pages/portal/PortalTickets'
import { PortalTicketNovo } from './pages/portal/PortalTicketNovo'
import { PortalAjudaHome, PortalAjudaArtigo } from './pages/portal/PortalAjuda'
import { PortalChats } from './pages/portal/PortalChats'
import { PortalEquipe } from './pages/portal/PortalEquipe'
import { PortalEquipeForm } from './pages/portal/PortalEquipeForm'
import { ToastProvider } from './components/ui/Toast'
import { ErrorBoundary } from './components/ErrorBoundary'
import { PageLoading } from './components/ui/PageLoading'
import { isMarketingHost } from './lib/marketingHost'
import { isSaasControlPlaneFrontend } from './lib/saasControlPlane'
import { gravarChatAtivoSession, type ChatAtivoCanal } from './lib/chatAtivo'
import { chatHubModoDePath, chatHubPathParaModo } from './lib/chatHubPaths'
import {
  gravarPortalChatAtivoSession,
  gravarPortalTicketAtivoSession,
  PORTAL_CHATS_PATH,
  PORTAL_TICKETS_PATH,
} from './lib/portalAtivo'
import { gravarTicketAtivoSession } from './lib/ticketAtivo'
import { isCapacitorNative } from './lib/capacitorNative'

/**
 * Apex comercial (`deskrudder.com.br`): `/` anônimo → landing.
 * Dev local (`localhost`) e control-plane: idem, para testar LP/admin.
 * App Capacitor: o WebView também usa `localhost`, mas abre o **login do painel** (mesma API do desktop).
 * Subdomínio de cliente: `/` anônimo → login do painel.
 * Autenticado → Layout + painel (index = Dashboard).
 */
function LayoutOrLanding() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) {
    return <PageLoading fullscreen label="Carregando sessão…" />
  }
  if (!user) {
    const host = typeof window !== 'undefined' ? window.location.hostname : ''
    const isLocalDev = host === 'localhost' || host === '127.0.0.1'
    const showLanding =
      !isCapacitorNative() &&
      (location.pathname === '/' || location.pathname === '') &&
      (isMarketingHost() || isSaasControlPlaneFrontend() || isLocalDev)
    if (showLanding) {
      return <LandingPage />
    }
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (user.role === 'saas_ops') {
    if (user.must_change_password || location.pathname === '/alterar-senha') {
      return <Layout />
    }
    return <Navigate to="/saas/licencas" replace />
  }
  return <Layout />
}

function PermissaoRoute({ children, codigo }: { children: React.ReactNode; codigo: string }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <PageLoading fullscreen label="Carregando sessão…" />
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  if (!temPermissao(user, codigo)) {
    return <AcessoNegado />
  }
  return <>{children}</>
}

function AlgumaPermissaoRoute({
  children,
  codigos,
  tambemFinanceiro = false,
}: {
  children: React.ReactNode
  codigos: string[]
  tambemFinanceiro?: boolean
}) {
  const { user, loading, isFinanceiroOuAdmin } = useAuth()
  if (loading) {
    return <PageLoading fullscreen label="Carregando sessão…" />
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  const liberado =
    codigos.some((codigo) => temPermissao(user, codigo)) || (tambemFinanceiro && isFinanceiroOuAdmin)
  if (!liberado) {
    return <AcessoNegado />
  }
  return <>{children}</>
}

function Inicio() {
  const { user, loading } = useAuth()
  if (loading) return <PageLoading fullscreen label="Carregando sessão…" />
  if (temPermissao(user, 'dashboard.ver')) return <Dashboard />
  if (temPermissao(user, 'tickets.ver')) return <Navigate to="/tickets" replace />
  if (temPermissao(user, 'chat.atender') || temPermissao(user, 'whatsapp.atender')) {
    return <Navigate to="/chat/atendendo" replace />
  }
  if (temPermissao(user, 'ponto.meu')) return <Navigate to="/ponto" replace />
  return <Navigate to="/minha-conta" replace />
}

function RedirectKbArtigoEditar() {
  const { id } = useParams<{ id: string }>()
  return <Navigate to={`/ajuda/artigos/${id}/editar`} replace />
}

/**
 * Rotas legadas com id na URL (`/chat/c/:id`, `/whatsapp/c/:id`, e-mails antigos):
 * guardam a conversa como ativa e caem na aba fixa do hub (#654).
 */
function RedirectChatConversa({ canal }: { canal: ChatAtivoCanal }) {
  const params = useParams<{ chatId?: string; conversaId?: string }>()
  const location = useLocation()
  const id = Number(params.chatId ?? params.conversaId)
  if (Number.isFinite(id) && id > 0) {
    gravarChatAtivoSession({ canal, id })
  }
  const destino = chatHubPathParaModo(chatHubModoDePath(location.pathname, location.search))
  return (
    <Navigate to={{ pathname: destino, search: location.search }} replace state={location.state} />
  )
}

/** `/tickets/:id` deixa de existir: id vai para a sessão e a URL fica `/tickets` (#655). */
function RedirectTicketDetalhe() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const ticketId = Number(id)
  if (Number.isFinite(ticketId) && ticketId > 0) {
    gravarTicketAtivoSession(ticketId)
  }
  return <Navigate to="/tickets" replace state={location.state} />
}

/** `/portal/tickets/:id` legado: sessão + URL fixa `#700`. */
function RedirectPortalTicketDetalhe() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const ticketId = Number(id)
  if (Number.isFinite(ticketId) && ticketId > 0) {
    gravarPortalTicketAtivoSession(ticketId)
  }
  return <Navigate to={PORTAL_TICKETS_PATH} replace state={location.state} />
}

/** `/portal/chats/:id` legado: sessão + URL fixa `#700`. */
function RedirectPortalChatDetalhe() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const chatId = Number(id)
  if (Number.isFinite(chatId) && chatId > 0) {
    gravarPortalChatAtivoSession(chatId)
  }
  return <Navigate to={PORTAL_CHATS_PATH} replace state={location.state} />
}

function RedirectLegacyChatInterno() {
  const location = useLocation()
  const path = location.pathname.replace(/^\/chat-interno/, '/chat/interno')
  return <Navigate to={`${path}${location.search}${location.hash}`} replace />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/login/admin" element={<Login />} />
      <Route path="/auth/sessao" element={<AuthSessao />} />
      <Route path="/trial" element={<TrialPage />} />
      <Route path="/privacidade" element={<PrivacidadePage />} />
      <Route path="/esqueci-senha" element={<EsqueciSenha />} />
      <Route path="/redefinir-senha" element={<RedefinirSenha />} />
      <Route path="/avaliar-ticket" element={<AvaliarTicket />} />
      <Route path="/kb" element={<KbPublicLayout />}>
        <Route index element={<KbPublicHome />} />
        <Route path="a/:slug" element={<KbPublicArtigo />} />
      </Route>
      <Route path="/portal/login" element={<PortalBrandingRoot><PortalLogin /></PortalBrandingRoot>} />
      <Route path="/portal" element={<PortalBrandingRoot><PortalLayout /></PortalBrandingRoot>}>
        <Route index element={<Navigate to="/portal/tickets" replace />} />
        <Route path="trocar-senha" element={<PortalTrocarSenha />} />
        <Route path="tickets" element={<PortalTickets />} />
        <Route path="tickets/novo" element={<PortalTicketNovo />} />
        <Route path="tickets/:id" element={<RedirectPortalTicketDetalhe />} />
        <Route path="chats" element={<PortalChats />} />
        <Route path="chats/:id" element={<RedirectPortalChatDetalhe />} />
        <Route path="equipe" element={<PortalEquipe />} />
        <Route path="equipe/novo" element={<PortalEquipeForm />} />
        <Route path="equipe/:id" element={<PortalEquipeForm />} />
        <Route path="ajuda" element={<PortalAjudaHome />} />
        <Route path="ajuda/:slug" element={<PortalAjudaArtigo />} />
      </Route>
      <Route path="/saas" element={<SaasLayout />}>
        <Route index element={<Navigate to="licencas" replace />} />
        <Route path="licencas/novo" element={<SaasLicencaForm />} />
        <Route path="licencas/:id/editar" element={<SaasLicencaForm />} />
        <Route path="licencas/:id" element={<SaasLicencaDetalhe />} />
        <Route path="licencas" element={<SaasLicencas />} />
        <Route path="planos/novo" element={<SaasPlanoForm />} />
        <Route path="planos/:id" element={<SaasPlanoForm />} />
        <Route path="planos" element={<SaasPlanos />} />
        <Route path="modulos" element={<SaasModulos />} />
        <Route path="leads/:id" element={<SaasLeadDetalhe />} />
        <Route path="leads" element={<SaasLeads />} />
        <Route path="solicitacoes/:id" element={<SaasSolicitacaoDetalhe />} />
        <Route path="solicitacoes" element={<SaasSolicitacoes />} />
        <Route path="usuarios/novo" element={<SaasUsuarioForm />} />
        <Route path="usuarios/:id" element={<SaasUsuarioForm />} />
        <Route path="usuarios" element={<SaasUsuarios />} />
        <Route path="setores/novo" element={<SaasSetorForm />} />
        <Route path="setores/:id" element={<SaasSetorForm />} />
        <Route path="setores" element={<SaasSetoresPage />} />
        <Route path="alertas" element={<SaasAlertas />} />
        <Route path="conta" element={<SaasConta />} />
        <Route path="sobre" element={<SaasSobre />} />
      </Route>
      <Route
        path="/"
        element={<LayoutOrLanding />}
      >
        <Route index element={<Inicio />} />
        <Route path="dashboard/tickets" element={<PermissaoRoute codigo="dashboard.ver"><DashboardTickets /></PermissaoRoute>} />
        <Route path="dashboard/chats" element={<PermissaoRoute codigo="dashboard.ver"><DashboardChats /></PermissaoRoute>} />
        <Route path="ponto" element={<PermissaoRoute codigo="ponto.meu"><MeuPonto /></PermissaoRoute>} />
        <Route
          path="equipe/online"
          element={
            <PermissaoRoute codigo="presenca.ver">
              <PresencaOnline />
            </PermissaoRoute>
          }
        />
        <Route
          path="equipe/ponto"
          element={
            <PermissaoRoute codigo="ponto.equipe">
              <PontoEquipe />
            </PermissaoRoute>
          }
        />
        <Route
          path="relatorios/tickets"
          element={
            <PermissaoRoute codigo="relatorios.ver">
              <RelatoriosTickets />
            </PermissaoRoute>
          }
        />
        <Route
          path="relatorios/chats"
          element={
            <PermissaoRoute codigo="relatorios.ver">
              <RelatoriosChats />
            </PermissaoRoute>
          }
        />
        <Route path="alterar-senha" element={<AlterarSenha />} />
        <Route path="minha-conta" element={<MinhaConta />} />
        <Route path="ajuda" element={<AjudaLayout />}>
          <Route index element={<Navigate to="consultar" replace />} />
          <Route path="consultar" element={<PermissaoRoute codigo="ajuda.consultar"><KbConsultaSection /></PermissaoRoute>} />
          <Route
            path="categorias"
            element={
              <PermissaoRoute codigo="ajuda.categorias.ver">
                <KbCategoriasPage embedded />
              </PermissaoRoute>
            }
          />
          <Route
            path="artigos"
            element={
              <PermissaoRoute codigo="ajuda.artigos.ver">
                <KbArtigosPage embedded />
              </PermissaoRoute>
            }
          />
        </Route>
        <Route path="ajuda/portal" element={<Navigate to="/configuracoes/canais/base-conhecimento" replace />} />
        <Route
          path="ajuda/artigos/novo"
          element={
            <PermissaoRoute codigo="ajuda.artigos.criar">
              <KbArtigoForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="ajuda/artigos/:id/editar"
          element={
            <PermissaoRoute codigo="ajuda.artigos.editar">
              <KbArtigoForm />
            </PermissaoRoute>
          }
        />
        <Route path="notificacoes/preferencias" element={<NotificacoesPreferencias />} />
        <Route path="sobre" element={<Sobre />} />
        <Route path="sobre/nova-solicitacao" element={<SolicitacaoMelhoriaNovaPage />} />
        <Route path="minhas-solicitacoes" element={<MinhasSolicitacoesPage />} />
        <Route path="minhas-solicitacoes/:id" element={<MinhasSolicitacoesPage />} />
        <Route
          path="solicitacoes-melhoria"
          element={
            <PermissaoRoute codigo="solicitacoes.ver">
              <SolicitacoesMelhoriaAdminPage />
            </PermissaoRoute>
          }
        />
        <Route
          path="solicitacoes-melhoria/:id"
          element={
            <PermissaoRoute codigo="solicitacoes.ver">
              <SolicitacoesMelhoriaAdminPage />
            </PermissaoRoute>
          }
        />
        <Route path="tickets" element={<PermissaoRoute codigo="tickets.ver"><Tickets /></PermissaoRoute>} />
        <Route path="tickets/novo" element={<PermissaoRoute codigo="tickets.criar"><TicketNovo /></PermissaoRoute>} />
        <Route path="tickets/:id" element={<PermissaoRoute codigo="tickets.ver"><RedirectTicketDetalhe /></PermissaoRoute>} />
        <Route
          path="crm/leads"
          element={
            <PermissaoRoute codigo="crm.ver">
              <CrmLeads />
            </PermissaoRoute>
          }
        />
        <Route
          path="crm/negociacoes/:id"
          element={
            <PermissaoRoute codigo="crm.ver">
              <CrmNegociacaoDetalhe />
            </PermissaoRoute>
          }
        />
        <Route
          path="crm/contratos"
          element={
            <PermissaoRoute codigo="contratos.ver">
              <CrmContratos />
            </PermissaoRoute>
          }
        />
        <Route
          path="faturamento"
          element={
            <AlgumaPermissaoRoute codigos={['faturamento.ver']} tambemFinanceiro>
              <Faturamento />
            </AlgumaPermissaoRoute>
          }
        />
        <Route path="chat" element={<ChatHubShell />}>
          <Route element={<ChatHubLayout />}>
            <Route index element={<Navigate to="atendendo" replace />} />
            <Route
              path="atendendo"
              element={
                <ChatHubPainel
                  placeholder={
                    <ChatHubPlaceholder
                      titulo="Atendendo"
                      subtitulo="Selecione um dos seus chats em atendimento na lista ao lado."
                    />
                  }
                />
              }
            />
            <Route
              path="espera"
              element={
                <ChatHubPainel
                  placeholder={
                    <ChatHubPlaceholder
                      titulo="Aguardando"
                      subtitulo="Chats na fila — assuma um novo atendimento."
                    />
                  }
                />
              }
            />
            <Route
              path="contatos"
              element={
                <ChatHubPainel
                  placeholder={
                    <ChatHubPlaceholder
                      titulo="Contatos"
                      subtitulo="Escolha um contato ou número avulso para iniciar conversa no WhatsApp."
                    />
                  }
                />
              }
            />
            <Route path="portal" element={<Navigate to="/chat/espera" replace />} />
            <Route path="portal/:chatId" element={<RedirectChatConversa canal="portal" />} />
            <Route
              path="interno"
              element={
                <ChatHubPainel
                  placeholder={
                    <ChatHubPlaceholder
                      titulo="Chat interno"
                      subtitulo="Converse com colegas ou acesse o canal do seu setor."
                    />
                  }
                />
              }
            />
            <Route path="interno/setor/:setorId" element={<ChatInternoSetorCanal />} />
            <Route path="interno/:conversaId" element={<RedirectChatConversa canal="interno" />} />
            <Route path="c/:chatId" element={<RedirectChatConversa canal="whatsapp" />} />
          </Route>
        </Route>
        <Route path="chat/historico" element={<Navigate to="/whatsapp/historico" replace />} />
        <Route path="whatsapp" element={<WhatsappLayout />}>
          <Route index element={<Navigate to="/chat/atendendo" replace />} />
          <Route path="atendendo" element={<Navigate to="/chat/atendendo" replace />} />
          <Route path="historico" element={<PermissaoRoute codigo="chat.historico"><WhatsappHistorico /></PermissaoRoute>} />
          <Route path="historico/:chatId" element={<PermissaoRoute codigo="chat.historico"><WhatsappConversa modoConsulta /></PermissaoRoute>} />
          <Route path="fila" element={<Navigate to="/chat/espera" replace />} />
          <Route path="meus" element={<Navigate to="/chat/atendendo" replace />} />
          <Route path="c/:chatId" element={<RedirectChatConversa canal="whatsapp" />} />
          <Route
            path="avaliacoes"
            element={
              <PermissaoRoute codigo="chat.avaliacoes">
                <WhatsappAvaliacoes />
              </PermissaoRoute>
            }
          />
        </Route>
        <Route path="chat-interno/*" element={<RedirectLegacyChatInterno />} />
        <Route
          path="redes/:id"
          element={
            <PermissaoRoute codigo="redes.ver">
              <RedeDetalhe />
            </PermissaoRoute>
          }
        />
        <Route
          path="redes/novo"
          element={
            <PermissaoRoute codigo="redes.criar">
              <RedeForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="redes/:id/editar"
          element={
            <PermissaoRoute codigo="redes.editar">
              <RedeForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="redes"
          element={
            <PermissaoRoute codigo="redes.ver">
              <Redes />
            </PermissaoRoute>
          }
        />
        <Route
          path="empresas/novo"
          element={
            <PermissaoRoute codigo="empresas.criar">
              <EmpresaForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="empresas/:id/editar"
          element={
            <PermissaoRoute codigo="empresas.editar">
              <EmpresaForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="empresas/:id"
          element={
            <AlgumaPermissaoRoute codigos={['empresas.ver', 'pdv.acessos.ver', 'empresas.editar']}>
              <EmpresaDetalhe />
            </AlgumaPermissaoRoute>
          }
        />
        <Route
          path="empresas"
          element={
            <PermissaoRoute codigo="empresas.ver">
              <Empresas />
            </PermissaoRoute>
          }
        />
        <Route path="rustdesk" element={<Navigate to="/acesso-remoto" replace />} />
        <Route
          path="acesso-remoto"
          element={
            <PermissaoRoute codigo="rustdesk.monitorar">
              <RustdeskPeers />
            </PermissaoRoute>
          }
        />
        <Route
          path="setores/novo"
          element={
            <PermissaoRoute codigo="setores.criar">
              <SetorForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="setores/:id/editar"
          element={
            <PermissaoRoute codigo="setores.editar">
              <SetorForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="setores/:id"
          element={
            <PermissaoRoute codigo="setores.ver">
              <SetorDetalhe />
            </PermissaoRoute>
          }
        />
        <Route path="setores" element={<Navigate to="/configuracoes/equipe/setores" replace />} />
        <Route
          path="atendentes/novo"
          element={
            <PermissaoRoute codigo="atendentes.criar">
              <AtendenteForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="atendentes/:id/editar"
          element={
            <PermissaoRoute codigo="atendentes.editar">
              <AtendenteForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="atendentes/:id"
          element={
            <PermissaoRoute codigo="atendentes.ver">
              <AtendenteDetalhe />
            </PermissaoRoute>
          }
        />
        <Route path="atendentes" element={<Navigate to="/configuracoes/equipe/atendentes" replace />} />
        <Route path="funcionarios-rede/:id" element={<FuncionarioRedeDetalhe />} />
        <Route
          path="funcionarios-rede/novo"
          element={
            <PermissaoRoute codigo="funcionarios.criar">
              <FuncionarioRedeForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="funcionarios-rede/:id/editar"
          element={
            <PermissaoRoute codigo="funcionarios.editar">
              <FuncionarioRedeForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="funcionarios-rede"
          element={
            <PermissaoRoute codigo="funcionarios.ver">
              <FuncionariosRede />
            </PermissaoRoute>
          }
        />
        <Route
          path="respostas-prontas/novo"
          element={
            <PermissaoRoute codigo="respostas.criar">
              <RespostaProntaForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="respostas-prontas/:id/editar"
          element={
            <PermissaoRoute codigo="respostas.editar">
              <RespostaProntaForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="respostas-prontas/:id"
          element={
            <PermissaoRoute codigo="respostas.ver">
              <RespostaProntaDetalhe />
            </PermissaoRoute>
          }
        />
        <Route path="respostas-prontas" element={<Navigate to="/configuracoes/tickets/respostas-prontas" replace />} />
        <Route
          path="base-conhecimento/novo"
          element={<Navigate to="/ajuda/artigos/novo" replace />}
        />
        <Route
          path="base-conhecimento/:id/editar"
          element={<RedirectKbArtigoEditar />}
        />
        <Route path="base-conhecimento" element={<Navigate to="/ajuda/artigos" replace />} />
        <Route
          path="status-ticket/novo"
          element={
            <PermissaoRoute codigo="status_ticket.criar">
              <StatusTicketForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="status-ticket/:id/editar"
          element={
            <PermissaoRoute codigo="status_ticket.editar">
              <StatusTicketForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="status-ticket/:id"
          element={
            <PermissaoRoute codigo="status_ticket.ver">
              <StatusTicketDetalhe />
            </PermissaoRoute>
          }
        />
        <Route path="status-ticket" element={<Navigate to="/configuracoes/tickets/status-ticket" replace />} />
        <Route path="auditoria" element={<Navigate to="/configuracoes/administracao/auditoria" replace />} />
        <Route
          path="tipos-negocio/novo"
          element={
            <PermissaoRoute codigo="tipos_negocio.criar">
              <TipoNegocioForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="tipos-negocio/:id/editar"
          element={
            <PermissaoRoute codigo="tipos_negocio.editar">
              <TipoNegocioForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="tipos-negocio/:id"
          element={
            <PermissaoRoute codigo="tipos_negocio.ver">
              <TipoNegocioDetalhe />
            </PermissaoRoute>
          }
        />
        <Route path="tipos-negocio" element={<Navigate to="/configuracoes/comercial/tipos-negocio" replace />} />
        <Route
          path="configuracoes"
          element={
            <AlgumaPermissaoRoute codigos={todasPermissoesConfig()}>
              <ConfigHubPage />
            </AlgumaPermissaoRoute>
          }
        />
        <Route
          path="configuracoes/equipe/grupos-permissao/novo"
          element={
            <PermissaoRoute codigo="grupos.criar">
              <GrupoPermissaoForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="configuracoes/equipe/grupos-permissao/:id/editar"
          element={
            <PermissaoRoute codigo="grupos.editar">
              <GrupoPermissaoForm />
            </PermissaoRoute>
          }
        />
        <Route
          path="configuracoes/equipe/grupos-permissao/:id"
          element={
            <PermissaoRoute codigo="grupos.ver">
              <GrupoPermissaoDetalhe />
            </PermissaoRoute>
          }
        />
        <Route
          path="configuracoes/:domain"
          element={
            <AlgumaPermissaoRoute codigos={todasPermissoesConfig()}>
              <ConfigDomainLayout />
            </AlgumaPermissaoRoute>
          }
        >
          <Route index element={<ConfigDomainIndexRedirect />} />
          <Route path="setores" element={<PermissaoRoute codigo="setores.ver"><Setores embedded /></PermissaoRoute>} />
          <Route path="atendentes" element={<PermissaoRoute codigo="atendentes.ver"><Atendentes embedded /></PermissaoRoute>} />
          <Route path="grupos-permissao" element={<PermissaoRoute codigo="grupos.ver"><GruposPermissao embedded /></PermissaoRoute>} />
          <Route path="status-ticket" element={<PermissaoRoute codigo="status_ticket.ver"><StatusTicketPage embedded /></PermissaoRoute>} />
          <Route path="natureza-motivo" element={<PermissaoRoute codigo="natureza.ver"><TicketNaturezaMotivoPage embedded /></PermissaoRoute>} />
          <Route path="respostas-prontas" element={<PermissaoRoute codigo="respostas.ver"><RespostasProntasPage embedded /></PermissaoRoute>} />
          <Route path="roteamento" element={<PermissaoRoute codigo="roteamento.ver"><RoteamentoRegrasPage embedded /></PermissaoRoute>} />
          <Route element={<PermissaoRoute codigo="sla.ver"><Outlet /></PermissaoRoute>}>
          <Route path="sla" element={<SlaConfigLayout />}>
            <Route index element={<Navigate to="politicas" replace />} />
            <Route path="politicas" element={<SlaPoliticasPage embedded />} />
            <Route path="calendarios" element={<SlaCalendariosPage embedded />} />
          </Route>
          </Route>
          <Route path="whatsapp" element={<PermissaoRoute codigo="canais.whatsapp.ver"><ConfigWhatsapp embedded /></PermissaoRoute>} />
          <Route path="email" element={<PermissaoRoute codigo="canais.email.ver"><ConfigEmpresaEmail embedded section="email" /></PermissaoRoute>} />
          <Route path="base-conhecimento" element={<PermissaoRoute codigo="ajuda.portal"><KbPortalSettingsPage embedded /></PermissaoRoute>} />
          <Route path="funil-crm" element={<PermissaoRoute codigo="funil.editar"><ConfigCrmFunil embedded /></PermissaoRoute>} />
          <Route path="propostas" element={<PermissaoRoute codigo="propostas.modelos"><ConfigPropostaTemplates embedded /></PermissaoRoute>} />
          <Route path="contratos" element={<PermissaoRoute codigo="contratos.modelos"><ConfigContratoTemplates embedded /></PermissaoRoute>} />
          <Route path="custos" element={<AlgumaPermissaoRoute codigos={['custos.ver', 'custos.simular', 'custos.editar']}><ConfigComercialCustos embedded /></AlgumaPermissaoRoute>} />
          <Route path="implantacao" element={<PermissaoRoute codigo="implantacao.editar"><ConfigImplantacaoChecklist embedded /></PermissaoRoute>} />
          <Route path="empresa" element={<PermissaoRoute codigo="instalacao.ver"><ConfigEmpresaEmail embedded section="empresa" /></PermissaoRoute>} />
          <Route path="tipos-negocio" element={<PermissaoRoute codigo="tipos_negocio.ver"><TiposNegocio embedded /></PermissaoRoute>} />
          <Route path="pdv" element={<PermissaoRoute codigo="pdv.ver"><ConfigPdvCatalogos embedded /></PermissaoRoute>} />
          <Route path="auditoria" element={<PermissaoRoute codigo="auditoria.ver"><Auditoria embedded /></PermissaoRoute>} />
          <Route path="sugestoes" element={<Navigate to="/solicitacoes-melhoria" replace />} />
        </Route>
        <Route path="configuracoes/atendimento/*" element={<ConfigLegacyRedirect />} />
        <Route path="configuracoes/cadastros/*" element={<ConfigLegacyRedirect />} />
        <Route path="configuracoes/sistema/*" element={<ConfigLegacyRedirect />} />
        <Route path="configuracoes/equipa/*" element={<ConfigLegacyRedirect />} />
        <Route path="configuracoes/empresa-catalogos/*" element={<ConfigLegacyRedirect />} />
        <Route path="configuracoes/whatsapp" element={<ConfigLegacyRedirect />} />
        <Route path="configuracoes/empresa-email" element={<ConfigLegacyRedirect />} />
        <Route path="configuracoes/pdv-catalogos" element={<ConfigLegacyRedirect />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ThemeProvider>
          <AuthProvider>
            <ToastProvider>
              <AppRoutes />
            </ToastProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
