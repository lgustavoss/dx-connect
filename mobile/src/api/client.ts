import { Platform } from 'react-native'

import { apiOriginFromSlug, instanceHeaders } from '../lib/instance'
import { storageDelete, storageGet, storageSet } from '../lib/storage'

export const API_VERSION_PREFIX = '/v1'

const KEY_ACCESS = 'access_token'
const KEY_REFRESH = 'refresh_token'
const KEY_SLUG = 'instance_slug'

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(message: string, status: number, body: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

export type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
  must_change_password: boolean
}

export type AtendenteMe = {
  id: number
  email: string
  nome: string
  role: string
  ativo: boolean
  must_change_password: boolean
  setor_ids?: number[]
  permissoes?: string[]
}

function mensagemDeErro(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  return fallback
}

export async function getStoredSlug(): Promise<string | null> {
  return storageGet(KEY_SLUG)
}

export async function persistSlug(slug: string): Promise<void> {
  await storageSet(KEY_SLUG, slug)
}

export async function persistTokens(tokens: TokenResponse): Promise<void> {
  await storageSet(KEY_ACCESS, tokens.access_token)
  await storageSet(KEY_REFRESH, tokens.refresh_token)
}

export async function clearSession(): Promise<void> {
  await storageDelete(KEY_ACCESS)
  await storageDelete(KEY_REFRESH)
}

export async function clearSessionAndSlug(): Promise<void> {
  await clearSession()
  await storageDelete(KEY_SLUG)
}

async function originOrThrow(): Promise<string> {
  const slug = await getStoredSlug()
  if (!slug) throw new ApiError('Sem instância. Faça login de novo.', 0, null)
  return apiOriginFromSlug(slug)
}

let refreshInFlight: Promise<boolean> | null = null

async function tryRefresh(origin: string): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight
  refreshInFlight = (async () => {
    const refresh = await storageGet(KEY_REFRESH)
    if (!refresh) return false
    const slug = (await getStoredSlug()) || ''
    const res = await fetch(`${origin}${API_VERSION_PREFIX}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...instanceHeaders(slug),
      },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!res.ok) {
      await clearSession()
      return false
    }
    const data = (await res.json()) as TokenResponse
    await persistTokens(data)
    return true
  })().finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

async function fetchWebFile(uri: string, name: string, type: string): Promise<File> {
  const res = await fetch(uri)
  const blob = await res.blob()
  return new File([blob], name, { type: type || blob.type || 'application/octet-stream' })
}

function isFormDataBody(body: RequestInit['body']): boolean {
  return typeof FormData !== 'undefined' && body != null && body instanceof FormData
}

async function authorizedFetch(path: string, options: RequestInit = {}, retried = false): Promise<Response> {
  const origin = await originOrThrow()
  const slug = (await getStoredSlug()) || ''
  const token = await storageGet(KEY_ACCESS)
  const form = isFormDataBody(options.body)
  const headers: Record<string, string> = {
    Accept: form ? '*/*' : 'application/json',
    ...(options.body && !form ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...instanceHeaders(slug),
    ...(options.headers as Record<string, string> | undefined),
  }
  const res = await fetch(`${origin}${API_VERSION_PREFIX}${path}`, { ...options, headers })
  if (res.status === 401 && !retried) {
    const ok = await tryRefresh(origin)
    if (ok) return authorizedFetch(path, options, true)
    throw new ApiError('Sessão expirada. Entre de novo.', 401, null)
  }
  return res
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await authorizedFetch(path, options)
  const text = await res.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }
  if (!res.ok) {
    throw new ApiError(mensagemDeErro(body, `Erro HTTP ${res.status}`), res.status, body)
  }
  return body as T
}

export async function apiBlob(path: string): Promise<Blob> {
  const res = await authorizedFetch(path, { headers: { Accept: '*/*' } })
  if (!res.ok) {
    const text = await res.text()
    let body: unknown = text
    try {
      body = JSON.parse(text)
    } catch {
      /* keep text */
    }
    throw new ApiError(mensagemDeErro(body, `Erro HTTP ${res.status}`), res.status, body)
  }
  return res.blob()
}

export async function loginNaInstancia(
  slug: string,
  email: string,
  senha: string,
): Promise<TokenResponse> {
  const origin = apiOriginFromSlug(slug)
  const res = await fetch(`${origin}${API_VERSION_PREFIX}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...instanceHeaders(slug),
    },
    body: JSON.stringify({ email: email.trim().toLowerCase(), senha }),
  })
  const text = await res.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }
  if (!res.ok) {
    throw new ApiError(mensagemDeErro(body, 'E-mail ou senha inválidos'), res.status, body)
  }
  const tokens = body as TokenResponse
  await persistSlug(slug)
  await persistTokens(tokens)
  return tokens
}

