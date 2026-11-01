import { Pressable, StyleSheet } from 'react-native'
import { useRouter, type Href } from 'expo-router'

import { voltarOuSubstituir } from '../hooks/useGestoVoltar'
import { useCores } from '../lib/tema'
import { Icon } from './Icon'

export function BotaoVoltar({ fallback }: { fallback: Href }) {
  const router = useRouter()
  const cores = useCores()
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel="Voltar"
      hitSlop={12}
      style={styles.botao}
      onPress={() => voltarOuSubstituir(router, fallback)}
    >
      <Icon name="chevron-back" size={26} color={cores.navy} />
    </Pressable>
  )
}

const styles = StyleSheet.create({
  botao: { paddingVertical: 4, paddingRight: 4, marginLeft: -6 },
})
