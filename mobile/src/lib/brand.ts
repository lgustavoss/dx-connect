export const APP_NAME = 'DeskRudder'
export const APP_TAGLINE = 'Atendimento no celular'

/** Paleta clara — mesmas superfícies do painel web (slate + branco). */
export const coresClaro = {
  /** Fundo de marca (login, splash) — igual nos dois temas. */
  marca: '#0B2D4A',
  /** Texto/ícone sobre a marca ou sobre a cor de ação — igual nos dois temas. */
  sobre: '#FFFFFF',
  navy: '#0B2D4A',
  navyMid: '#1A4568',
  teal: '#0D9488',
  tealDark: '#0F766E',
  tealSoft: '#E6F6F4',
  deck: '#F3F5F8',
  chatBg: '#E8EEF2',
  /** Superfície de cards, header e menus. */
  white: '#FFFFFF',
  /** Fundo da bolha recebida (precisa contrastar com chatBg). */
  bolhaIn: '#FFFFFF',
  text: '#0F172A',
  muted: '#64748B',
  border: '#E6EAF0',
  danger: '#DC2626',
  dangerBg: '#FEF2F2',
  warning: '#B45309',
  warningBg: '#FFFBEB',
  /** Texto dentro de avisos/notas internas (fundo warningBg). */
  avisoTexto: '#78350F',
}

export type Cores = typeof coresClaro

/** Paleta escura — espelha o esquema do painel web (slate-950/900/800 + cyan). */
export const coresEscuro: Cores = {
  marca: '#0B2D4A',
  sobre: '#FFFFFF',
  navy: '#E2E8F0',
  navyMid: '#CBD5E1',
  teal: '#14B8A6',
  tealDark: '#5EEAD4',
  tealSoft: '#083344',
  deck: '#020617',
  chatBg: '#0B1220',
  white: '#0F172A',
  bolhaIn: '#1E293B',
  text: '#F1F5F9',
  muted: '#94A3B8',
  border: '#1E293B',
  danger: '#F87171',
  dangerBg: '#3F1A1F',
  warning: '#FCD34D',
  warningBg: '#3B2A0A',
  avisoTexto: '#FCD34D',
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

/** Opções de header do Stack (claro ou escuro) a partir da paleta atual. */
export function headerTema(cores: Cores) {
  return {
    headerStyle: { backgroundColor: cores.white },
    headerTintColor: cores.navy,
    headerTitleStyle: { fontWeight: '600' as const, fontSize: 17 },
    headerShadowVisible: false,
  }
}