export function atendentesMe() {
  return api<AtendenteMe>('/atendentes/me')
}

export const atendentes = {
  trocarSenha: (senhaAtual: string, senhaNova: string) =>
    api<AtendenteMe>('/atendentes/me/trocar-senha', {
      method: 'POST',
      body: JSON.stringify({ senha_atual: senhaAtual, senha_nova: senhaNova }),
    }),
}

export async function getAccessToken(): Promise<string | null> {
  return storageGet(KEY_ACCESS)
}

export async function apiOrigin(): Promise<string> {
  return originOrThrow()
}

export type WhatsappChat = {
  id: number
  protocolo: string
  wa_id: string
  cliente_nome?: string | null
  estado: string
  setor_id?: number | null
  setor_nome?: string | null
  atendente_id?: number | null
  atendente_nome?: string | null
  empresa_id?: number | null
  empresa_nome?: string | null
  funcionario_nome?: string | null
  foto_perfil_url?: string | null
  ticket_ids?: number[]
  nao_lidas_count?: number
  created_at?: string | null
  atendimento_inicio_at?: string | null
}

export type WhatsappMensagem = {
  id: number
  chat_id: number
  direcao: string
  corpo: string
  tipo_midia?: string | null
  midia_disponivel?: boolean
  midia_nome_original?: string | null
  evento_sistema?: string | null
  atendente_nome?: string | null
  created_at?: string | null
  apagada?: boolean
}

