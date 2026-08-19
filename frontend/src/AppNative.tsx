import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams, useLocation } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { ToastProvider } from './components/ui/Toast'
import { ErrorBoundary } from './components/ErrorBoundary'
import { PageLoading } from './components/ui/PageLoading'
import { gravarChatAtivoSession, type ChatAtivoCanal } from './lib/chatAtivo'
import { chatHubModoDePath, chatHubPathParaModo } from './lib/chatHubPaths'
import { gravarTicketAtivoSession } from './lib/ticketAtivo'

const EsqueciSenha = lazy(() => import('./pages/EsqueciSenha').then((m) => ({ default: m.EsqueciSenha })))
const RedefinirSenha = lazy(() => import('./pages/RedefinirSenha').then((m) => ({ default: m.RedefinirSenha })))
const AlterarSenha = lazy(() => import('./pages/AlterarSenha').then((m) => ({ default: m.AlterarSenha })))
const NotificacoesPreferencias = lazy(() =>
  import('./pages/NotificacoesPreferencias').then((m) => ({ default: m.NotificacoesPreferencias })),
)
const Tickets = lazy(() => import('./pages/Tickets').then((m) => ({ default: m.Tickets })))
const TicketNovo = lazy(() => import('./pages/TicketNovo').then((m) => ({ default: m.TicketNovo })))
const ChatHubShell = lazy(() => import('./pages/chat/ChatHubShell').then((m) => ({ default: m.ChatHubShell })))
const ChatHubLayout = lazy(() => import('./pages/chat/ChatHubLayout').then((m) => ({ default: m.ChatHubLayout })))
const ChatHubPainel = lazy(() => import('./pages/chat/ChatHubPainel').then((m) => ({ default: m.ChatHubPainel })))
const ChatHubPlaceholder = lazy(() =>
  import('./pages/chat/ChatHubPlaceholder').then((m) => ({ default: m.ChatHubPlaceholder })),
)
const ChatInternoSetorCanal = lazy(() =>
  import('./pages/chat-interno/ChatInternoSetorCanal').then((m) => ({ default: m.ChatInternoSetorCanal })),
)
const WhatsappLayout = lazy(() => import('./pages/whatsapp/WhatsappLayout').then((m) => ({ default: m.WhatsappLayout })))
const WhatsappHistorico = lazy(() =>
  import('./pages/whatsapp/WhatsappHistorico').then((m) => ({ default: m.WhatsappHistorico })),
)

function LayoutNative() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) {
    return <PageLoading fullscreen label="Carregando sessão…" />
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return <Layout />
}

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

function RedirectTicketDetalhe() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const ticketId = Number(id)
  if (Number.isFinite(ticketId) && ticketId > 0) {
    gravarTicketAtivoSession(ticketId)
  }
  return <Navigate to="/tickets" replace state={location.state} />
}

function RedirectLegacyChatInterno() {
  const location = useLocation()
  const path = location.pathname.replace(/^\/chat-interno/, '/chat/interno')
  return <Navigate to={`${path}${location.search}${location.hash}`} replace />
}

function NativeRoutes() {
  return (
    <Suspense fallback={<PageLoading fullscreen label="Carregando…" />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/esqueci-senha" element={<EsqueciSenha />} />
        <Route path="/redefinir-senha" element={<RedefinirSenha />} />
        <Route path="/" element={<LayoutNative />}>
          <Route index element={<Navigate to="/chat/atendendo" replace />} />
          <Route path="alterar-senha" element={<AlterarSenha />} />
          <Route path="notificacoes/preferencias" element={<NotificacoesPreferencias />} />
          <Route path="tickets" element={<Tickets />} />
          <Route path="tickets/novo" element={<TicketNovo />} />
          <Route path="tickets/:id" element={<RedirectTicketDetalhe />} />
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
                        subtitulo="Escolha um contacto ou número avulso para iniciar conversa no WhatsApp."
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
            <Route path="historico" element={<WhatsappHistorico />} />
            <Route path="fila" element={<Navigate to="/chat/espera" replace />} />
            <Route path="meus" element={<Navigate to="/chat/atendendo" replace />} />
            <Route path="c/:chatId" element={<RedirectChatConversa canal="whatsapp" />} />
          </Route>
          <Route path="chat-interno/*" element={<RedirectLegacyChatInterno />} />
        </Route>
        <Route path="*" element={<Navigate to="/chat/atendendo" replace />} />
      </Routes>
    </Suspense>
  )
}

/** Shell Capacitor: tickets + chat, sem landing/SaaS/cadastros (#735 / #736). */
export default function AppNative() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ThemeProvider>
          <AuthProvider>
            <ToastProvider>
              <NativeRoutes />
            </ToastProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
