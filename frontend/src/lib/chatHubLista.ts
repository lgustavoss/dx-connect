import type { PortalChats, WhatsappChats } from '../api/client'
import { chatHubPathParaModo, type ChatHubModo } from './chatHubPaths'
import { rotuloResponsavelChat } from './whatsappChatMeta'

export type ChatHubCanal = 'whatsapp' | 'portal'

export type ChatHubItem = {
  canal: ChatHubCanal
  id: number
  protocolo: string
  nome: string
  subtitulo?: string | null
  setor_nome?: string | null
  created_at?: string | null
  atendimento_inicio_at?: string | null
  estado: string
  atendente_id?: number | null
  atendente_nome?: string | null
  ultima_mensagem_preview?: string | null
  foto_perfil_url?: string | null
  nao_lidas_count?: number
}

export function mapWhatsappChat(c: WhatsappChats.Chat): ChatHubItem {
  return {
    canal: 'whatsapp',
    id: c.id,
    protocolo: c.protocolo,
    nome: c.cliente_nome || 'Cliente',
    subtitulo: c.wa_id,
    setor_nome: c.setor_nome,
    created_at: c.created_at,
    atendimento_inicio_at: c.atendimento_inicio_at,
    estado: c.estado,
    atendente_id: c.atendente_id,
    atendente_nome: c.atendente_nome,
    foto_perfil_url: c.foto_perfil_url,
    nao_lidas_count: c.nao_lidas_count ?? 0,
  }
}

export function mapPortalChat(c: PortalChats.Chat): ChatHubItem {
  return {
    canal: 'portal',
    id: c.id,
    protocolo: c.protocolo,
    nome: c.visitante_nome,
    subtitulo: c.visitante_email,
    setor_nome: c.setor_nome,
    created_at: c.created_at,
    atendimento_inicio_at: c.atendimento_inicio_at,
    estado: c.estado,
    atendente_id: c.atendente_id,
    atendente_nome: c.atendente_nome,
    ultima_mensagem_preview: c.ultima_mensagem_preview,
    nao_lidas_count: c.nao_lidas_count ?? 0,
  }
}

/** Só o path da aba — gravar chat ativo no onClick via `abrirChat` (#654). */
export function chatHubItemLink(from?: ChatHubModo) {
  const modo: ChatHubModo =
    from === 'espera' ? 'espera' : from === 'contatos' ? 'contatos' : 'atendendo'
  return { pathname: chatHubPathParaModo(modo), search: '' }
}

export function chatHubItemKey(item: ChatHubItem) {
  return `${item.canal}-${item.id}`
}

export function filtrarChatHubPorBusca(items: ChatHubItem[], busca: string): ChatHubItem[] {
  const q = busca.trim().toLowerCase()
  if (!q) return items
  return items.filter((c) => {
    const nome = c.nome.toLowerCase()
    const sub = (c.subtitulo || '').toLowerCase()
    const proto = c.protocolo.toLowerCase()
    const canal = c.canal === 'portal' ? 'portal' : 'whatsapp'
    return nome.includes(q) || sub.includes(q) || proto.includes(q) || canal.includes(q)
  })
}

export function ordenarFila(items: ChatHubItem[]): ChatHubItem[] {
  return [...items].sort((a, b) => {
    const ta = a.created_at ? new Date(a.created_at).getTime() : 0
    const tb = b.created_at ? new Date(b.created_at).getTime() : 0
    return ta - tb
  })
}

export function ordenarAtendendo(items: ChatHubItem[]): ChatHubItem[] {
  return [...items].sort((a, b) => {
    const ua = a.nao_lidas_count ?? 0
    const ub = b.nao_lidas_count ?? 0
    if (ub !== ua) return ub - ua
    const ta = a.atendimento_inicio_at || a.created_at
    const tb = b.atendimento_inicio_at || b.created_at
    return (tb ? new Date(tb).getTime() : 0) - (ta ? new Date(ta).getTime() : 0)
  })
}

export type AtendendoSecoes = {
  comigo: ChatHubItem[]
  outros: ChatHubItem[]
  /** Secções com cabeçalho quando há chats de outros atendentes */
  mostrarSecoes: boolean
}

export function separarAtendendoPorResponsavel(
  items: ChatHubItem[],
  usuarioId?: number | null,
): AtendendoSecoes {
  if (usuarioId == null) {
    return { comigo: ordenarAtendendo(items), outros: [], mostrarSecoes: false }
  }

  const comigo: ChatHubItem[] = []
  const outros: ChatHubItem[] = []
  for (const item of items) {
    if (item.atendente_id === usuarioId) comigo.push(item)
    else outros.push(item)
  }

  return {
    comigo: ordenarAtendendo(comigo),
    outros: ordenarAtendendo(outros),
    mostrarSecoes: outros.length > 0,
  }
}

export function rotuloResponsavelItem(item: ChatHubItem, usuarioId?: number | null): string {
  return rotuloResponsavelChat(item, usuarioId)
}
