const STORAGE_PREFIX = 'chat-interno-scroll-v1'
const NEAR_BOTTOM_PX = 80

export type ChatInternoScrollState = {
  nearBottom: boolean
  anchorMessageId: number | null
  scrollTop: number
}

function storageKey(conversaId: number): string {
  return `${STORAGE_PREFIX}:${conversaId}`
}

export function isNearBottom(el: HTMLElement, threshold = NEAR_BOTTOM_PX): boolean {
  return el.scrollHeight - el.scrollTop - el.clientHeight <= threshold
}

export function findAnchorMessageId(container: HTMLElement): number | null {
  const containerRect = container.getBoundingClientRect()
  const nodes = container.querySelectorAll<HTMLElement>('[data-chat-msg-id]')
  for (const node of nodes) {
    const rect = node.getBoundingClientRect()
    if (rect.bottom > containerRect.top + 12) {
      const id = Number(node.dataset.chatMsgId)
      return Number.isFinite(id) ? id : null
    }
  }
  return null
}

export function saveChatInternoScroll(conversaId: number, container: HTMLElement): void {
  try {
    const state: ChatInternoScrollState = {
      nearBottom: isNearBottom(container),
      anchorMessageId: findAnchorMessageId(container),
      scrollTop: container.scrollTop,
    }
    sessionStorage.setItem(storageKey(conversaId), JSON.stringify(state))
  } catch {
    // sessionStorage indisponível — ignorar
  }
}

export function loadChatInternoScroll(conversaId: number): ChatInternoScrollState | null {
  try {
    const raw = sessionStorage.getItem(storageKey(conversaId))
    if (!raw) return null
    return JSON.parse(raw) as ChatInternoScrollState
  } catch {
    return null
  }
}

export function clearChatInternoScroll(conversaId: number): void {
  try {
    sessionStorage.removeItem(storageKey(conversaId))
  } catch {
    // ignorar
  }
}

export function scrollChatToBottom(container: HTMLElement): void {
  container.scrollTop = container.scrollHeight
}

export function restoreChatInternoScroll(
  conversaId: number,
  container: HTMLElement,
): boolean {
  const saved = loadChatInternoScroll(conversaId)
  if (!saved) {
    scrollChatToBottom(container)
    return true
  }

  if (saved.nearBottom) {
    scrollChatToBottom(container)
    return true
  }

  if (saved.anchorMessageId != null) {
    const anchor = container.querySelector<HTMLElement>(
      `[data-chat-msg-id="${saved.anchorMessageId}"]`,
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
