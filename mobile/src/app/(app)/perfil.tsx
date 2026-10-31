import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { useAuth } from '../../auth/AuthContext'
import { Avatar } from '../../components/Avatar'
import { Icon } from '../../components/Icon'
import { colors, radius } from '../../lib/brand'

export default function PerfilScreen() {
  const insets = useSafeAreaInsets()
  const { me, slug, sair } = useAuth()

  const papel =
    me?.role === 'admin' ? 'Administrador' : me?.role === 'atendente' ? 'Atendente' : me?.role || '—'

  return (
    <View style={[styles.box, { paddingTop: Math.max(insets.top, 12) + 8 }]}>
      <View style={styles.card}>
        <Avatar nome={me?.nome || '?'} size={72} />
        <Text style={styles.titulo}>{me?.nome}</Text>
        <Text style={styles.email}>{me?.email}</Text>
        <View style={styles.pills}>
          <View style={styles.pill}>
            <Text style={styles.pillTxt}>{papel}</Text>
          </View>
          <View style={styles.pill}>
            <Text style={styles.pillTxt}>{slug}</Text>
          </View>
        </View>
      </View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Sair e trocar instância"
        style={styles.botao}
        onPress={() => void sair()}
      >
        <Icon name="log-out-outline" size={20} color={colors.danger} />
        <Text style={styles.botaoTxt}>Sair e trocar instância</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  box: { flex: 1, backgroundColor: colors.deck, padding: 20, gap: 16 },
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    paddingVertical: 28,
    paddingHorizontal: 20,
    alignItems: 'center',
    gap: 8,
  },
  titulo: { fontSize: 22, fontWeight: '700', color: colors.navy, marginTop: 8 },
  email: { fontSize: 15, color: colors.muted },
  pills: { flexDirection: 'row', gap: 8, marginTop: 8 },
  pill: {
    backgroundColor: colors.tealSoft,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: radius.full,
  },
  pillTxt: { fontSize: 13, fontWeight: '600', color: colors.tealDark },
  botao: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: colors.white,
    borderRadius: radius.md,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: colors.dangerBg,
  },
  botaoTxt: { color: colors.danger, fontWeight: '700', fontSize: 15 },
})
