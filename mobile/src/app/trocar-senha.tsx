import { Stack } from 'expo-router'

import { headerClaro } from '../lib/brand'
import { TrocarSenhaScreen } from '../screens/TrocarSenha'

export default function TrocarSenhaPage() {
  return (
    <>
      <Stack.Screen
        options={{
          headerShown: true,
          title: 'Trocar senha',
          headerBackVisible: false,
          gestureEnabled: false,
          ...headerClaro,
        }}
      />
      <TrocarSenhaScreen />
    </>
  )
}
