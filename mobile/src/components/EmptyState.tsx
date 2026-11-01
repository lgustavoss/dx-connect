import { useMemo } from 'react'
import { StyleSheet, Text, View } from 'react-native'

import { type Cores } from '../lib/brand'
import { useCores } from '../lib/tema'
import { Icon, type IconName } from './Icon'

export function EmptyState({
  icone,
  titulo,
}: {
  icone: IconName
  titulo: string
}) {
  const cores = useCores()
  const styles = useMemo(() => criarEstilos(cores), [cores])
  return (
    <View style={styles.box}>
      <View style={styles.iconeWrap}>
        <Icon name={icone} size={28} color={cores.muted} />
      </View>
      <Text style={styles.txt}>{titulo}</Text>
    </View>
  )
}

function criarEstilos(cores: Cores) {
  return StyleSheet.create({
    box: { alignItems: 'center', paddingHorizontal: 32, paddingTop: 56, gap: 12 },
    iconeWrap: {
      width: 56,
      height: 56,
      borderRadius: 28,
      backgroundColor: cores.white,
      alignItems: 'center',
      justifyContent: 'center',
    },
    txt: { textAlign: 'center', color: cores.muted, fontSize: 15, lineHeight: 22 },
  })
}
