import { useEffect } from 'react'

/**
 * Expõe a altura e o offset do visualViewport (teclado virtual) em CSS:
 * `--vv-height`, `--vv-offset-top`, `--vv-keyboard` (1 se teclado aberto).
 * Usado pelo shell e pelo composer do chat (#692 / #751).
 */
export function useVisualViewportCss(): void {
  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return
    const apply = () => {
      const root = document.documentElement
      const height = Math.round(vv.height)
      const offsetTop = Math.round(vv.offsetTop)
      root.style.setProperty('--vv-height', `${height}px`)
      root.style.setProperty('--vv-offset-top', `${offsetTop}px`)
      // Heurística: teclado quando a viewport encolhe face a innerHeight
      const keyboardOpen = window.innerHeight - height > 80 || offsetTop > 0
      root.style.setProperty('--vv-keyboard', keyboardOpen ? '1' : '0')
      root.dataset.vvKeyboard = keyboardOpen ? '1' : '0'
    }
    apply()
    vv.addEventListener('resize', apply)
    vv.addEventListener('scroll', apply)
    window.addEventListener('orientationchange', apply)
    return () => {
      vv.removeEventListener('resize', apply)
      vv.removeEventListener('scroll', apply)
      window.removeEventListener('orientationchange', apply)
      const root = document.documentElement
      root.style.removeProperty('--vv-height')
      root.style.removeProperty('--vv-offset-top')
      root.style.removeProperty('--vv-keyboard')
      delete root.dataset.vvKeyboard
    }
  }, [])
}
