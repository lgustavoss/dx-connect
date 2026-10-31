import { Stack } from 'expo-router'

import { WhatsappConversa } from '../../screens/WhatsappConversa'
import { colors } from '../../lib/brand'

export default function ConversaPage() {
  return (
    <>
      <Stack.Screen
        options={{
          headerShown: true,
          title: 'Conversa',
          headerBackTitle: 'WhatsApp',
          headerStyle: { backgroundColor: colors.navy },
          headerTintColor: colors.white,
          headerTitleStyle: { fontWeight: '700' },
        }}
      />
      <WhatsappConversa />
    </>
  )
}
