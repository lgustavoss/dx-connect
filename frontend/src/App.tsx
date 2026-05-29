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
import { ConfigEmpresaEmail } from './pages/ConfigEmpresaEmail'
import { WhatsappLayout } from './pages/whatsapp/WhatsappLayout'
import { WhatsappAtendendo } from './pages/whatsapp/WhatsappAtendendo'
import { WhatsappHistorico } from './pages/whatsapp/WhatsappHistorico'
import { WhatsappConversa } from './pages/whatsapp/WhatsappConversa'
import { AlterarSenha } from './pages/AlterarSenha'
import { AcessoNegado } from './pages/AcessoNegado'
import { ToastProvider } from './components/ui/Toast'
import { ErrorBoundary } from './components/ErrorBoundary'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <span className="text-slate-500 dark:text-slate-400">Carregando...</span>
      </div>
    )
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <span className="text-slate-500 dark:text-slate-400">Carregando...</span>
      </div>
    )
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
          path="setores"
          element={
            <AdminRoute>
              <Setores />
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
        <Route
          path="atendentes"
          element={
            <AdminRoute>
              <Atendentes />
            </AdminRoute>
          }
        />
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
        <Route
          path="respostas-prontas"
          element={
            <AdminRoute>
              <RespostasProntasPage />
            </AdminRoute>
          }
        />
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
        <Route
          path="status-ticket"
          element={
            <AdminRoute>
              <StatusTicketPage />
            </AdminRoute>
          }
        />
        <Route
          path="auditoria"
          element={
            <AdminRoute>
              <Auditoria />
            </AdminRoute>
          }
        />
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
        <Route
          path="tipos-negocio"
          element={
            <AdminRoute>
              <TiposNegocio />
            </AdminRoute>
          }
        />
        <Route
          path="configuracoes/whatsapp"
          element={
            <AdminRoute>
              <ConfigWhatsapp />
            </AdminRoute>
          }
        />
        <Route
          path="configuracoes/empresa-email"
          element={
            <AdminRoute>
              <ConfigEmpresaEmail />
            </AdminRoute>
          }
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
