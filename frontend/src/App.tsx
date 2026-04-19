import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { AtendimentoChat } from './pages/AtendimentoChat'
import { Tickets } from './pages/Tickets'
import { TicketNovo } from './pages/TicketNovo'
import { TicketDetalhe } from './pages/TicketDetalhe'
import { Redes } from './pages/Redes'
import { RedeDetalhe } from './pages/RedeDetalhe'
import { Empresas } from './pages/Empresas'
import { EmpresaDetalhe } from './pages/EmpresaDetalhe'
import { Setores } from './pages/Setores'
import { Atendentes } from './pages/Atendentes'
import { FuncionariosRede } from './pages/FuncionariosRede'
import { FuncionarioRedeDetalhe } from './pages/FuncionarioRedeDetalhe'
import { StatusTicketPage } from './pages/StatusTicket'
import { Auditoria } from './pages/Auditoria'
import { TiposNegocio } from './pages/TiposNegocio'
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
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="atendimento" element={<AtendimentoChat />} />
        <Route path="alterar-senha" element={<AlterarSenha />} />
        <Route path="tickets" element={<Tickets />} />
        <Route path="tickets/novo" element={<TicketNovo />} />
        <Route path="tickets/:id" element={<TicketDetalhe />} />
        <Route
          path="redes/:id"
          element={
            <AdminRoute>
              <RedeDetalhe />
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
          path="setores"
          element={
            <AdminRoute>
              <Setores />
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
          path="funcionarios-rede"
          element={
            <AdminRoute>
              <FuncionariosRede />
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
          path="tipos-negocio"
          element={
            <AdminRoute>
              <TiposNegocio />
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
