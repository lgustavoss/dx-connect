import { Redirect, Tabs } from 'expo-router'

import { useAuth } from '../../auth/AuthContext'
import { Icon } from '../../components/Icon'
import { colors } from '../../lib/brand'

function corAba(color: unknown) {
  return typeof color === 'string' ? color : colors.muted
}

export default function AppTabs() {
  const { me } = useAuth()
  if (!me) return <Redirect href="/" />
  if (me.must_change_password) return <Redirect href="/trocar-senha" />

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.teal,
        tabBarInactiveTintColor: colors.muted,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        tabBarStyle: {
          backgroundColor: colors.white,
          borderTopColor: colors.border,
          height: 58,
          paddingTop: 4,
        },
      }}
    >
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Chat',
          tabBarIcon: ({ color, size }) => (
            <Icon name="chatbubbles" size={size} color={corAba(color)} />
          ),
        }}
      />
      <Tabs.Screen
        name="tickets"
        options={{
          title: 'Tickets',
          tabBarIcon: ({ color, size }) => (
            <Icon name="ticket-outline" size={size} color={corAba(color)} />
          ),
        }}
      />
      <Tabs.Screen
        name="perfil"
        options={{
          title: 'Perfil',
          tabBarIcon: ({ color, size }) => (
            <Icon name="person-outline" size={size} color={corAba(color)} />
          ),
        }}
      />
    </Tabs>
  )
}
