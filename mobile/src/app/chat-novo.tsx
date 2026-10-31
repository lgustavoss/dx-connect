import { Stack } from 'expo-router'

import { BotaoVoltar } from '../components/BotaoVoltar'
import { headerClaro } from '../lib/brand'
import { ChatNovo } from '../screens/ChatNovo'

export default function ChatNovoPage() {
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
          ...headerClaro,
        }}
      />
      <ChatNovo />
    </>
  )
}
