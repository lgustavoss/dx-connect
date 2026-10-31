import { Redirect, Tabs } from 'expo-router'

import { useAuth } from '../../auth/AuthContext'
import { colors } from '../../lib/brand'

export default function AppTabs() {
  const { me } = useAuth()
  if (!me) return <Redirect href="/" />

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.navy },
        headerTintColor: colors.white,
        tabBarActiveTintColor: colors.teal,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: { backgroundColor: colors.white },
      }}
    >
      <Tabs.Screen name="whatsapp" options={{ title: 'WhatsApp' }} />
      <Tabs.Screen name="tickets" options={{ title: 'Tickets' }} />
      <Tabs.Screen name="perfil" options={{ title: 'Perfil' }} />
    </Tabs>
  )
}
