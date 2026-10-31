import { useEffect } from 'react'
import { StyleSheet, Text } from 'react-native'

/** Codepoints do Ionicons 5 (mesma fonte em /Ionicons.ttf). */
const GLIFOS: Record<string, number> = {
  add: 61699,
  'add-circle-outline': 61701,
  attach: 61777,
  chatbubbles: 61975,
  'chatbubbles-outline': 61976,
  'chevron-back': 61993,
  'close-circle-outline': 62028,
  'document-outline': 62129,
  'globe-outline': 62288,
  'image-outline': 62351,
  'lock-closed-outline': 62408,
  'log-out-outline': 62417,
  'logo-whatsapp': 62501,
  'person-outline': 62636,
  send: 62821,
  'ticket-outline': 62939,
}

const FONTE_ID = 'ionicons-webfont'

function garantirFonte() {
  if (typeof document === 'undefined') return
  if (document.getElementById(FONTE_ID)) return
  const style = document.createElement('style')
  style.id = FONTE_ID
  style.textContent =
    '@font-face{font-family:Ionicons;font-style:normal;font-weight:normal;src:url("/Ionicons.ttf") format("truetype");}'
  document.head.appendChild(style)
}

export function Icon({
  name,
  size = 22,
  color,
}: {
  name: string
  size?: number
  color: string
}) {
  useEffect(() => {
    garantirFonte()
  }, [])
  const code = GLIFOS[name]
  const glyph = typeof code === 'number' ? String.fromCharCode(code) : '•'
  return (
    <Text
      accessibilityElementsHidden
      importantForAccessibility="no"
      style={[styles.glifo, { fontSize: size, lineHeight: size, color, width: size, height: size }]}
    >
      {glyph}
    </Text>
  )
}

const styles = StyleSheet.create({
  glifo: {
    fontFamily: 'Ionicons',
    textAlign: 'center',
  },
})
