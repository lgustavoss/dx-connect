import { Stack } from 'expo-router'

import { BotaoVoltar } from '../../components/BotaoVoltar'
import { headerTema } from '../../lib/brand'
import { useCores } from '../../lib/tema'
import { TicketDetalhe } from '../../screens/TicketDetalhe'

export default function TicketPage() {
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
          headerLeft: () => <BotaoVoltar fallback="/tickets" />,
          ...headerTema(cores),
        }}
      />
      <TicketDetalhe />
    </>
  )
}
