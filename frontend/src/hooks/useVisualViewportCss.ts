import { useEffect } from 'react'

/**
 * Expõe a altura visível real (teclado virtual no iOS/Android) em `--vv-height`.
 * Usado pelo shell `h-dvh` para o compositor não ficar atrás do teclado (#692).
 */
export function useVisualViewportCss(): void {
  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return
    const apply = () => {
      document.documentElement.style.setProperty('--vv-height', `${Math.round(vv.height)}px`)
    }
    apply()
    vv.addEventListener('resize', apply)
    vv.addEventListener('scroll', apply)
    return () => {
      vv.removeEventListener('resize', apply)
      vv.removeEventListener('scroll', apply)
      document.documentElement.style.removeProperty('--vv-height')
    }
  }, [])
}
