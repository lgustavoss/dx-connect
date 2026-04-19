import type { Tickets } from '../../api/client'

export interface ChatAttachmentMeta {
  id: string
  name: string
  sizeLabel: string
}

export interface ChatIncomingMessage {
  id: string
  body: string
  createdAt: string
  source: 'whatsapp' | 'web' | 'manual'
  attachments: ChatAttachmentMeta[]
}

export interface ChatWorkspaceState {
  customerName: string
  stationName: string
  contactPhone: string
  channel: 'whatsapp' | 'webchat' | 'telefone'
  queueStatus: 'novo' | 'em_atendimento' | 'aguardando_cliente' | 'resolvido'
  priority: 'normal' | 'alta' | 'critica'
  tone: 'acolhedor' | 'consultivo' | 'agil'
  tags: string[]
  notes: string
  linkedTicketId: number | null
  aiEnabled: boolean
  incomingMessages: ChatIncomingMessage[]
}

const STORAGE_PREFIX = 'dx-connect:chat-workspace:'

function normalizeTags(tags: string[]): string[] {
  return [...new Set(tags.map((tag) => tag.trim()).filter(Boolean))]
}

export function defaultChatWorkspace(ticket: Tickets.Ticket): ChatWorkspaceState {
  const statusName = (ticket.status_nome || '').toLowerCase()
  let queueStatus: ChatWorkspaceState['queueStatus'] = 'novo'
  if (statusName.includes('fechado')) queueStatus = 'resolvido'
  else if (statusName.includes('atendimento')) queueStatus = 'em_atendimento'
  else if (statusName.includes('aguardando')) queueStatus = 'aguardando_cliente'

  return {
    customerName: ticket.empresa_nome || 'Cliente da rede',
    stationName: ticket.empresa_nome || 'Posto sem identificacao',
    contactPhone: '',
    channel: 'whatsapp',
    queueStatus,
    priority: 'normal',
    tone: 'consultivo',
    tags: normalizeTags([
      ticket.setor_nome || 'Suporte',
      ticket.rede_nome || '',
    ]),
    notes: '',
    linkedTicketId: ticket.id,
    aiEnabled: true,
    incomingMessages: [],
  }
}

export function loadChatWorkspace(ticket: Tickets.Ticket): ChatWorkspaceState {
  if (typeof window === 'undefined') return defaultChatWorkspace(ticket)
  try {
    const raw = window.localStorage.getItem(`${STORAGE_PREFIX}${ticket.id}`)
    if (!raw) return defaultChatWorkspace(ticket)
    const parsed = JSON.parse(raw) as Partial<ChatWorkspaceState>
    const fallback = defaultChatWorkspace(ticket)
    return {
      ...fallback,
      ...parsed,
      tags: normalizeTags(parsed.tags ?? fallback.tags),
      linkedTicketId: parsed.linkedTicketId ?? ticket.id,
      incomingMessages: Array.isArray(parsed.incomingMessages)
        ? parsed.incomingMessages.map((message) => ({
            id: String(message.id),
            body: String(message.body ?? ''),
            createdAt: String(message.createdAt ?? new Date().toISOString()),
            source:
              message.source === 'web' || message.source === 'manual' || message.source === 'whatsapp'
                ? message.source
                : 'manual',
            attachments: Array.isArray(message.attachments)
              ? message.attachments.map((attachment) => ({
                  id: String(attachment.id),
                  name: String(attachment.name ?? 'Arquivo'),
                  sizeLabel: String(attachment.sizeLabel ?? ''),
                }))
              : [],
          }))
        : fallback.incomingMessages,
    }
  } catch {
    return defaultChatWorkspace(ticket)
  }
}

export function saveChatWorkspace(ticketId: number, state: ChatWorkspaceState) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(`${STORAGE_PREFIX}${ticketId}`, JSON.stringify(state))
}

export function formatFileSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 102.4) / 10} KB`
  return `${Math.round(size / 104857.6) / 10} MB`
}
