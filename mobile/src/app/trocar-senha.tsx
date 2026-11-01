import { Stack } from 'expo-router'

import { headerTema } from '../lib/brand'
import { useCores } from '../lib/tema'
import { TrocarSenhaScreen } from '../screens/TrocarSenha'

export default function TrocarSenhaPage() {
  const cores = useCores()
  return (
    <>
      <Stack.Screen
        options={{
          headerShown: true,
          title: 'Trocar senha',
          headerBackVisible: false,
          gestureEnabled: false,
          ...headerTema(cores),
        }}
      />
      <TrocarSenhaScreen />
    </>
  )
}
