import { useState } from 'react'
import { Image, StyleSheet, Text, View } from 'react-native'

import { AVATAR_PALETA, colors } from '../lib/brand'
import { iniciais } from '../lib/format'

function corDoNome(nome: string): string {
  let h = 0
  for (let i = 0; i < nome.length; i += 1) h = (h * 31 + nome.charCodeAt(i)) >>> 0
  return AVATAR_PALETA[h % AVATAR_PALETA.length]
}

export function Avatar({
  nome,
  fotoUrl,
  size = 48,
}: {
  nome: string
  fotoUrl?: string | null
  size?: number
}) {
  const [falhou, setFalhou] = useState(false)
  const bg = corDoNome(nome || '?')
  if (fotoUrl && !falhou) {
    return (
      <Image
        accessibilityLabel={nome}
        source={{ uri: fotoUrl }}
        onError={() => setFalhou(true)}
        style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: colors.border }}
      />
    )
  }
  return (
    <View
      accessibilityLabel={nome}
      style={[
        styles.box,
        { width: size, height: size, borderRadius: size / 2, backgroundColor: bg },
      ]}
    >
      <Text style={[styles.txt, { fontSize: size * 0.34 }]}>{iniciais(nome)}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  box: { alignItems: 'center', justifyContent: 'center' },
  txt: { color: colors.white, fontWeight: '700', letterSpacing: 0.3 },
})
