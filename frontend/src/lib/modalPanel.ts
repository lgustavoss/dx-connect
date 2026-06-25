/**
 * Superfícies padrão de modais em overlay.
 * Compacto: max-w-lg (formulários curtos). Largo: max-w-5xl (alinhado ao CadastroFormPageShell).
 * Strings literais completas para o Tailwind JIT incluir as classes.
 */

const MODAL_PANEL_SURFACE =
  'rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-600 dark:bg-slate-900 dark:shadow-2xl dark:ring-1 dark:ring-white/10'

export const MODAL_OVERLAY =
  'fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4'

export const MODAL_PANEL_COMPACT = `w-full max-w-lg p-5 ${MODAL_PANEL_SURFACE}`

export const MODAL_PANEL_SCROLLABLE =
  `max-h-[90vh] w-full max-w-lg overflow-y-auto p-5 ${MODAL_PANEL_SURFACE}`

/** Cabeçalho + corpo scrollável + rodapé opcional (conteúdo extenso, ex. editor KB). */
export const MODAL_PANEL_WIDE_SHELL =
  `flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden ${MODAL_PANEL_SURFACE}`
