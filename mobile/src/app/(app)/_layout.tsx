import { Redirect, Tabs } from 'expo-router'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { useAuth } from '../../auth/AuthContext'
import { Icon } from '../../components/Icon'
import { type Cores } from '../../lib/brand'
import { useTema } from '../../lib/tema'

function corAba(color: unknown, cores: Cores) {
  return typeof color === 'string' ? color : cores.muted
}

export default function AppTabs() {
  const { me } = useAuth()
  const { cores } = useTema()
  const insets = useSafeAreaInsets()
  if (!me) return <Redirect href="/" />
  if (me.must_change_password) return <Redirect href="/trocar-senha" />

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: cores.teal,
        tabBarInactiveTintColor: cores.muted,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        tabBarStyle: {
          backgroundColor: cores.white,
          borderTopColor: cores.border,
          height: 62 + insets.bottom,
          paddingTop: 8,
          paddingBottom: insets.bottom + 10,
        },
      }}
    >
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Chat',
          tabBarIcon: ({ color, size }) => (
            <Icon name="chatbubbles" size={size} color={corAba(color, cores)} />
          ),
        }}
      />
      <Tabs.Screen
        name="tickets"
        options={{
          title: 'Tickets',
          tabBarIcon: ({ color, size }) => (
            <Icon name="ticket-outline" size={size} color={corAba(color, cores)} />
          ),
        }}
      />
      <Tabs.Screen
        name="perfil"
        options={{
          title: 'Perfil',
          tabBarIcon: ({ color, size }) => (
            <Icon name="person-outline" size={size} color={corAba(color, cores)} />
          ),
        }}
      />
    </Tabs>
  )
}
