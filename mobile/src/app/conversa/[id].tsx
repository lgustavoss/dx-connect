import { Stack } from 'expo-router'

import { BotaoVoltar } from '../../components/BotaoVoltar'
import { headerClaro } from '../../lib/brand'
import { WhatsappConversa } from '../../screens/WhatsappConversa'

export default function ConversaPage() {
  return (
    <>
      <Stack.Screen
        options={{
          headerShown: true,
          title: '',
          headerBackVisible: false,
          gestureEnabled: true,
          fullScreenGestureEnabled: true,
          headerLeft: () => <BotaoVoltar fallback="/chat" />,
          ...headerClaro,
        }}
      />
      <WhatsappConversa />
    </>
  )
}
