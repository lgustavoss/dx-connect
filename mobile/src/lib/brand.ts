export const APP_NAME = 'DeskRudder'
export const APP_TAGLINE = 'Atendimento no celular'

export const colors = {
  navy: '#0B2D4A',
  navyMid: '#1A4568',
  teal: '#0D9488',
  tealDark: '#0F766E',
  tealSoft: '#E6F6F4',
  deck: '#F3F5F8',
  chatBg: '#E8EEF2',
  text: '#0F172A',
  muted: '#64748B',
  border: '#E6EAF0',
  danger: '#DC2626',
  dangerBg: '#FEF2F2',
  warning: '#B45309',
  warningBg: '#FFFBEB',
  white: '#FFFFFF',
}

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 22,
  full: 999,
}

export const AVATAR_PALETA = [
  '#0B2D4A',
  '#0F766E',
  '#1D4ED8',
  '#6D28D9',
  '#BE185D',
  '#C2410C',
  '#0E7490',
  '#3F6212',
] as const

export const headerClaro = {
  headerStyle: { backgroundColor: colors.white },
  headerTintColor: colors.navy,
  headerTitleStyle: { fontWeight: '600' as const, fontSize: 17 },
  headerShadowVisible: false,
}
