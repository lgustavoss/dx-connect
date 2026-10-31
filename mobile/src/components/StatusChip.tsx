import { StyleSheet, Text, View } from 'react-native'

import { colors, radius } from '../lib/brand'
import { rotuloEstado } from '../lib/format'

export function StatusChip({ estado }: { estado: string }) {
  const fila = estado === 'aguardando_atendente'
  const encerrado = estado === 'encerrado'
  return (
    <View style={[styles.chip, fila && styles.fila, encerrado && styles.encerrado]}>
      <Text style={[styles.txt, fila && styles.txtFila, encerrado && styles.txtEncerrado]}>
        {rotuloEstado(estado)}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.full,
    backgroundColor: colors.tealSoft,
  },
  fila: { backgroundColor: colors.warningBg },
  encerrado: { backgroundColor: '#EEF1F5' },
  txt: { fontSize: 11, fontWeight: '600', color: colors.tealDark },
  txtFila: { color: colors.warning },
  txtEncerrado: { color: colors.muted },
})
