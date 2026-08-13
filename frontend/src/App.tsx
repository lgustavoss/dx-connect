import { BrowserRouter, Routes, Route, Navigate, useParams, useLocation } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { AuthSessao } from './pages/AuthSessao'
import { EsqueciSenha } from './pages/EsqueciSenha'
import { RedefinirSenha } from './pages/RedefinirSenha'
import { AvaliarTicket } from './pages/AvaliarTicket'
import { LandingPage } from './pages/marketing/LandingPage'
import { TrialPage } from './pages/marketing/TrialPage'
import { Dashboard } from './pages/Dashboard'
import { DashboardTickets } from './pages/DashboardTickets'
import { DashboardChats } from './pages/DashboardChats'
import { RelatoriosTickets } from './pages/RelatoriosTickets'
import { RelatoriosChats } from './pages/RelatoriosChats'
import { PresencaOnline } from './pages/PresencaOnline'
import { Tickets } from './pages/Tickets'
import { TicketNovo } from './pages/TicketNovo'
import { TicketDetalhe } from './pages/TicketDetalhe'
import { Redes } from './pages/Redes'
import { RedeDetalhe } from './pages/RedeDetalhe'
import { RedeForm } from './pages/RedeForm'
import { Empresas } from './pages/Empresas'
import { EmpresaForm } from './pages/EmpresaForm'
import { EmpresaDetalhe } from './pages/EmpresaDetalhe'
import { Setores } from './pages/Setores'
import { SetorForm } from './pages/SetorForm'
import { SetorDetalhe } from './pages/SetorDetalhe'
import { Atendentes } from './pages/Atendentes'
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
import { ConfigAtendimentoLayout } from './pages/config/ConfigAtendimentoLayout'
import { ConfigCadastrosLayout } from './pages/config/ConfigCadastrosLayout'
import { ConfigSistemaLayout } from './pages/config/ConfigSistemaLayout'
import { WhatsappLayout } from './pages/whatsapp/WhatsappLayout'
import { WhatsappHistorico } from './pages/whatsapp/WhatsappHistorico'
import { WhatsappAvaliacoes } from './pages/whatsapp/WhatsappAvaliacoes'
import { WhatsappConversa } from './pages/whatsapp/WhatsappConversa'
import { ChatInternoThread } from './pages/chat-interno/ChatInternoThread'
import { ChatInternoSetorCanal } from './pages/chat-interno/ChatInternoSetorCanal'
import { ChatHubShell } from './pages/chat/ChatHubShell'
import { ChatHubLayout } from './pages/chat/ChatHubLayout'
import { ChatHubPlaceholder } from './pages/chat/ChatHubPlaceholder'
import { PortalConversa } from './pages/chat/PortalConversa'
import { AlterarSenha } from './pages/AlterarSenha'
import { NotificacoesPreferencias } from './pages/NotificacoesPreferencias'
import { Sobre } from './pages/Sobre'
import { AcessoNegado } from './pages/AcessoNegado'
import { SaasLicencas } from './pages/saas/SaasLicencas'
import { SaasLicencaForm } from './pages/saas/SaasLicencaForm'
import { SaasLicencaDetalhe } from './pages/saas/SaasLicencaDetalhe'
import { SaasPlanos } from './pages/saas/SaasPlanos'
import { SaasPlanoForm } from './pages/saas/SaasPlanoForm'
import { SaasModulos } from './pages/saas/SaasModulos'
import { SaasLeads } from './pages/saas/SaasLeads'
import { SaasLeadDetalhe } from './pages/saas/SaasLeadDetalhe'
import { SaasLayout } from './pages/saas/SaasLayout'
import { SaasSobre } from './pages/saas/SaasSobre'
import { KbPublicLayout } from './pages/kb-public/KbPublicLayout'
import { KbPublicHome } from './pages/kb-public/KbPublicHome'
import { KbPublicArtigo } from './pages/kb-public/KbPublicArtigo'
import { PortalBrandingRoot } from './pages/portal/PortalBrandingRoot'
import { PortalLayout } from './pages/portal/PortalLayout'
import { PortalLogin } from './pages/portal/PortalLogin'
import { PortalTrocarSenha } from './pages/portal/PortalTrocarSenha'
import { PortalTickets } from './pages/portal/PortalTickets'
import { PortalTicketNovo } from './pages/portal/PortalTicketNovo'
import { PortalTicketDetalhe } from './pages/portal/PortalTicketDetalhe'
import { PortalAjudaHome, PortalAjudaArtigo } from './pages/portal/PortalAjuda'
import { PortalChats } from './pages/portal/PortalChats'
import { PortalChatDetalhe } from './pages/portal/PortalChatDetalhe'
import { PortalEquipe } from './pages/portal/PortalEquipe'
import { PortalEquipeForm } from './pages/portal/PortalEquipeForm'
import { ToastProvider } from './components/ui/Toast'
import { ErrorBoundary } from './components/ErrorBoundary'
import { PageLoading } from './components/ui/PageLoading'
import { isMarketingHost } from './lib/marketingHost'
import { isSaasControlPlaneFrontend } from './lib/saasControlPlane'