export const whatsapp = {
  fila: () => api<WhatsappChat[]>('/whatsapp/chats/fila'),
  meus: () => api<WhatsappChat[]>('/whatsapp/chats/meus'),
  encerrados: (offset = 0, limit = 10) =>
    api<{ items: WhatsappChat[]; total: number }>(
      `/whatsapp/chats/encerrados${qs({ limit, offset })}`,
    ),
  get: (id: number) => api<WhatsappChat>(`/whatsapp/chats/${id}`),
  mensagens: (id: number) => api<WhatsappMensagem[]>(`/whatsapp/chats/${id}/mensagens`),
  assumir: (id: number) => api<WhatsappChat>(`/whatsapp/chats/${id}/assumir`, { method: 'POST' }),
  encerrar: (id: number) => api<WhatsappChat>(`/whatsapp/chats/${id}/encerrar`, { method: 'POST' }),
  enviar: (id: number, texto: string) =>
    api<WhatsappMensagem>(`/whatsapp/chats/${id}/mensagens`, {
      method: 'POST',
      body: JSON.stringify({ texto }),
    }),
  marcarVisto: (id: number) => api<void>(`/whatsapp/chats/${id}/visto`, { method: 'POST' }),
  midiaBlob: (chatId: number, mensagemId: number) =>
    apiBlob(`/whatsapp/chats/${chatId}/mensagens/${mensagemId}/midia`),
  enviarMidia: (id: number, file: { uri: string; name: string; type: string }, caption?: string) => {
    const form = new FormData()
    const nome = file.name.toLowerCase()
    let mediatipo = 'documento'
    if (file.type.startsWith('image/')) mediatipo = 'imagem'
    else if (file.type.startsWith('audio/') || nome.endsWith('.ogg') || nome.endsWith('.m4a') || nome.endsWith('.webm'))
      mediatipo = 'audio'
    else if (file.type.startsWith('video/')) mediatipo = 'video'
    form.append('mediatipo', mediatipo)
    form.append('caption', caption || '')
    if (Platform.OS === 'web') {
      return fetchWebFile(file.uri, file.name, file.type).then((webFile) => {
        form.append('file', webFile)
        return api<WhatsappMensagem>(`/whatsapp/chats/${id}/mensagens/midia`, { method: 'POST', body: form })
      })
    }
    form.append('file', { uri: file.uri, name: file.name, type: file.type } as unknown as Blob)
    return api<WhatsappMensagem>(`/whatsapp/chats/${id}/mensagens/midia`, { method: 'POST', body: form })
  },
  abrirTicket: (
    id: number,
    data: { empresa_id: number; setor_id: number; assunto: string; descricao?: string | null },
  ) =>
    api<WhatsappChat>(`/whatsapp/chats/${id}/abrir-ticket`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  contatos: (busca: string) =>
    api<{ items: WhatsappContato[]; total: number }>(
      `/whatsapp/chats/contatos${qs({ busca, limit: 12, offset: 0 })}`,
    ),
  iniciar: (data: {
    funcionario_id?: number
    telefone?: string
    mensagem_inicial?: string
    empresa_id?: number
    setor_id?: number
  }) =>
    api<WhatsappChat>('/whatsapp/chats/iniciar', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}

export type WhatsappContato = {
  id: number
  nome: string
  email?: string | null
  telefone?: string | null
  tipo: string
  empresas?: { id: number; nome: string }[]
  rede_nome?: string | null
}

export type SetorResumo = { id: number; nome: string; ativo?: boolean }

export const setores = {
  listar: () =>
    api<{ items: SetorResumo[]; total: number }>('/setores?incluir_inativos=false&limit=100&offset=0'),
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined) continue
    p.set(k, String(v))
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

export type Ticket = {
  id: number
  protocolo: string
  assunto: string
  descricao?: string | null
  empresa_id?: number | null
  empresa_nome?: string | null
  setor_id: number
  setor_nome?: string | null
  status_nome?: string | null
  atendente_id?: number | null
  atendente_nome?: string | null
  fechado_em?: string | null
  created_at?: string | null
  fila_desde_at?: string | null
}

export type TicketLista = { items: Ticket[]; total: number }

export type TicketMensagem = {
  id: number
  ticket_id: number
  atendente_id?: number | null
  atendente_nome?: string | null
  autor_externo?: string | null
  tipo: string
  corpo: string
  created_at?: string | null
}

export const tickets = {
  fila: () =>
    api<TicketLista>(
      `/tickets${qs({ situacao: 'abertos', sem_responsavel: true, limit: 50, offset: 0 })}`,
    ),
  meus: () =>
    api<TicketLista>(`/tickets${qs({ situacao: 'abertos', meus: true, limit: 50, offset: 0 })}`),
  get: (id: number) => api<Ticket>(`/tickets/${id}`),
  mensagens: (id: number) => api<TicketMensagem[]>(`/tickets/${id}/mensagens`),
  assumir: (id: number, atendenteId: number) =>
    api<Ticket>(`/tickets/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ atendente_id: atendenteId }),
    }),
  enviar: (id: number, corpo: string, tipo: 'publico' | 'interno') =>
    api<TicketMensagem>(`/tickets/${id}/mensagens`, {
      method: 'POST',
      body: JSON.stringify({ corpo, tipo, notificar_cliente_por_email: false }),
    }),
}

export const dispositivos = {
  registrar: (token: string, plataforma = 'android') =>
    api<{ id: number; token: string; plataforma: string }>('/dispositivos', {
      method: 'POST',
      body: JSON.stringify({ token, plataforma }),
    }),
  apagarPorToken: (token: string) =>
    api<void>(`/dispositivos${qs({ token })}`, { method: 'DELETE' }),
}
