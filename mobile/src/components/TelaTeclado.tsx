import type { ReactNode } from 'react'
import { KeyboardAvoidingView, Platform, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { useAlturaTeclado } from '../hooks/useAlturaTeclado'

type Props = {
  children: ReactNode
  style?: StyleProp<ViewStyle>
  /** Altura do header fora do SafeArea (iOS), igual ao keyboardVerticalOffset antigo. */
  offset?: number
  /** Cor da faixa que fica entre o conteúdo e o teclado no Android (ex.: fundo do composer). */
  corRodape?: string
  /** Espaço extra entre o conteúdo e o teclado no Android. */
  folga?: number
}

/**
 * Empurra o conteúdo quando o teclado abre.
 *
 * iOS: KeyboardAvoidingView com padding (comportamento que já funcionava).
 * Android: edge-to-edge não redimensiona a janela sozinho, então reservamos um
 * espaço com a altura do teclado no fim da tela — o mesmo efeito do adjustResize.
 */
export function TelaTeclado({ children, style, offset = 0, corRodape, folga = 0 }: Props) {
  const altura = useAlturaTeclado()
  const insets = useSafeAreaInsets()
  const ios = Platform.OS === 'ios'

  // Com o teclado fechado, o Android edge-to-edge deixa o composer embaixo da
  // barra de gestos; reservamos a área segura para o input ficar na mesma
  // altura das outras telas. Com o teclado aberto, o espaço é a altura dele.
  const rodapeAndroid = altura > 0 ? altura + folga : insets.bottom + folga
  const rodapeIos = altura > 0 ? 0 : insets.bottom

  return (
    <KeyboardAvoidingView
      style={[styles.root, style]}
      behavior={ios ? 'padding' : undefined}
      keyboardVerticalOffset={offset}
    >
      <View style={styles.fill}>{children}</View>
      {ios ? (
        rodapeIos > 0 ? <View style={{ height: rodapeIos, backgroundColor: corRodape }} /> : null
      ) : (
        <View style={{ height: rodapeAndroid, backgroundColor: corRodape }} />
      )}
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  fill: { flex: 1 },
})
