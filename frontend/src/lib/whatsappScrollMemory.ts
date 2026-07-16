/** Memória de scroll do WhatsApp — espelha o padrão do chat interno. */

const STORAGE_PREFIX = 'whatsapp-scroll-v1'
const NEAR_BOTTOM_PX = 80

export type WhatsappScrollState = {
  nearBottom: boolean
  anchorMessageId: number | null
  scrollTop: number
}

function storageKey(chatId: number): string {
  return `${STORAGE_PREFIX}:${chatId}`
}

export function isNearBottom(el: HTMLElement, threshold = NEAR_BOTTOM_PX): boolean {
  return el.scrollHeight - el.scrollTop - el.clientHeight <= threshold
}

export function findWhatsappAnchorMessageId(container: HTMLElement): number | null {
  const containerRect = container.getBoundingClientRect()
  const nodes = container.querySelectorAll<HTMLElement>('[data-wa-msg-id]')
  for (const node of nodes) {
    const rect = node.getBoundingClientRect()
    if (rect.bottom > containerRect.top + 12) {
      const id = Number(node.dataset.waMsgId)
      return Number.isFinite(id) ? id : null
    }
  }
  return null
}

export function saveWhatsappScroll(chatId: number, container: HTMLElement): void {
  try {
    const state: WhatsappScrollState = {
      nearBottom: isNearBottom(container),
      anchorMessageId: findWhatsappAnchorMessageId(container),
      scrollTop: container.scrollTop,
    }
    sessionStorage.setItem(storageKey(chatId), JSON.stringify(state))
  } catch {
    // sessionStorage indisponível
  }
}

export function loadWhatsappScroll(chatId: number): WhatsappScrollState | null {
  try {
    const raw = sessionStorage.getItem(storageKey(chatId))
    if (!raw) return null
    return JSON.parse(raw) as WhatsappScrollState
  } catch {
    return null
  }
}

export function scrollWhatsappToBottom(container: HTMLElement): void {
  container.scrollTop = container.scrollHeight
}

/** Restaura posição; devolve se ficou “colado” no fim. */
export function restoreWhatsappScroll(chatId: number, container: HTMLElement): boolean {
  const saved = loadWhatsappScroll(chatId)
  if (!saved) {
    scrollWhatsappToBottom(container)
    return true
  }

  if (saved.nearBottom) {
    scrollWhatsappToBottom(container)
    return true
  }

  if (saved.anchorMessageId != null) {
    const anchor = container.querySelector<HTMLElement>(
      `[data-wa-msg-id="${saved.anchorMessageId}"]`,
    )
    if (anchor) {
      anchor.scrollIntoView({ block: 'start' })
      return false
    }
  }

  container.scrollTop = saved.scrollTop
  return false
}

export function preserveScrollOnContentChange(
  container: HTMLElement,
  prevScrollTop: number,
  prevScrollHeight: number,
): void {
  const delta = container.scrollHeight - prevScrollHeight
  container.scrollTop = prevScrollTop + delta
}
