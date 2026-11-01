import { Stack } from 'expo-router'

import { BotaoVoltar } from '../components/BotaoVoltar'
import { headerTema } from '../lib/brand'
import { useCores } from '../lib/tema'
import { ChatNovo } from '../screens/ChatNovo'

export default function ChatNovoPage() {
  const cores = useCores()
  return (
    <>
      <Stack.Screen
        options={{
          headerShown: true,
          title: 'Nova conversa',
          headerBackVisible: false,
          gestureEnabled: true,
          fullScreenGestureEnabled: true,
          headerLeft: () => <BotaoVoltar fallback="/chat" />,
          ...headerTema(cores),
        }}
      />
      <ChatNovo />
    </>
  )
}
