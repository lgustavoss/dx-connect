import { createElement, useEffect, useRef, type CSSProperties } from 'react'
import { Platform, StyleSheet, View } from 'react-native'
import { useRouter, type Href } from 'expo-router'

import { voltarOuSubstituir } from '../hooks/useGestoVoltar'

const LIMIAR_PX = 64

const estiloWeb: CSSProperties = {
  position: 'absolute',
  left: 0,
  top: 52,
  bottom: 0,
  width: 28,
  zIndex: 40,
  touchAction: 'pan-y',
}

export function FaixaGestoVoltar({ fallback }: { fallback: Href }) {
  const router = useRouter()
  const origemX = useRef<number | null>(null)
  const elRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (Platform.OS !== 'web') return
    const el = elRef.current
    if (!el) return
    let origem: number | null = null
    const down = (e: PointerEvent) => {
      origem = e.clientX
      try {
        el.setPointerCapture(e.pointerId)
      } catch {
        /* captura pode falhar em testes */
      }
    }
    const move = (e: PointerEvent) => {
      if (origem != null && e.clientX - origem >= LIMIAR_PX) {
        origem = null
        voltarOuSubstituir(router, fallback)
      }
    }
    const fim = () => {
      origem = null
    }
    el.addEventListener('pointerdown', down)
    el.addEventListener('pointermove', move)
    el.addEventListener('pointerup', fim)
    el.addEventListener('pointercancel', fim)
    return () => {
      el.removeEventListener('pointerdown', down)
      el.removeEventListener('pointermove', move)
      el.removeEventListener('pointerup', fim)
      el.removeEventListener('pointercancel', fim)
    }
  }, [router, fallback])

  const aoInicio = (x: number) => {
    origemX.current = x
  }
  const aoFim = (x: number) => {
    const inicio = origemX.current
    origemX.current = null
    if (inicio != null && x - inicio >= LIMIAR_PX) voltarOuSubstituir(router, fallback)
  }

  if (Platform.OS === 'web') {
    return createElement('div', {
      'aria-hidden': true,
      style: estiloWeb,
      ref: elRef,
    })
  }

  return (
    <View
      onStartShouldSetResponder={() => true}
      onMoveShouldSetResponder={() => true}
      onResponderGrant={(e) => aoInicio(e.nativeEvent.pageX)}
      onResponderRelease={(e) => aoFim(e.nativeEvent.pageX)}
      onResponderTerminate={() => {
        origemX.current = null
      }}
      style={styles.faixa}
    />
  )
}

const styles = StyleSheet.create({
  faixa: {
    position: 'absolute',
    left: 0,
    top: 52,
    bottom: 0,
    width: 28,
    zIndex: 40,
  },
})
