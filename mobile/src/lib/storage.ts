import { Platform } from 'react-native'
import * as SecureStore from 'expo-secure-store'

export async function storageGet(key: string): Promise<string | null> {
  if (Platform.OS === 'web') {
    try {
      return globalThis.localStorage?.getItem(key) ?? null
    } catch {
      return null
    }
  }
  return SecureStore.getItemAsync(key)
}

export async function storageSet(key: string, value: string): Promise<void> {
  if (Platform.OS === 'web') {
    globalThis.localStorage?.setItem(key, value)
    return
  }
  await SecureStore.setItemAsync(key, value)
}

export async function storageDelete(key: string): Promise<void> {
  if (Platform.OS === 'web') {
    globalThis.localStorage?.removeItem(key)
    return
  }
  await SecureStore.deleteItemAsync(key)
}
