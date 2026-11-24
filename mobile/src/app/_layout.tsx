import { router, Stack, usePathname } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect } from 'react'
import { ActivityIndicator, LogBox, View } from 'react-native'

import { AuthProvider, useAuth } from '../auth/AuthContext'
import { escutarAberturaNotificacao, instalarHandlerNotificacao } from '../lib/push'
import { RealtimeProvider } from '../lib/realtime'
import { TemaProvider, useTema } from '../lib/tema'

// Mídia do chat usa `response.arrayBuffer()` (sem blob: no nativo). Ainda
// escondemos a tarja "Open debugger to view warnings" do DevTools no Expo.
LogBox.ignoreLogs(['Open debugger to view warnings.'])

instalarHandlerNotificacao()

function RootNav() {
  const { ready, me } = useAuth()
  const { cores, tema } = useTema()
  const pathname = usePathname()
  useEffect(() => escutarAberturaNotificacao(), [])

  const precisaTrocarSenha = Boolean(me?.must_change_password)
  useEffect(() => {
    // Bloqueia qualquer rota (inclusive deep link de notificação) até a senha ser trocada.
    if (!precisaTrocarSenha) return
    if (pathname === '/' || pathname === '/trocar-senha') return
    router.replace('/trocar-senha')
  }, [precisaTrocarSenha, pathname])

  if (!ready) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: cores.marca }}>
        <ActivityIndicator color={cores.sobre} />
      </View>
    )
  }
  return (
    <>
      <StatusBar style={tema === 'dark' || !me ? 'light' : 'dark'} />
      <RealtimeProvider ativo={Boolean(me)}>
        <Stack
          screenOptions={{
            headerShown: false,
            animation: 'slide_from_right',
            gestureEnabled: true,
            fullScreenGestureEnabled: true,
          }}
        />
      </RealtimeProvider>
    </>
  )
}

export default function RootLayout() {
  return (
    <TemaProvider>
      <AuthProvider>
        <RootNav />
      </AuthProvider>
    </TemaProvider>
  )
}
