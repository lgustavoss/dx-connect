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
  encerrados: () =>
    api<{ items: WhatsappChat[]; total: number }>('/whatsapp/chats/encerrados?limit=30&offset=0'),
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
}
