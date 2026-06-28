/** Identidade visual DeskRudder — fonte única para nome, cores e copy de marca. */
export const APP_NAME = 'DeskRudder'
export const APP_NAME_HTML = 'DeskRudder'

/** Tagline curta (login, marketing interno). */
export const APP_TAGLINE = 'Organize. Foque. Direcione'

/** Descrição em uma linha (meta, sobre). */
export const APP_DESCRIPTION =
  'Plataforma de atendimento multicanal — tickets, WhatsApp e e-mail com fila, roteamento e SLA.'

export const brandColors = {
  /** Profundidade / confiança — fundos escuros, gradientes. */
  navy: '#0B2D4A',
  navyMid: '#134166',
  /** Ação primária — botões, links, destaques. */
  teal: '#0D9488',
  tealLight: '#14B8A6',
  tealDark: '#0F766E',
  /** Extremo do gradiente (mar aberto). */
  sky: '#0284C7',
  /** Detalhe do leme (uso pontual no ícone). */
  brass: '#C9973A',
  /** Superfícies do tema escuro (app — espelha index.css @theme). */
  deep: '#071826',
  panel: '#0A1628',
  surface: '#0E2438',
  surfaceElevated: '#112D45',
  border: '#1A4568',
  /** Superfícies claras. */
  deck: '#F8FAFC',
  ink: '#0F172A',
} as const

/** Superfícies do tema claro (app). */
export const brandLightSurfaces = {
  bg: '#F8FAFC',
  bgSubtle: '#F1F5F9',
  surface: '#FFFFFF',
  border: '#E2E8F0',
  text: '#0F172A',
  muted: '#64748B',
  navActive: '#F0FDFA',
} as const

/** Wordmark no tema escuro (BrandLogo markVariant onDark). */
export const brandWordmarkOnDark = {
  desk: '#F1F5F9',
  rudder: '#38BDF8',
} as const

export const brandGradients = {
  /** Gradiente do monograma oficial (referencia). */
  mark: `linear-gradient(135deg, ${brandColors.navy} 0%, ${brandColors.sky} 100%)`,
  primary: `linear-gradient(135deg, ${brandColors.navy} 0%, ${brandColors.sky} 100%)`,
  primaryHorizontal: `linear-gradient(90deg, ${brandColors.navy} 0%, ${brandColors.sky} 100%)`,
  wordmark: `linear-gradient(90deg, ${brandColors.navy} 0%, ${brandColors.sky} 100%)`,
  panel: `linear-gradient(165deg, ${brandColors.navy} 0%, ${brandColors.navyMid} 45%, #0a4d6e 100%)`,
} as const

/** Versão de cache bust para PNGs de marca em public/. */
export const BRAND_ASSET_VERSION = '22'

/** Assets estaticos em public/ (logo v2 — agente 3D no D). */
export const brandAssets = {
  version: BRAND_ASSET_VERSION,
  mark: '/deskrudder-mark.png',
  markAlpha: '/deskrudder-mark-alpha.png',
  mark32: '/deskrudder-mark-32.png',
  logoRefV2: '/deskrudder-logo-ref-v2-black.png',
  logoName: '/deskrudder-logo-name.png',
  lockup: '/deskrudder-lockup.png',
  loginPanel: '/deskrudder-login-panel.png',
  /** Painel plexus à esquerda no login desktop (fundo original). */
  loginPlexusPanel: '/duplexsoft-brand-panel.png',
} as const

/** Chaves de persistência local (com fallback legado DX Connect). */
export const THEME_STORAGE_KEY = 'deskrudder-theme'
export const THEME_STORAGE_KEY_LEGACY = 'dx-connect-theme'
export const LOGIN_EMAIL_STORAGE_KEY = 'deskrudder-login-email'
export const LOGIN_EMAIL_STORAGE_KEY_LEGACY = 'dx-connect-login-email'
