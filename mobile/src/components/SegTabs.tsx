import { useMemo } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'

import { type Cores, radius } from '../lib/brand'
import { useCores } from '../lib/tema'

export type SegItem = { id: string; titulo: string; badge?: number }

export function SegTabs({
  itens,
  ativo,
  onChange,
}: {
  itens: SegItem[]
  ativo: string
  onChange: (id: string) => void
}) {
  const cores = useCores()
  const styles = useMemo(() => criarEstilos(cores), [cores])
  return (
    <View style={styles.trilha}>
      {itens.map((item) => {
        const on = item.id === ativo
        return (
          <Pressable
            key={item.id}
            accessibilityRole="tab"
            accessibilityState={{ selected: on }}
            onPress={() => onChange(item.id)}
            style={[styles.seg, on && styles.segOn]}
          >
            <Text style={[styles.txt, on && styles.txtOn]} numberOfLines={1}>
              {item.titulo}
            </Text>
            {item.badge ? (
              <View style={[styles.badge, on && styles.badgeOn]}>
                <Text style={[styles.badgeTxt, on && styles.badgeTxtOn]}>{item.badge}</Text>
              </View>
            ) : null}
          </Pressable>
        )
      })}
    </View>
  )
}

function criarEstilos(cores: Cores) {
  return StyleSheet.create({
    trilha: {
      flexDirection: 'row',
      marginHorizontal: 16,
      marginTop: 12,
      marginBottom: 4,
      padding: 4,
      borderRadius: radius.xl,
      backgroundColor: cores.chatBg,
      gap: 4,
    },
    seg: {
      flex: 1,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6,
      paddingVertical: 8,
      borderRadius: radius.lg,
    },
    segOn: { backgroundColor: cores.white },
    txt: { fontSize: 13, fontWeight: '600', color: cores.muted },
    txtOn: { color: cores.navy },
    badge: {
      minWidth: 18,
      height: 18,
      paddingHorizontal: 5,
      borderRadius: 9,
      backgroundColor: cores.border,
      alignItems: 'center',
      justifyContent: 'center',
    },
    badgeOn: { backgroundColor: cores.tealSoft },
    badgeTxt: { fontSize: 11, fontWeight: '700', color: cores.muted },
    badgeTxtOn: { color: cores.tealDark },
  })
}
