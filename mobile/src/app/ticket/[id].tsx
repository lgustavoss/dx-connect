import { Stack } from 'expo-router'

import { BotaoVoltar } from '../../components/BotaoVoltar'
import { headerClaro } from '../../lib/brand'
import { TicketDetalhe } from '../../screens/TicketDetalhe'

export default function TicketPage() {
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
          ...headerClaro,
        }}
      />
      <TicketDetalhe />
    </>
  )
}
