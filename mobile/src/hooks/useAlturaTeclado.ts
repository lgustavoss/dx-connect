import { useEffect, useState } from 'react'
import { Dimensions, Keyboard, Platform } from 'react-native'

/**
 * Altura do teclado no Android (0 quando fechado).
 *
 * No Android com edge-to-edge (padrão no Expo SDK 54+) a janela não encolhe
 * quando o teclado abre, então a tela precisa empurrar o conteúdo para cima.
 * Se a janela encolheu de fato (adjustResize de Android antigo), devolve 0 para
 * não deslocar o conteúdo duas vezes.
 */
export function useAlturaTeclado(): number {
  const [altura, setAltura] = useState(0)

  useEffect(() => {
    if (Platform.OS !== 'android') return

    const aoMostrar = Keyboard.addListener('keyboardDidShow', (evento) => {
      const teclado = evento.endCoordinates?.height ?? 0
      const janelaEncolheu =
        Dimensions.get('screen').height - Dimensions.get('window').height > teclado * 0.5
      setAltura(janelaEncolheu ? 0 : teclado)
    })
    const aoEsconder = Keyboard.addListener('keyboardDidHide', () => setAltura(0))

    return () => {
      aoMostrar.remove()
      aoEsconder.remove()
    }
  }, [])

  return altura
}
