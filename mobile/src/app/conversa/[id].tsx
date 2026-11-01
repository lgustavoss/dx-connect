import { Stack } from 'expo-router'

import { BotaoVoltar } from '../../components/BotaoVoltar'
import { headerTema } from '../../lib/brand'
import { useCores } from '../../lib/tema'
import { WhatsappConversa } from '../../screens/WhatsappConversa'

export default function ConversaPage() {
  const cores = useCores()
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
          ...headerTema(cores),
        }}
      />
      <WhatsappConversa />
    </>
  )
}
