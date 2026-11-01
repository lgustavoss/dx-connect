import type { ComponentProps } from 'react'
import Ionicons from '@expo/vector-icons/Ionicons'

export type IconName = ComponentProps<typeof Ionicons>['name']

export function Icon({
  name,
  size = 22,
  color,
}: {
  name: IconName
  size?: number
  color: string
}) {
  return <Ionicons name={name} size={size} color={color} />
}
