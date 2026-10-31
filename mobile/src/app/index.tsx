import { Redirect } from 'expo-router'

import { useAuth } from '../auth/AuthContext'
import { LoginScreen } from '../screens/LoginScreen'

export default function Index() {
  const { me } = useAuth()
  if (me) return <Redirect href="/whatsapp" />
  return <LoginScreen />
}
