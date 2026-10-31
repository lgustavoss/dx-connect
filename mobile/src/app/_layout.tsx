import { router, Stack, usePathname } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect } from 'react'
import { ActivityIndicator, View } from 'react-native'

import { AuthProvider, useAuth } from '../auth/AuthContext'
import { colors } from '../lib/brand'
import { escutarAberturaNotificacao, instalarHandlerNotificacao } from '../lib/push'

instalarHandlerNotificacao()

function RootNav() {
  const { ready, me } = useAuth()
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
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.navy }}>
        <ActivityIndicator color={colors.white} />
      </View>
    )
  }
  return (
    <>
      <StatusBar style={me ? 'dark' : 'light'} />
      <Stack
        screenOptions={{
          headerShown: false,
          animation: 'slide_from_right',
          gestureEnabled: true,
          fullScreenGestureEnabled: true,
        }}
      />
    </>
  )
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <RootNav />
    </AuthProvider>
  )
}
