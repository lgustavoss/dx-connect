import { useMemo } from 'react'
import { StyleSheet, Text, View } from 'react-native'

import { type Cores, radius } from '../lib/brand'
import { rotuloEstado } from '../lib/format'
import { useCores } from '../lib/tema'

export function StatusChip({ estado }: { estado: string }) {
  const cores = useCores()
  const styles = useMemo(() => criarEstilos(cores), [cores])
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

function criarEstilos(cores: Cores) {
  return StyleSheet.create({
    chip: {
      paddingHorizontal: 8,
      paddingVertical: 3,
      borderRadius: radius.full,
      backgroundColor: cores.tealSoft,
    },
    fila: { backgroundColor: cores.warningBg },
    encerrado: { backgroundColor: cores.deck },
    txt: { fontSize: 11, fontWeight: '600', color: cores.tealDark },
    txtFila: { color: cores.warning },
    txtEncerrado: { color: cores.muted },
  })
}
