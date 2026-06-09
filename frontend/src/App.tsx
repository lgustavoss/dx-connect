import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { EsqueciSenha } from './pages/EsqueciSenha'
import { RedefinirSenha } from './pages/RedefinirSenha'
import { Dashboard } from './pages/Dashboard'
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
import { RespostaProntaForm } from './pages/RespostaProntaForm'
import { RespostaProntaDetalhe } from './pages/RespostaProntaDetalhe'
import { Auditoria } from './pages/Auditoria'
import { TiposNegocio } from './pages/TiposNegocio'
import { TipoNegocioForm } from './pages/TipoNegocioForm'
import { TipoNegocioDetalhe } from './pages/TipoNegocioDetalhe'
import { ConfigWhatsapp } from './pages/ConfigWhatsapp'
import { ConfigPdvCatalogos } from './pages/ConfigPdvCatalogos'
import { ConfigEmpresaEmail } from './pages/ConfigEmpresaEmail'
import { ConfigAtendimentoLayout } from './pages/config/ConfigAtendimentoLayout'
import { ConfigCadastrosLayout } from './pages/config/ConfigCadastrosLayout'
import { ConfigSistemaLayout } from './pages/config/ConfigSistemaLayout'
import { WhatsappLayout } from './pages/whatsapp/WhatsappLayout'
import { WhatsappAtendendo } from './pages/whatsapp/WhatsappAtendendo'
import { WhatsappHistorico } from './pages/whatsapp/WhatsappHistorico'
import { WhatsappConversa } from './pages/whatsapp/WhatsappConversa'
import { AlterarSenha } from './pages/AlterarSenha'
import { AcessoNegado } from './pages/AcessoNegado'
import { ToastProvider } from './components/ui/Toast'
import { ErrorBoundary } from './components/ErrorBoundary'
import { PageLoading } from './components/ui/PageLoading'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <PageLoading fullscreen label="Carregando sessão…" />
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
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

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/esqueci-senha" element={<EsqueciSenha />} />
      <Route path="/redefinir-senha" element={<RedefinirSenha />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="alterar-senha" element={<AlterarSenha />} />
        <Route path="tickets" element={<Tickets />} />
        <Route path="tickets/novo" element={<TicketNovo />} />
        <Route path="tickets/:id" element={<TicketDetalhe />} />
        <Route path="whatsapp" element={<WhatsappLayout />}>
          <Route index element={<Navigate to="atendendo" replace />} />
          <Route path="atendendo" element={<WhatsappAtendendo />} />
          <Route path="historico" element={<WhatsappHistorico />} />
          <Route path="fila" element={<Navigate to="/whatsapp/atendendo" replace />} />
          <Route path="meus" element={<Navigate to="/whatsapp/atendendo" replace />} />
          <Route path="c/:chatId" element={<WhatsappConversa />} />
        </Route>
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
