import { StyleSheet, Text, View } from 'react-native'

import { colors } from '../lib/brand'
import { Icon, type IconName } from './Icon'

export function EmptyState({
  icone,
  titulo,
}: {
  icone: IconName
  titulo: string
}) {
  return (
    <View style={styles.box}>
      <View style={styles.iconeWrap}>
        <Icon name={icone} size={28} color={colors.muted} />
      </View>
      <Text style={styles.txt}>{titulo}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  box: { alignItems: 'center', paddingHorizontal: 32, paddingTop: 56, gap: 12 },
  iconeWrap: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.white,
    alignItems: 'center',
    justifyContent: 'center',
  },
  txt: { textAlign: 'center', color: colors.muted, fontSize: 15, lineHeight: 22 },
})