/**
 * Apex comercial (`deskrudder.com.br`): `/` anônimo → landing.
 * Dev local (`localhost`) e control-plane: idem, para testar LP/admin.
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
      (location.pathname === '/' || location.pathname === '') &&
      (isMarketingHost() || isSaasControlPlaneFrontend() || isLocalDev)
    if (showLanding) {
      return <LandingPage />
    }
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (user.role === 'saas_ops') {
    return <Navigate to="/saas/licencas" replace />
  }
  return <Layout />
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <PageLoading fullscreen label="Carregando sessão…" />
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  if (user.role !== 'admin') {
    return <AcessoNegado />
  }
  return <>{children}</>
}

function RedirectKbArtigoEditar() {
  const { id } = useParams<{ id: string }>()
  return <Navigate to={`/ajuda/artigos/${id}/editar`} replace />
}

function RedirectWhatsappConversa() {
  const { chatId } = useParams<{ chatId: string }>()
  return <Navigate to={`/chat/c/${chatId}`} replace />
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
        <Route path="tickets/:id" element={<PortalTicketDetalhe />} />
        <Route path="chats" element={<PortalChats />} />
        <Route path="chats/:id" element={<PortalChatDetalhe />} />
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
        <Route path="sobre" element={<SaasSobre />} />
      </Route>
      <Route
        path="/"
        element={<LayoutOrLanding />}
      >
        <Route index element={<Dashboard />} />
        <Route path="dashboard/tickets" element={<DashboardTickets />} />
        <Route path="dashboard/chats" element={<DashboardChats />} />
        <Route
          path="equipe/online"
          element={
            <AdminRoute>
              <PresencaOnline />
            </AdminRoute>
          }
        />
        <Route
          path="relatorios/tickets"
          element={
            <AdminRoute>
              <RelatoriosTickets />
            </AdminRoute>
          }
        />
        <Route
          path="relatorios/chats"
          element={
            <AdminRoute>
              <RelatoriosChats />
            </AdminRoute>
          }
        />
        <Route path="alterar-senha" element={<AlterarSenha />} />
        <Route path="ajuda" element={<AjudaLayout />}>
          <Route index element={<Navigate to="consultar" replace />} />
          <Route path="consultar" element={<KbConsultaSection />} />
          <Route
            path="categorias"
            element={
              <AdminRoute>
                <KbCategoriasPage embedded />
              </AdminRoute>
            }
          />
          <Route
            path="artigos"
            element={
              <AdminRoute>
                <KbArtigosPage embedded />
              </AdminRoute>
            }
          />
        </Route>
        <Route path="ajuda/portal" element={<Navigate to="/configuracoes/sistema/base-conhecimento" replace />} />
        <Route
          path="ajuda/artigos/novo"
          element={
            <AdminRoute>
              <KbArtigoForm />
            </AdminRoute>
          }
        />
        <Route
          path="ajuda/artigos/:id/editar"
          element={
            <AdminRoute>
              <KbArtigoForm />
            </AdminRoute>
          }
        />
        <Route path="notificacoes/preferencias" element={<NotificacoesPreferencias />} />
        <Route path="sobre" element={<Sobre />} />
        <Route path="tickets" element={<Tickets />} />
        <Route path="tickets/novo" element={<TicketNovo />} />
        <Route path="tickets/:id" element={<TicketDetalhe />} />
        <Route path="chat" element={<ChatHubShell />}>
          <Route element={<ChatHubLayout />}>
            <Route index element={<Navigate to="atendendo" replace />} />
            <Route
              path="atendendo"
              element={
                <ChatHubPlaceholder
                  titulo="Atendendo"
                  subtitulo="Selecione um dos seus chats em atendimento na lista ao lado."
                />
              }
            />
            <Route
              path="espera"
              element={
                <ChatHubPlaceholder
                  titulo="Aguardando"
                  subtitulo="Chats na fila — assuma um novo atendimento."
                />
              }
            />
            <Route
              path="contatos"
              element={
                <ChatHubPlaceholder
                  titulo="Contatos"
                  subtitulo="Escolha um contacto ou número avulso para iniciar conversa no WhatsApp."
                />
              }
            />
            <Route path="portal" element={<Navigate to="/chat/espera" replace />} />
            <Route path="portal/:chatId" element={<PortalConversa />} />
            <Route
              path="interno"
              element={
                <ChatHubPlaceholder
                  titulo="Chat interno"
                  subtitulo="Converse com colegas ou acesse o canal do seu setor."
                />
              }
            />
            <Route path="interno/setor/:setorId" element={<ChatInternoSetorCanal />} />
            <Route path="interno/:conversaId" element={<ChatInternoThread />} />
            <Route path="c/:chatId" element={<WhatsappConversa />} />
          </Route>
        </Route>
        <Route path="chat/historico" element={<Navigate to="/whatsapp/historico" replace />} />
        <Route path="whatsapp" element={<WhatsappLayout />}>
          <Route index element={<Navigate to="/chat/atendendo" replace />} />
          <Route path="atendendo" element={<Navigate to="/chat/atendendo" replace />} />
          <Route path="historico" element={<WhatsappHistorico />} />
          <Route path="fila" element={<Navigate to="/chat/espera" replace />} />
          <Route path="meus" element={<Navigate to="/chat/atendendo" replace />} />
          <Route path="c/:chatId" element={<RedirectWhatsappConversa />} />
          <Route
            path="avaliacoes"
            element={
              <AdminRoute>
                <WhatsappAvaliacoes />
              </AdminRoute>
            }
          />
        </Route>
        <Route path="chat-interno/*" element={<RedirectLegacyChatInterno />} />
        <Route
          path="redes/:id"
          element={
            <AdminRoute>
              <RedeDetalhe />
            </AdminRoute>
          }
        />
        <Route
          path="redes/novo"
          element={
            <AdminRoute>
              <RedeForm />
            </AdminRoute>
          }
        />
        <Route
          path="redes/:id/editar"
          element={
            <AdminRoute>
              <RedeForm />
            </AdminRoute>
          }
        />
        <Route
          path="redes"
          element={
            <AdminRoute>
              <Redes />
            </AdminRoute>
          }
        />
        <Route
          path="empresas/novo"
          element={
            <AdminRoute>
              <EmpresaForm />
            </AdminRoute>
          }
        />
        <Route
          path="empresas/:id/editar"
          element={
            <AdminRoute>
              <EmpresaForm />
            </AdminRoute>
          }
        />
        <Route
          path="empresas/:id"
          element={
            <AdminRoute>
              <EmpresaDetalhe />
            </AdminRoute>
          }
        />
        <Route
          path="empresas"
          element={
            <AdminRoute>
              <Empresas />
            </AdminRoute>
          }
        />
        <Route
          path="setores/novo"
          element={
            <AdminRoute>
              <SetorForm />
            </AdminRoute>
          }
        />
        <Route
          path="setores/:id/editar"
          element={
            <AdminRoute>
              <SetorForm />
            </AdminRoute>
          }
        />
        <Route
          path="setores/:id"
          element={
            <AdminRoute>
              <SetorDetalhe />
            </AdminRoute>
          }
        />
        <Route path="setores" element={<Navigate to="/configuracoes/atendimento/setores" replace />} />
        <Route
          path="atendentes/novo"
          element={
            <AdminRoute>
              <AtendenteForm />
            </AdminRoute>
          }
        />
        <Route
          path="atendentes/:id/editar"
          element={
            <AdminRoute>
              <AtendenteForm />
            </AdminRoute>
          }
        />
        <Route
          path="atendentes/:id"
          element={
            <AdminRoute>
              <AtendenteDetalhe />
            </AdminRoute>
          }
        />
        <Route path="atendentes" element={<Navigate to="/configuracoes/atendimento/atendentes" replace />} />
        <Route
          path="funcionarios-rede/:id"
          element={
            <AdminRoute>
              <FuncionarioRedeDetalhe />
            </AdminRoute>
          }
        />
        <Route
          path="funcionarios-rede/novo"
          element={
            <AdminRoute>
              <FuncionarioRedeForm />
            </AdminRoute>
          }
        />
        <Route
          path="funcionarios-rede/:id/editar"
          element={
            <AdminRoute>
              <FuncionarioRedeForm />
            </AdminRoute>
          }
        />
        <Route
          path="funcionarios-rede"
          element={
            <AdminRoute>
              <FuncionariosRede />
            </AdminRoute>
          }
        />
        <Route
          path="respostas-prontas/novo"
          element={
            <AdminRoute>
              <RespostaProntaForm />
            </AdminRoute>
          }
        />
        <Route
          path="respostas-prontas/:id/editar"
          element={
            <AdminRoute>
              <RespostaProntaForm />
            </AdminRoute>
          }
        />
        <Route
          path="respostas-prontas/:id"
          element={
            <AdminRoute>
              <RespostaProntaDetalhe />
            </AdminRoute>
          }
        />
        <Route path="respostas-prontas" element={<Navigate to="/configuracoes/atendimento/respostas-prontas" replace />} />
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
            <AdminRoute>
              <StatusTicketForm />
            </AdminRoute>
          }
        />
        <Route
          path="status-ticket/:id/editar"
          element={
            <AdminRoute>
              <StatusTicketForm />
            </AdminRoute>
          }
        />
        <Route
          path="status-ticket/:id"
          element={
            <AdminRoute>
              <StatusTicketDetalhe />
            </AdminRoute>
          }
        />
        <Route path="status-ticket" element={<Navigate to="/configuracoes/atendimento/status-ticket" replace />} />
        <Route path="auditoria" element={<Navigate to="/configuracoes/sistema/auditoria" replace />} />
        <Route
          path="tipos-negocio/novo"
          element={
            <AdminRoute>
              <TipoNegocioForm />
            </AdminRoute>
          }
        />
        <Route
          path="tipos-negocio/:id/editar"
          element={
            <AdminRoute>
              <TipoNegocioForm />
            </AdminRoute>
          }
        />
        <Route
          path="tipos-negocio/:id"
          element={
            <AdminRoute>
              <TipoNegocioDetalhe />
            </AdminRoute>
          }
        />
        <Route path="tipos-negocio" element={<Navigate to="/configuracoes/cadastros/tipos-negocio" replace />} />
        <Route
          path="configuracoes/atendimento"
          element={
            <AdminRoute>
              <ConfigAtendimentoLayout />
            </AdminRoute>
          }
        >
          <Route index element={<Navigate to="setores" replace />} />
          <Route path="setores" element={<Setores embedded />} />
          <Route path="atendentes" element={<Atendentes embedded />} />
          <Route path="status-ticket" element={<StatusTicketPage embedded />} />
          <Route path="natureza-motivo" element={<TicketNaturezaMotivoPage embedded />} />
          <Route path="respostas-prontas" element={<RespostasProntasPage embedded />} />
          <Route path="base-conhecimento" element={<Navigate to="/ajuda/artigos" replace />} />
          <Route path="roteamento" element={<RoteamentoRegrasPage embedded />} />
          <Route path="sla" element={<SlaConfigLayout />}>
            <Route index element={<Navigate to="politicas" replace />} />
            <Route path="politicas" element={<SlaPoliticasPage embedded />} />
            <Route path="calendarios" element={<SlaCalendariosPage embedded />} />
          </Route>
        </Route>
        <Route
          path="configuracoes/cadastros"
          element={
            <AdminRoute>
              <ConfigCadastrosLayout />
            </AdminRoute>
          }
        >
          <Route index element={<Navigate to="tipos-negocio" replace />} />
          <Route path="tipos-negocio" element={<TiposNegocio embedded />} />
          <Route path="pdv" element={<ConfigPdvCatalogos embedded />} />
          <Route path="custos" element={<ConfigComercialCustos embedded />} />
        </Route>
        <Route
          path="configuracoes/sistema"
          element={
            <AdminRoute>
              <ConfigSistemaLayout />
            </AdminRoute>
          }
        >
          <Route index element={<Navigate to="empresa" replace />} />
          <Route path="empresa" element={<ConfigEmpresaEmail embedded section="empresa" />} />
          <Route path="email" element={<ConfigEmpresaEmail embedded section="email" />} />
          <Route path="empresa-email" element={<Navigate to="empresa" replace />} />
          <Route path="whatsapp" element={<ConfigWhatsapp embedded />} />
          <Route path="base-conhecimento" element={<KbPortalSettingsPage embedded />} />
          <Route path="auditoria" element={<Auditoria embedded />} />
        </Route>
        <Route
          path="configuracoes/whatsapp"
          element={<Navigate to="/configuracoes/sistema/whatsapp" replace />}
        />
        <Route
          path="configuracoes/empresa-email"
          element={<Navigate to="/configuracoes/sistema/empresa" replace />}
        />
        <Route
          path="configuracoes/pdv-catalogos"
          element={<Navigate to="/configuracoes/cadastros/pdv" replace />}
        />
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
