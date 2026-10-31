import { Pressable, StyleSheet, Text, View } from 'react-native'

import { useAuth } from '../../auth/AuthContext'
import { colors } from '../../lib/brand'
import { publicApiOriginFromSlug } from '../../lib/instance'

export default function PerfilScreen() {
  const { me, slug, sair } = useAuth()
  let api = slug
  try {
    api = publicApiOriginFromSlug(slug)
  } catch {
    /* slug ainda vazio */
  }

  return (
    <View style={styles.box}>
      <Text style={styles.titulo}>{me?.nome}</Text>
      <Text style={styles.linha}>{me?.email}</Text>
      <Text style={styles.linha}>Perfil: {me?.role}</Text>
      <Text style={styles.linha}>Instância: {slug}</Text>
      <Text style={styles.api}>{api}</Text>
      <Pressable style={styles.botao} onPress={() => void sair()}>
        <Text style={styles.botaoTxt}>Sair e trocar instância</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  box: { flex: 1, backgroundColor: colors.deck, padding: 24, gap: 8 },
  titulo: { fontSize: 22, fontWeight: '700', color: colors.navy },
  linha: { fontSize: 16, color: colors.navyMid },
  api: { fontSize: 13, color: colors.muted, marginTop: 4 },
  botao: {
    marginTop: 24,
    backgroundColor: colors.navy,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  botaoTxt: { color: colors.white, fontWeight: '700' },
})
