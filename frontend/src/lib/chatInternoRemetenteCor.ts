/** Cores estáveis por atendente_id — diferencia remetentes em grupos. */

const NOME_CLASSES = [
  'text-violet-600 dark:text-violet-300',
  'text-emerald-600 dark:text-emerald-300',
  'text-orange-600 dark:text-orange-300',
  'text-rose-600 dark:text-rose-300',
  'text-sky-600 dark:text-sky-300',
  'text-amber-700 dark:text-amber-300',
  'text-fuchsia-600 dark:text-fuchsia-300',
  'text-teal-600 dark:text-teal-300',
] as const

const AVATAR_CLASSES = [
  'bg-violet-500/90',
  'bg-emerald-500/90',
  'bg-orange-500/90',
  'bg-rose-500/90',
  'bg-sky-500/90',
  'bg-amber-500/90',
  'bg-fuchsia-500/90',
  'bg-teal-500/90',
] as const

function indiceCor(atendenteId: number): number {
  return Math.abs(atendenteId) % NOME_CLASSES.length
}

export function corNomeRemetenteChat(atendenteId: number): string {
  return NOME_CLASSES[indiceCor(atendenteId)]
}

export function corAvatarRemetenteChat(atendenteId: number): string {
  return AVATAR_CLASSES[indiceCor(atendenteId)]
}

export function inicialNomeRemetente(nome: string | null | undefined): string {
  const t = (nome ?? '').trim()
  if (!t) return '?'
  return t.charAt(0).toUpperCase()
}
