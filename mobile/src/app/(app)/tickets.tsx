import { StyleSheet, Text, View } from 'react-native'

import { colors } from '../../lib/brand'

export default function TicketsPlaceholder() {
  return (
    <View style={styles.box}>
      <Text style={styles.titulo}>Tickets</Text>
      <Text style={styles.corpo}>
        Inbox de tickets em breve: fila, seus chamados e a conversa de cada um.
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  box: { flex: 1, backgroundColor: colors.deck, padding: 24, gap: 8 },
  titulo: { fontSize: 22, fontWeight: '700', color: colors.navy },
  corpo: { fontSize: 16, color: colors.muted, lineHeight: 22 },
})
