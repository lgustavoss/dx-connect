import { useRouter, type Href } from 'expo-router'

export function voltarOuSubstituir(router: ReturnType<typeof useRouter>, fallback: Href) {
  if (router.canGoBack()) router.back()
  else router.replace(fallback)
}
