import { mensagemErroApi } from './errorMessage'
import { isCapacitorNative } from '../lib/capacitorNative'
import { clientApiOrigin, readRememberedAccount } from '../lib/marketingHost'
import { isMultiTenantMode, resolveTenantIdFromHostname } from '../lib/tenant'

function bakedApiUrl(): string | undefined {
  const url = import.meta.env.VITE_API_URL as string | undefined
  return url?.trim() || undefined
}

function apiBaseUrl(): string {
  if (isCapacitorNative()) {
    // APK debug com VITE_API_URL (emulador/LAN) fala com essa API; o slug só escolhe a instância no APK de loja.
    const baked = bakedApiUrl()
    if (baked) return baked.replace(/\/+$/, '')
    const slug = readRememberedAccount()
    if (slug) {
      try {
        return clientApiOrigin(slug)
      } catch {
        /* slug inválido no storage */
      }
    }
    // Vazio de propósito: api()/SSE recusam pedidos — evita fetch relativo a https://localhost.
    return ''
  }
  if (import.meta.env.DEV) return '/api'
  const url = bakedApiUrl()
  if (!url) {
    throw new Error('VITE_API_URL não definido — o build de produção deveria ter falhado no vite.config.')
  }
  return url.replace(/\/+$/, '')
}

/** Capacitor: há alvo de API (slug gravado ou VITE_API_URL de debug). */
export function hasNativeApiTarget(): boolean {
  if (!isCapacitorNative()) return true
  return Boolean(apiBaseUrl())
}

function apiOrigin(): string {
  return apiBaseUrl()
}

/** Prefixo de versão da API (ex.: dev: `/api` + `/v1` + `/auth/login` → `/v1/auth/login` no backend). */
export const API_VERSION_PREFIX = '/v1'

/** URL base da API (sem barra final). Útil para montar URLs mostradas ao administrador (ex.: webhook). */
export function resolvedApiBaseUrl(): string {
  return apiBaseUrl()
}

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

const TOKEN_KEY = 'token'
const REFRESH_TOKEN_KEY = 'refresh_token'

function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
}

function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY) || localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function getAuthToken(): string | null {
  return getToken();
}

export function clearAuthToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

/** Invalida sessão e força novo login (evita voltar com «Back» para páginas autenticadas). */
export function invalidateSessionAndRedirectToLogin(): void {
  clearAuthToken()
  const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`
  const qs = returnTo && returnTo !== '/login' ? `?returnTo=${encodeURIComponent(returnTo)}` : ''
  window.location.replace(`/login${qs}`)
}

function setTokens(tokens: { access_token: string; refresh_token?: string | null }, lembrarMe = true) {
  const store = lembrarMe ? localStorage : sessionStorage
  store.setItem(TOKEN_KEY, tokens.access_token)
  if (tokens.refresh_token) store.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
}

let refreshInFlight: Promise<{ access_token: string; refresh_token?: string | null; must_change_password?: boolean } | null> | null =
  null

async function refreshAccessToken(): Promise<{ access_token: string; refresh_token?: string | null; must_change_password?: boolean } | null> {
  if (refreshInFlight) return refreshInFlight
  const refresh_token = getRefreshToken()
  if (!refresh_token) return null
  refreshInFlight = (async () => {
    try {
      const res = await api<{ access_token: string; refresh_token?: string | null; must_change_password?: boolean }>(
        '/auth/refresh',
        {
          method: 'POST',
          body: JSON.stringify({ refresh_token }),
          // evita loop: api() trata 401, então no refresh não podemos cair no retry.
          headers: { 'X-DX-Skip-Refresh': '1' },
        },
      )
      // persiste sempre no mesmo storage onde já estava o refresh
      const lembrarMe = Boolean(localStorage.getItem(REFRESH_TOKEN_KEY))
      setTokens(res, lembrarMe)
      return res
    } catch {
      return null
    } finally {
      refreshInFlight = null
    }
  })()
  return refreshInFlight
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  if (!apiOrigin()) {
    throw new ApiError('Informe a conta da empresa para ligar ao painel.', 0, null)
  }
  const token = getToken();
  const isFormData =
    typeof FormData !== 'undefined' && options.body != null && options.body instanceof FormData
  const headers: HeadersInit = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers as object),
  }
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  if (isMultiTenantMode()) {
    ;(headers as Record<string, string>)['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
  }
  let res: Response
  try {
    res = await fetch(`${apiOrigin()}${API_VERSION_PREFIX}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(
      'Não foi possível contactar o painel desta conta. Verifique o identificador ou a ligação à internet.',
      0,
      null,
    )
  }

  // Tratamento especial para login: não redirecionar nem recarregar a página,
  // apenas devolver a mensagem para o formulário exibir via toast.
  if (res.status === 401 && path.startsWith('/auth/login')) {
    const err = await res.json().catch(() => ({}));
    let msg = mensagemErroApi(err, 401);
    if (msg.startsWith('Não foi possível concluir')) msg = 'E-mail ou senha inválidos.';
    throw new ApiError(msg, 401, err);
  }

  if (res.status === 401) {
    const err = await res.json().catch(() => ({}));
    // Se já estamos no fluxo de refresh, não tenta de novo.
    const skipRefresh =
      headers instanceof Headers
        ? headers.has('X-DX-Skip-Refresh')
        : typeof headers === 'object' && headers != null && 'X-DX-Skip-Refresh' in (headers as Record<string, unknown>)
    if (!skipRefresh && !path.startsWith('/auth/refresh')) {
      const refreshed = await refreshAccessToken()
      if (refreshed?.access_token) {
        // retry 1x com o novo access token
        return api<T>(path, options)
      }
    }

    invalidateSessionAndRedirectToLogin()
    throw new ApiError(mensagemErroApi(err, 401), 401, err);
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(mensagemErroApi(err, res.status), res.status, err);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

/** Chamadas públicas (sem token nem redirect em 401). */
async function publicApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!apiOrigin()) {
    throw new ApiError('Informe a conta da empresa para ligar ao painel.', 0, null)
  }
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as object),
  }
  if (isMultiTenantMode()) {
    ;(headers as Record<string, string>)['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
  }
  const res = await fetch(`${apiOrigin()}${API_VERSION_PREFIX}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new ApiError(mensagemErroApi(err, res.status), res.status, err)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const kbPublic = {
  branding: () => publicApi<Kb.PublicBranding>('/kb/public/branding'),
  logoAssetUrl: () => `${apiOrigin()}${API_VERSION_PREFIX}/kb/public/logo`,
  listCategories: () => publicApi<Kb.Category[]>('/kb/public/categories'),
  listArticles: (params?: { busca?: string; category_id?: number; limit?: number }) =>
    publicApi<Kb.ArticleBrief[]>(withParams('/kb/public/articles', params)),
  getArticleBySlug: (slug: string) =>
    publicApi<Kb.Article>(`/kb/public/articles/${encodeURIComponent(slug)}`),
  submitArticleFeedback: (slug: string, data: { util: boolean }) =>
    publicApi<Kb.ArticleFeedback>(`/kb/public/articles/${encodeURIComponent(slug)}/feedback`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  suggestions: (params: { motivo_id?: number; natureza_id?: number }) =>
    publicApi<Kb.ArticleBrief[]>(withParams('/kb/public/suggestions', params)),
  iniciarChat: (data: Kb.PortalChatSessionCreate, visitorToken?: string | null) =>
    publicApi<Kb.PortalChatSession>('/kb/public/chat/session', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: visitorToken ? { 'X-Portal-Visitor-Token': visitorToken } : {},
    }),
  obterChat: (visitorToken: string) =>
    publicApi<Kb.PortalChatPublicSession>('/kb/public/chat', {
      headers: { 'X-Portal-Visitor-Token': visitorToken },
    }),
  listarMensagensChat: (visitorToken: string, sinceId?: number) =>
    publicApi<Kb.PortalChatMensagem[]>(
      withParams('/kb/public/chat/mensagens', sinceId ? { since_id: sinceId } : undefined),
      { headers: { 'X-Portal-Visitor-Token': visitorToken } },
    ),
  enviarMensagemChat: (visitorToken: string, corpo: string) =>
    publicApi<Kb.PortalChatMensagem>('/kb/public/chat/mensagens', {
      method: 'POST',
      body: JSON.stringify({ corpo }),
      headers: { 'X-Portal-Visitor-Token': visitorToken },
    }),
  enviarMidiaChat: (visitorToken: string, file: File, caption?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    let mediatipo = 'documento';
    const nome = file.name.toLowerCase();
    if (file.type.startsWith('image/')) mediatipo = 'imagem';
    else if (file.type.startsWith('audio/') || nome.endsWith('.webm') || nome.endsWith('.ogg')) mediatipo = 'audio';
    else if (file.type.startsWith('video/')) mediatipo = 'video';
    formData.append('mediatipo', mediatipo);
    formData.append('caption', caption || '');
    return publicApi<Kb.PortalChatMensagem>('/kb/public/chat/mensagens/midia', {
      method: 'POST',
      body: formData,
      headers: { 'X-Portal-Visitor-Token': visitorToken },
    });
  },
  midiaChatUrl: (mensagemId: number) =>
    `${apiOrigin()}${API_VERSION_PREFIX}/kb/public/chat/mensagens/${mensagemId}/midia`,
}

export const publicCsat = {
  get: (token: string) =>
    publicApi<PublicCsat.TicketCsat>(`/public/csat/tickets/${encodeURIComponent(token)}`),
  submit: (token: string, data: { nota: number; comentario?: string | null }) =>
    publicApi<PublicCsat.TicketCsat>(`/public/csat/tickets/${encodeURIComponent(token)}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export namespace PublicCsat {
  export interface TicketCsat {
    status: 'pendente' | 'respondido' | 'expirado' | 'invalido';
    protocolo?: string | null;
    assunto?: string | null;
    nota?: number | null;
    comentario?: string | null;
    respondida_em?: string | null;
  }
}

export const auth = {
  login: (email: string, senha: string) =>
    api<{ access_token: string; refresh_token?: string | null; must_change_password?: boolean }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, senha }),
    }),
  solicitarRedefinicaoSenha: (email: string) =>
    api<{ detail: string }>('/auth/solicitar-redefinicao-senha', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  redefinirSenha: (token: string, senha_nova: string) =>
    api<{ detail: string }>('/auth/redefinir-senha', {
      method: 'POST',
      body: JSON.stringify({ token, senha_nova }),
    }),
};

function withParams(path: string, params?: Record<string, string | number | boolean | undefined>) {
  if (!params) return path;
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `${path}?${s}` : path;
}

/** Resposta padrão de listagens paginadas (backend ListaPaginada). */
export type Paginated<T> = { items: T[]; total: number };

/**
 * Aceita tanto `{ items, total }` quanto array legado `[]` (API antiga),
 * evitando tela em branco quando backend e frontend estão dessincronizados.
 */
export function normalizePaginated<T>(data: unknown): Paginated<T> {
  if (Array.isArray(data)) {
    return { items: data as T[], total: (data as T[]).length }
  }
  if (data && typeof data === 'object' && 'items' in data) {
    const d = data as { items?: unknown; total?: unknown }
    const items = Array.isArray(d.items) ? (d.items as T[]) : []
    const total = typeof d.total === 'number' ? d.total : items.length
    return { items, total }
  }
  return { items: [], total: 0 }
}

function listPaginated<T>(path: string, params?: Record<string, string | number | boolean | undefined>) {
  return api<unknown>(withParams(path, params)).then((raw) => normalizePaginated<T>(raw))
}

export const redes = {
  list: (params?: {
    incluir_inativos?: boolean;
    busca?: string;
    ordenar_por?: 'nome' | 'ativo' | 'created_at';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<Redes.Rede>('/redes', params),
  get: (id: number) => api<Redes.Rede>(`/redes/${id}`),
  getFuncionarios: (
    redeId: number,
    params?: {
      incluir_inativos?: boolean;
      busca?: string;
      ordenar_por?: 'nome' | 'email' | 'tipo';
      ordem?: 'asc' | 'desc';
      offset?: number;
      limit?: number;
    },
  ) => listPaginated<Redes.FuncionarioComVinculo>(`/redes/${redeId}/funcionarios`, params),
  create: (data: Redes.Create) => api<Redes.Rede>('/redes', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Redes.Update) => api<Redes.Rede>(`/redes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/redes/${id}`, { method: 'DELETE' }),
};

const CADASTRO_AUX_FETCH_MS = 60_000;

function signalCadastroAux(external?: AbortSignal | null): AbortSignal {
  const t = AbortSignal.timeout(CADASTRO_AUX_FETCH_MS);
  if (!external) return t;
  if (typeof AbortSignal.any === 'function') return AbortSignal.any([t, external]);
  return external;
}

export namespace CadastroAux {
  export interface Uf {
    sigla: string;
    nome: string;
    ibge_id: number;
  }
  export interface MunicipiosResponse {
    uf: string;
    nomes: string[];
  }
  export interface CepEndereco {
    cep: string;
    logradouro: string;
    complemento: string;
    bairro: string;
    localidade: string;
    uf: string;
  }
}

/** UF, municípios (IBGE) e CEP (ViaCEP) — sempre via backend. */
export const cadastroAux = {
  ufs: (init?: RequestInit) =>
    api<CadastroAux.Uf[]>('/cadastro-aux/ufs', { ...init, signal: signalCadastroAux(init?.signal ?? null) }),
  municipiosPorUf: (uf: string, init?: RequestInit) =>
    api<CadastroAux.MunicipiosResponse>(
      withParams('/cadastro-aux/municipios', { uf: uf.trim().toUpperCase() }),
      { ...init, signal: signalCadastroAux(init?.signal ?? null) },
    ),
  consultarCep: (cep: string, init?: RequestInit) =>
    api<CadastroAux.CepEndereco>(`/cadastro-aux/cep/${encodeURIComponent(cep.replace(/\D/g, ''))}`, {
      ...init,
      signal: signalCadastroAux(init?.signal ?? null),
    }),
  /** Recarrega todos os municípios do IBGE no servidor (somente admin). */
  sincronizarMunicipios: () =>
    api<{ ok: boolean; total: number }>('/cadastro-aux/municipios/sincronizar', { method: 'POST' }),
};

export const empresas = {
  /** Admin: tipar como Empresa. Atendente: omita o genérico (lista resumida). */
  list: <T = Empresas.EmpresaListaItem>(params?: {
    rede_id?: number;
    incluir_inativos?: boolean;
    busca?: string;
    ordenar_por?: 'nome' | 'cnpj_cpf' | 'cidade' | 'rede' | 'ativo';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<T>('/empresas', params),
  get: (id: number) => api<Empresas.Empresa>(`/empresas/${id}`),
  consultarCnpj: (cnpj: string) => api<Empresas.ConsultaCNPJ>(`/empresas/consultar-cnpj/${encodeURIComponent(cnpj.replace(/\D/g, ''))}`),
  create: (data: Empresas.Create) => api<Empresas.Empresa>('/empresas', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Empresas.Update) => api<Empresas.Empresa>(`/empresas/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/empresas/${id}`, { method: 'DELETE' }),
};

export const tiposNegocio = {
  list: (params?: {
    incluir_inativos?: boolean;
    busca?: string;
    ordenar_por?: 'nome' | 'ativo';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<TiposNegocio.Tipo>('/tipos-negocio', params),
  get: (id: number) => api<TiposNegocio.Tipo>(`/tipos-negocio/${id}`),
  create: (data: TiposNegocio.Create) => api<TiposNegocio.Tipo>('/tipos-negocio', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: TiposNegocio.Update) => api<TiposNegocio.Tipo>(`/tipos-negocio/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/tipos-negocio/${id}`, { method: 'DELETE' }),
};

export const setores = {
  list: (params?: {
    incluir_inativos?: boolean;
    busca?: string;
    ordenar_por?: 'nome' | 'slug' | 'ativo';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<Setores.Setor>('/setores', params),
  get: (id: number) => api<Setores.Setor>(`/setores/${id}`),
  create: (data: Setores.Create) => api<Setores.Setor>('/setores', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Setores.Update) => api<Setores.Setor>(`/setores/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  updateDistribuicao: (id: number, data: Setores.DistribuicaoUpdate) =>
    api<Setores.Distribuicao>(`/setores/${id}/distribuicao`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/setores/${id}`, { method: 'DELETE' }),
};

export const atendentes = {
  trocarSenha: (senhaAtual: string, senhaNova: string) =>
    api<Atendentes.Atendente>('/atendentes/me/trocar-senha', {
      method: 'POST',
      body: JSON.stringify({ senha_atual: senhaAtual, senha_nova: senhaNova }),
    }),
  list: (params?: {
    incluir_inativos?: boolean;
    busca?: string;
    ordenar_por?: 'nome' | 'email' | 'role' | 'ativo';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<Atendentes.Atendente>('/atendentes', params),
  /** Ligação real ao setor no banco (para o modal de ticket); não exige ser admin. */
  listPorSetor: (setorId: number, params?: { incluir_inativos?: boolean }) =>
    api<Atendentes.Atendente[]>(withParams(`/atendentes/por-setor/${setorId}`, params)),
  me: () => api<Atendentes.Atendente>('/atendentes/me'),
  get: (id: number) => api<Atendentes.Atendente>(`/atendentes/${id}`),
  avaliacoes: (id: number) => api<Atendentes.AvaliacoesResumo>(`/atendentes/${id}/avaliacoes`),
  create: (data: Atendentes.Create) => api<Atendentes.Atendente>('/atendentes', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Atendentes.Update) => api<Atendentes.Atendente>(`/atendentes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/atendentes/${id}`, { method: 'DELETE' }),
};

export const funcionariosRede = {
  list: (params?: {
    rede_id?: number;
    empresa_id?: number;
    tipo?: string;
    incluir_inativos?: boolean;
    busca?: string;
    ordenar_por?: 'nome' | 'email' | 'tipo' | 'ativo' | 'rede_id';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<FuncionariosRede.Funcionario>('/funcionarios-rede', params),
  get: (id: number) => api<FuncionariosRede.Funcionario>(`/funcionarios-rede/${id}`),
  create: (data: FuncionariosRede.Create) => api<FuncionariosRede.Funcionario>('/funcionarios-rede', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: FuncionariosRede.Update) => api<FuncionariosRede.Funcionario>(`/funcionarios-rede/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/funcionarios-rede/${id}`, { method: 'DELETE' }),
};

export const statusTicket = {
  list: (params?: {
    incluir_inativos?: boolean;
    busca?: string;
    ordenar_por?: 'nome' | 'slug' | 'ordem' | 'ativo';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<StatusTicket.Status>('/status-ticket', params),
  get: (id: number) => api<StatusTicket.Status>(`/status-ticket/${id}`),
  create: (data: StatusTicket.Create) => api<StatusTicket.Status>('/status-ticket', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: StatusTicket.Update) => api<StatusTicket.Status>(`/status-ticket/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/status-ticket/${id}`, { method: 'DELETE' }),
};

export const respostasProntas = {
  list: (params?: {
    incluir_inativos?: boolean;
    busca?: string;
    setor_id?: number;
    ordenar_por?: 'titulo' | 'ordem' | 'ativo';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<RespostasProntas.Resposta>('/respostas-prontas', params),
  get: (id: number) => api<RespostasProntas.Resposta>(`/respostas-prontas/${id}`),
  create: (data: RespostasProntas.Create) =>
    api<RespostasProntas.Resposta>('/respostas-prontas', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: RespostasProntas.Update) =>
    api<RespostasProntas.Resposta>(`/respostas-prontas/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/respostas-prontas/${id}`, { method: 'DELETE' }),
  disponiveis: (setorId: number, busca?: string) =>
    api<RespostasProntas.Resposta[]>(
      withParams('/respostas-prontas/disponiveis', { setor_id: setorId, busca: busca || undefined }),
    ),
};

export const kb = {
  listCategories: () => api<Kb.Category[]>('/kb/categories'),
  createCategory: (data: Kb.CategoryCreate) =>
    api<Kb.Category>('/kb/categories', { method: 'POST', body: JSON.stringify(data) }),
  updateCategory: (id: number, data: Kb.CategoryUpdate) =>
    api<Kb.Category>(`/kb/categories/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCategory: (id: number) => api<void>(`/kb/categories/${id}`, { method: 'DELETE' }),
  reorderCategories: (items: { id: number; ordem: number }[]) =>
    api<Kb.Category[]>('/kb/categories/reorder', {
      method: 'PUT',
      body: JSON.stringify({ items }),
    }),
  listArticles: (params?: {
    busca?: string;
    status?: string;
    category_id?: number;
    incluir_arquivados?: boolean;
    offset?: number;
    limit?: number;
    ordenar_por?: 'titulo' | 'status' | 'updated_at' | 'published_at';
    ordem?: 'asc' | 'desc';
  }) => listPaginated<Kb.ArticleBrief>('/kb/articles', params),
  getArticle: (id: number) => api<Kb.Article>(`/kb/articles/${id}`),
  createArticle: (data: Kb.ArticleCreate) =>
    api<Kb.Article>('/kb/articles', { method: 'POST', body: JSON.stringify(data) }),
  updateArticle: (id: number, data: Kb.ArticleUpdate) =>
    api<Kb.Article>(`/kb/articles/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  publishArticle: (id: number) =>
    api<Kb.Article>(`/kb/articles/${id}/publish`, { method: 'POST' }),
  archiveArticle: (id: number) =>
    api<Kb.Article>(`/kb/articles/${id}/archive`, { method: 'POST' }),
  consulta: (params?: { busca?: string; category_id?: number; limit?: number }) =>
    api<Kb.ArticleBrief[]>(withParams('/kb/articles/consulta', params)),
  getPublicado: (id: number) => api<Kb.Article>(`/kb/articles/publicados/${id}`),
  listPublicCategories: () => kbPublic.listCategories(),
  listPublicArticles: (params?: { busca?: string; category_id?: number; limit?: number }) =>
    kbPublic.listArticles(params),
  getPublicArticleBySlug: (slug: string) => kbPublic.getArticleBySlug(slug),
  listArticleVersions: (articleId: number) => api<Kb.ArticleVersion[]>(`/kb/articles/${articleId}/versions`),
  listArticleMotivoLinks: (articleId: number) => api<Kb.MotivoLinkItem[]>(`/kb/articles/${articleId}/motivo-links`),
  updateArticleMotivoLinks: (articleId: number, links: Kb.MotivoLinkItem[]) =>
    api<Kb.MotivoLinkItem[]>(`/kb/articles/${articleId}/motivo-links`, {
      method: 'PUT',
      body: JSON.stringify({ links }),
    }),
  suggestions: (params: { motivo_id?: number; natureza_id?: number }) =>
    api<Kb.ArticleBrief[]>(withParams('/kb/suggestions', params)),
  publicSuggestions: (params: { motivo_id?: number; natureza_id?: number }) => kbPublic.suggestions(params),
  getPortalSettings: () => api<Kb.PortalSettings>('/kb/portal-settings'),
  updatePortalSettings: (data: Kb.PortalSettingsUpdate) =>
    api<Kb.PortalSettings>('/kb/portal-settings', { method: 'PUT', body: JSON.stringify(data) }),
  getArticleVersion: (articleId: number, versionId: number) =>
    api<Kb.ArticleVersionDetail>(`/kb/articles/${articleId}/versions/${versionId}`),
  uploadImage: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api<Kb.ImageUpload>('/kb/images', { method: 'POST', body: fd })
  },
  imageUrl: (filename: string) => `${resolvedApiBaseUrl()}${API_VERSION_PREFIX}/kb/images/${encodeURIComponent(filename)}`,
};

export const routingRules = {
  list: (params?: { incluir_inativos?: boolean }) =>
    api<RoutingRules.Regra[]>(withParams('/routing/rules', params)),
  get: (id: number) => api<RoutingRules.Regra>(`/routing/rules/${id}`),
  create: (data: RoutingRules.Create) =>
    api<RoutingRules.Regra>('/routing/rules', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: RoutingRules.Update) =>
    api<RoutingRules.Regra>(`/routing/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/routing/rules/${id}`, { method: 'DELETE' }),
  reorder: (items: { id: number; ordem: number }[]) =>
    api<RoutingRules.Regra[]>('/routing/rules/reorder', {
      method: 'PUT',
      body: JSON.stringify({ items }),
    }),
  simulate: (data: RoutingRules.Simulate) =>
    api<RoutingRules.Resultado>('/routing/rules/simulate', { method: 'POST', body: JSON.stringify(data) }),
};

export const sla = {
  prioridades: () => api<Sla.PrioridadesDisponiveis>('/sla/prioridades'),
  policies: {
    list: (params?: { setor_id?: number; incluir_inativos?: boolean }) =>
      api<Sla.Policy[]>(withParams('/sla/policies', params)),
    get: (id: number) => api<Sla.Policy>(`/sla/policies/${id}`),
    create: (data: Sla.PolicyCreate) =>
      api<Sla.Policy>('/sla/policies', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: Sla.PolicyUpdate) =>
      api<Sla.Policy>(`/sla/policies/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  },
  calendars: {
    list: (params?: { setor_id?: number; incluir_inativos?: boolean }) =>
      api<Sla.BusinessCalendar[]>(withParams('/sla/calendars', params)),
    get: (id: number) => api<Sla.BusinessCalendar>(`/sla/calendars/${id}`),
    create: (data: Sla.BusinessCalendarCreate) =>
      api<Sla.BusinessCalendar>('/sla/calendars', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: Sla.BusinessCalendarUpdate) =>
      api<Sla.BusinessCalendar>(`/sla/calendars/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  },
};

export const audit = {
  list: (params?: {
    entity_type?: string;
    entity_id?: number;
    action?: string;
    atendente_id?: number;
    de?: string;
    ate?: string;
    busca?: string;
    ordenar_por?: 'created_at' | 'entity_type' | 'entity_id' | 'action' | 'atendente';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<Audit.AuditLogEntry>('/audit', params),
  exportCsv: async (params?: {
    entity_type?: string;
    entity_id?: number;
    action?: string;
    atendente_id?: number;
    de?: string;
    ate?: string;
    busca?: string;
  }) => {
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (isMultiTenantMode()) {
      headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname());
    }
    if (token) headers.Authorization = `Bearer ${token}`;
    const url = `${apiOrigin()}${API_VERSION_PREFIX}${withParams('/audit', { ...params, format: 'csv' })}`;
    const res = await fetch(url, { headers });
    if (res.status === 401) {
      invalidateSessionAndRedirectToLogin();
      throw new ApiError('Sessão expirada ou inválida.', 401, {});
    }
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody);
    }
    return res.blob();
  },
};

export const presenca = {
  online: () => api<Presenca.ListaOnline>('/presenca/online'),
  forcarSaida: (atendenteId: number) =>
    api<void>(`/presenca/online/${atendenteId}/forcar-saida`, { method: 'POST' }),
};

export const ponto = {
  bater: (data: Ponto.Bater) =>
    api<Ponto.Batida>('/ponto/bater', { method: 'POST', body: JSON.stringify(data) }),
  me: () => api<Ponto.EstadoMe>('/ponto/me'),
  minhasBatidas: (params?: { desde?: string; ate?: string; offset?: number; limit?: number }) =>
    api<Ponto.Historico>(withParams('/ponto/me/batidas', params)),
  meuCalendario: (ano: number, mes: number) =>
    api<Ponto.Calendario>(withParams('/ponto/me/calendario', { ano, mes })),
  meuBancoHoras: (desde: string, ate: string) =>
    api<Ponto.BancoHoras>(withParams('/ponto/me/banco-horas', { desde, ate })),
  bancoHorasAdmin: (atendenteId: number, desde: string, ate: string) =>
    api<Ponto.BancoHoras>(
      withParams('/ponto/banco-horas', { atendente_id: atendenteId, desde, ate }),
    ),
  batidasAdmin: (params?: {
    atendente_id?: number;
    desde?: string;
    ate?: string;
    offset?: number;
    limit?: number;
  }) => listPaginated<Ponto.BatidaAdmin>('/ponto/batidas', params),
  calendarioAdmin: (atendenteId: number, ano: number, mes: number) =>
    api<Ponto.Calendario>(withParams('/ponto/calendario', { atendente_id: atendenteId, ano, mes })),
  hoje: () => api<Ponto.HojeLista>('/ponto/hoje'),
  digest: () => api<Ponto.Digest>('/ponto/digest'),
  alertas: () => api<Ponto.AlertasMe>('/ponto/me/alertas'),
  settings: () => api<Ponto.Settings>('/ponto/settings'),
  updateSettings: (data: Ponto.SettingsUpdate) =>
    api<Ponto.Settings>('/ponto/settings', { method: 'PATCH', body: JSON.stringify(data) }),
  feriados: (ano?: number) => api<Ponto.Feriado[]>(withParams('/ponto/feriados', { ano })),
  criarFeriado: (data: Ponto.FeriadoCreate) =>
    api<Ponto.Feriado>('/ponto/feriados', { method: 'POST', body: JSON.stringify(data) }),
  removerFeriado: (id: number) =>
    api<void>(`/ponto/feriados/${id}`, { method: 'DELETE' }),
  criarAjuste: (data: Ponto.AjusteCreate) =>
    api<Ponto.Batida>('/ponto/batidas', { method: 'POST', body: JSON.stringify(data) }),
  atualizarAjuste: (id: number, data: Ponto.AjusteUpdate) =>
    api<Ponto.Batida>(`/ponto/batidas/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  anular: (id: number, motivo: string) =>
    api<Ponto.Batida>(`/ponto/batidas/${id}/anular`, {
      method: 'POST',
      body: JSON.stringify({ motivo }),
    }),
  criarJustificativa: (data: Ponto.JustificativaCreate) =>
    api<Ponto.Justificativa>('/ponto/justificativas', { method: 'POST', body: JSON.stringify(data) }),
  minhasJustificativas: () => api<Ponto.Justificativa[]>('/ponto/justificativas/me'),
  justificativasAdmin: (estado?: string) =>
    api<Ponto.Justificativa[]>(withParams('/ponto/justificativas', { estado })),
  decidirJustificativa: (id: number, data: Ponto.JustificativaDecisao) =>
    api<Ponto.Justificativa>(`/ponto/justificativas/${id}/decidir`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  exportCsv: async (params?: { atendente_id?: number; desde?: string; ate?: string }) => {
    const token = getAuthToken()
    const headers: Record<string, string> = {}
    if (isMultiTenantMode()) {
      headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
    }
    if (token) headers.Authorization = `Bearer ${token}`
    const url = `${apiOrigin()}${API_VERSION_PREFIX}${withParams('/ponto/batidas/export.csv', params)}`
    const res = await fetch(url, { headers })
    if (res.status === 401) {
      invalidateSessionAndRedirectToLogin()
      throw new ApiError('Sessão expirada ou inválida.', 401, {})
    }
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}))
      throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody)
    }
    return res.blob()
  },
};

export namespace WhatsappSettings {
  export interface Read {
    evolution_base_url: string | null
    evolution_instance_name: string | null
    has_api_key: boolean
    has_webhook_secret: boolean
    evolution_embutida_disponivel: boolean
    auto_msg_espera_ativa: boolean
    auto_msg_espera_texto: string | null
    auto_msg_assumido_ativa: boolean
    auto_msg_assumido_texto: string | null
    auto_msg_encerrado_ativa: boolean
    auto_msg_encerrado_texto: string | null
    auto_msg_fora_horario_ativa: boolean
    auto_msg_fora_horario_texto: string | null
    horario_inicio: string | null
    horario_fim: string | null
    horario_timezone: string
    horario_semana?: Record<string, { ativo?: boolean; inicio?: string; fim?: string }> | null
    usar_feriados_nacionais?: boolean
    nome_empresa_exibicao?: string | null
    inativ_encerramento_ativa?: boolean
    inativ_aviso_minutos?: number | null
    inativ_encerramento_apos_aviso_minutos?: number | null
    auto_msg_inativ_aviso_ativa?: boolean
    auto_msg_inativ_aviso_texto?: string | null
    avaliacao_ativa?: boolean
    avaliacao_janela_minutos?: number
    auto_msg_avaliacao_ativa?: boolean
    auto_msg_avaliacao_texto?: string | null
    auto_msg_avaliacao_obrigado_texto?: string | null
    auto_msg_avaliacao_timeout_texto?: string | null
    auto_msg_avaliacao_pular_texto?: string | null
  }
  export interface ProvisionEmbutidoResult {
    instance: string
    webhook_url: string
    qrcode?: Record<string, unknown> | null
    connect_http_status?: number | null
    connect_erro?: string | null
  }
  export interface Update {
    evolution_base_url?: string | null
    evolution_instance_name?: string | null
    evolution_api_key?: string | null
    webhook_secret?: string | null
    auto_msg_espera_ativa?: boolean | null
    auto_msg_espera_texto?: string | null
    auto_msg_assumido_ativa?: boolean | null
    auto_msg_assumido_texto?: string | null
    auto_msg_encerrado_ativa?: boolean | null
    auto_msg_encerrado_texto?: string | null
    auto_msg_fora_horario_ativa?: boolean | null
    auto_msg_fora_horario_texto?: string | null
    horario_inicio?: string | null
    horario_fim?: string | null
    horario_timezone?: string | null
    horario_semana?: Record<string, { ativo?: boolean; inicio?: string; fim?: string }> | null
    usar_feriados_nacionais?: boolean | null
    nome_empresa_exibicao?: string | null
    inativ_encerramento_ativa?: boolean | null
    inativ_aviso_minutos?: number | null
    inativ_encerramento_apos_aviso_minutos?: number | null
    auto_msg_inativ_aviso_ativa?: boolean | null
    auto_msg_inativ_aviso_texto?: string | null
    avaliacao_ativa?: boolean | null
    avaliacao_janela_minutos?: number | null
    auto_msg_avaliacao_ativa?: boolean | null
    auto_msg_avaliacao_texto?: string | null
    auto_msg_avaliacao_obrigado_texto?: string | null
    auto_msg_avaliacao_timeout_texto?: string | null
    auto_msg_avaliacao_pular_texto?: string | null
  }
  export interface TesteResult {
    ok: boolean
    detalhe?: string | null
  }
}

export const whatsappSettings = {
  get: () => api<WhatsappSettings.Read>('/settings/whatsapp'),
  patch: (data: WhatsappSettings.Update) =>
    api<WhatsappSettings.Read>('/settings/whatsapp', { method: 'PATCH', body: JSON.stringify(data) }),
  testar: () =>
    api<WhatsappSettings.TesteResult>('/settings/whatsapp/testar-conexao', {
      method: 'POST',
    }),
  provisionarEmbutido: () =>
    api<WhatsappSettings.ProvisionEmbutidoResult>('/settings/whatsapp/provisao-embutida', { method: 'POST' }),
  qrCode: () => api<Record<string, unknown>>('/settings/whatsapp/qr-code'),
  estadoEmbutido: () => api<Record<string, unknown>>('/settings/whatsapp/estado-embutido'),
  reporEmbutido: () => api<void>('/settings/whatsapp/repor-embutido', { method: 'POST' }),
}

export namespace SystemSettings {
  export interface EmpresaSistema {
    cnpj?: string | null
    nome?: string | null
    razao_social?: string | null
    nome_fantasia?: string | null
    email?: string | null
    telefone?: string | null
    endereco?: string | null
    numero?: string | null
    complemento?: string | null
    bairro?: string | null
    cidade?: string | null
    estado?: string | null
    cep?: string | null
    logo_url?: string | null
  }

  export interface EmpresaSistemaUpdate {
    cnpj?: string | null
    nome?: string | null
    razao_social?: string | null
    nome_fantasia?: string | null
    email?: string | null
    telefone?: string | null
    endereco?: string | null
    numero?: string | null
    complemento?: string | null
    bairro?: string | null
    cidade?: string | null
    estado?: string | null
    cep?: string | null
  }

  export interface TicketEmailGraceOpcao {
    segundos: number
    rotulo: string
  }

  export interface EmailSettingsRead {
    transactional_from_email?: string | null
    transactional_from_name?: string | null
    transactional_reply_to_email?: string | null
    outbound_configured?: boolean
    has_transactional_api_key?: boolean
    ticket_mensagem_email_grace_seconds?: number
    opcoes_ticket_mensagem_email_grace?: TicketEmailGraceOpcao[]
  }

  export interface EmailSettingsUpdate {
    transactional_api_key?: string | null
    transactional_from_email?: string | null
    transactional_from_name?: string | null
    ticket_mensagem_email_grace_seconds?: number | null
  }

  export interface EmailTestResult {
    ok: boolean
    detail?: string | null
  }
}

export const systemSettings = {
  getEmpresaSistema: () => api<SystemSettings.EmpresaSistema>('/settings/empresa-sistema'),
  putEmpresaSistema: (data: SystemSettings.EmpresaSistemaUpdate) =>
    api<SystemSettings.EmpresaSistema>('/settings/empresa-sistema', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  uploadEmpresaLogo: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api<SystemSettings.EmpresaSistema>('/settings/empresa-sistema/logo', { method: 'POST', body: fd })
  },
  deleteEmpresaLogo: () => api<SystemSettings.EmpresaSistema>('/settings/empresa-sistema/logo', { method: 'DELETE' }),
  getEmail: () => api<SystemSettings.EmailSettingsRead>('/settings/email'),
  putEmail: (data: SystemSettings.EmailSettingsUpdate) =>
    api<SystemSettings.EmailSettingsRead>('/settings/email', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  testEmailTransactional: () =>
    api<SystemSettings.EmailTestResult>('/settings/email/test-transactional', { method: 'POST' }),
}

export namespace TenantApi {
  export interface TenantRead {
    id: number
    nome: string
    ativo: boolean
    app_host?: string | null
  }

  export interface InboundAddressRead {
    id: number
    tenant_id: number
    local_part: string
    full_address: string
    label?: string | null
    setor_id: number
    setor_nome?: string | null
    setor_slug?: string | null
    default_empresa_id?: number | null
    ativo: boolean
  }
}

export const tenantApi = {
  getAtual: () => api<TenantApi.TenantRead>('/tenant/atual'),
  listInboundAddresses: () => api<TenantApi.InboundAddressRead[]>('/tenant/inbound-addresses'),
}

export async function fetchEmpresaSistemaLogoBlob(): Promise<Blob | null> {
  const token = getAuthToken()
  const headers: Record<string, string> = {}
  if (isMultiTenantMode()) {
    headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
  }
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${apiOrigin()}${API_VERSION_PREFIX}/settings/empresa-sistema/logo`, { headers })
  if (res.status === 404) return null
  if (res.status === 401) {
    invalidateSessionAndRedirectToLogin()
    throw new ApiError('Sessão expirada ou inválida.', 401, {})
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody)
  }
  return res.blob()
}

export namespace WhatsappChats {
  export interface Chat {
    id: number
    protocolo: string
    wa_id: string
    cliente_nome?: string | null
    estado: string
    setor_id?: number | null
    setor_nome?: string | null
    atendente_id?: number | null
    atendente_nome?: string | null
    created_at?: string | null
    atendimento_inicio_at?: string | null
    encerramento_at?: string | null
    avaliacao_nota?: number | null
    avaliacao_respondida_at?: string | null
    avaliacao_solicitada?: boolean
    ticket_ids: number[]
    funcionario_rede_id?: number | null
    funcionario_nome?: string | null
    funcionario_email?: string | null
    funcionario_tipo?: string | null
    empresa_id?: number | null
    empresa_nome?: string | null
    empresas_opcoes?: EmpresaOpcao[]
    inatividade_pausada?: boolean
    inatividade_retomada_em?: string | null
    classificacao_demanda_pendente?: boolean
    foto_perfil_url?: string | null
    foto_perfil_atualizada_em?: string | null
  }
  export interface EmpresaOpcao {
    id: number
    nome: string
  }
  export interface FuncionarioOpcao {
    id: number
    nome: string
    email?: string | null
    telefone?: string | null
    tipo: string
    empresas: EmpresaOpcao[]
    rede_id?: number | null
    rede_nome?: string | null
    similaridade?: number | null
    similaridade_alta?: boolean
  }
  export interface Contato {
    id: number
    nome: string
    email?: string | null
    telefone?: string | null
    tipo: string
    empresas: EmpresaOpcao[]
    rede_id?: number | null
    rede_nome?: string | null
  }
  export interface EmpresaCatalogo extends EmpresaOpcao {
    rede_id: number
  }
  export interface FuncionarioCatalogo {
    redes: Array<{ id: number; nome: string }>
    empresas: EmpresaCatalogo[]
  }
  export interface Avaliacao {
    chat_id: number
    protocolo: string
    wa_id: string
    cliente_nome?: string | null
    atendente_id?: number | null
    atendente_nome?: string | null
    setor_id?: number | null
    setor_nome?: string | null
    nota?: number | null
    avaliacao_respondida_at?: string | null
    encerramento_at?: string | null
    sem_avaliacao: boolean
  }
  export interface ReacaoMensagem {
    emoji: string
    count: number
    reagiu_eu: boolean
    atendente_ids?: number[]
    tem_cliente?: boolean
  }
  export interface Mensagem {
    id: number
    chat_id: number
    direcao: string
    corpo: string
    tipo_midia?: string | null
    mimetype?: string | null
    midia_disponivel?: boolean
    midia_nome_original?: string | null
    evento_sistema?: string | null
    wa_message_id?: string | null
    quoted_wa_message_id?: string | null
    quoted_corpo_preview?: string | null
    atendente_id?: number | null
    atendente_nome?: string | null
    status_entrega?: 'pendente' | 'enviada' | 'entregue' | 'lida' | 'erro' | null
    created_at?: string | null
    reacoes?: ReacaoMensagem[]
    editada?: boolean
    editada_em?: string | null
    apagada?: boolean
    pode_editar?: boolean
    pode_apagar_para_todos?: boolean
  }
  export interface Demanda {
    id: number
    chat_id: number
    natureza_id: number
    natureza_nome?: string | null
    motivo_id?: number | null
    motivo_nome?: string | null
    desfecho: string
    ticket_id?: number | null
    descricao_curta?: string | null
    atendente_id?: number | null
    atendente_nome?: string | null
    created_at?: string | null
  }
  export interface DemandaCreate {
    natureza_id: number
    motivo_id?: number | null
    descricao_curta?: string | null
  }
  export interface DemandaUpdate {
    natureza_id?: number
    motivo_id?: number | null
    descricao_curta?: string | null
  }
}

/** Obtém o binário de uma mensagem com mídia (requer JWT; não usar em `src` de img direto). */
export async function fetchWhatsAppMidiaBlob(chatId: number, mensagemId: number): Promise<Blob> {
  const token = getAuthToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(
    `${apiOrigin()}${API_VERSION_PREFIX}/whatsapp/chats/${chatId}/mensagens/${mensagemId}/midia`,
    { headers },
  )
  if (res.status === 401) {
    invalidateSessionAndRedirectToLogin()
    throw new ApiError('Sessão expirada ou inválida.', 401, {})
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody)
  }
  return res.blob()
}

export async function fetchPortalMidiaBlob(chatId: number, mensagemId: number): Promise<Blob> {
  const token = getAuthToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(
    `${apiOrigin()}${API_VERSION_PREFIX}/portal-chats/${chatId}/mensagens/${mensagemId}/midia`,
    { headers },
  )
  if (res.status === 401) {
    invalidateSessionAndRedirectToLogin()
    throw new ApiError('Sessão expirada ou inválida.', 401, {})
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody)
  }
  return res.blob()
}

export async function fetchPortalPublicMidiaBlob(
  visitorToken: string,
  mensagemId: number,
): Promise<Blob> {
  const res = await fetch(
    `${apiOrigin()}${API_VERSION_PREFIX}/kb/public/chat/mensagens/${mensagemId}/midia`,
    { headers: { 'X-Portal-Visitor-Token': visitorToken } },
  )
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody)
  }
  return res.blob()
}

export async function fetchChatInternoMidiaBlob(conversaId: number, mensagemId: number): Promise<Blob> {
  const token = getAuthToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(
    `${apiOrigin()}${API_VERSION_PREFIX}/chat-interno/conversas/${conversaId}/mensagens/${mensagemId}/download`,
    { headers },
  )
  if (res.status === 401) {
    invalidateSessionAndRedirectToLogin()
    throw new ApiError('Sessão expirada ou inválida.', 401, {})
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody)
  }
  return res.blob()
}

export async function fetchTicketAnexoBlob(ticketId: number, anexoId: number): Promise<Blob> {
  const token = getAuthToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(
    `${apiOrigin()}${API_VERSION_PREFIX}/tickets/${ticketId}/anexos/${anexoId}/download`,
    { headers },
  )
  if (res.status === 401) {
    invalidateSessionAndRedirectToLogin()
    throw new ApiError('Sessão expirada ou inválida.', 401, {})
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody)
  }
  return res.blob()
}

export const portalChats = {
  fila: () => api<PortalChats.Chat[]>('/portal-chats/fila'),
  meus: () => api<PortalChats.Chat[]>('/portal-chats/meus'),
  get: (id: number) => api<PortalChats.Chat>(`/portal-chats/${id}`),
  mensagens: (id: number, sinceId?: number) =>
    api<PortalChats.Mensagem[]>(withParams(`/portal-chats/${id}/mensagens`, sinceId ? { since_id: sinceId } : undefined)),
  demandas: (id: number) => api<PortalChats.Demanda[]>(`/portal-chats/${id}/demandas`),
  registrarDemanda: (id: number, data: PortalChats.DemandaCreate) =>
    api<PortalChats.Demanda>(`/portal-chats/${id}/demandas`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  excluirDemanda: (id: number, demandaId: number) =>
    api<void>(`/portal-chats/${id}/demandas/${demandaId}`, { method: 'DELETE' }),
  atualizarDemanda: (id: number, demandaId: number, data: PortalChats.DemandaUpdate) =>
    api<PortalChats.Demanda>(`/portal-chats/${id}/demandas/${demandaId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  assumir: (id: number) => api<PortalChats.Chat>(`/portal-chats/${id}/assumir`, { method: 'POST' }),
  encerrar: (id: number) => api<PortalChats.Chat>(`/portal-chats/${id}/encerrar`, { method: 'POST' }),
  transferir: (id: number, data: { setor_id: number; atendente_id?: number | null }) =>
    api<PortalChats.Chat>(`/portal-chats/${id}/transferir`, { method: 'POST', body: JSON.stringify(data) }),
  enviar: (id: number, corpo: string) =>
    api<PortalChats.Mensagem>(`/portal-chats/${id}/mensagens`, {
      method: 'POST',
      body: JSON.stringify({ corpo }),
    }),
  marcarVisto: (id: number) => api<void>(`/portal-chats/${id}/visto`, { method: 'POST' }),
  setoresParaTransferencia: () => api<Array<{ id: number; nome: string }>>('/portal-chats/transfer/setores'),
  enviarMidia: (id: number, file: File, caption?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    let mediatipo = 'documento';
    const nome = file.name.toLowerCase();
    if (file.type.startsWith('image/')) mediatipo = 'imagem';
    else if (file.type.startsWith('audio/') || nome.endsWith('.webm') || nome.endsWith('.ogg') || nome.endsWith('.m4a')) {
      mediatipo = 'audio';
    } else if (file.type.startsWith('video/')) mediatipo = 'video';
    formData.append('mediatipo', mediatipo);
    formData.append('caption', caption || '');
    return api<PortalChats.Mensagem>(`/portal-chats/${id}/mensagens/midia`, {
      method: 'POST',
      body: formData,
    });
  },
}

export const whatsappChats = {
  fila: () => api<WhatsappChats.Chat[]>('/whatsapp/chats/fila'),
  meus: () => api<WhatsappChats.Chat[]>('/whatsapp/chats/meus'),
  contatos: (params?: { busca?: string; offset?: number; limit?: number }) =>
    listPaginated<WhatsappChats.Contato>('/whatsapp/chats/contatos', params),
  iniciar: (data: {
    funcionario_id?: number | null
    telefone?: string | null
    mensagem_inicial?: string | null
    empresa_id?: number | null
  }) =>
    api<WhatsappChats.Chat>('/whatsapp/chats/iniciar', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  encerrados: (params?: Record<string, string | number | undefined>) =>
    listPaginated<WhatsappChats.Chat>('/whatsapp/chats/encerrados', params),
  avaliacoes: (params?: Record<string, string | number | undefined>) =>
    listPaginated<WhatsappChats.Avaliacao>('/whatsapp/chats/avaliacoes', params),
  get: (id: number) => api<WhatsappChats.Chat>(`/whatsapp/chats/${id}`),
  mensagens: (id: number) => api<WhatsappChats.Mensagem[]>(`/whatsapp/chats/${id}/mensagens`),
  demandas: (id: number) => api<WhatsappChats.Demanda[]>(`/whatsapp/chats/${id}/demandas`),
  registrarDemanda: (id: number, data: WhatsappChats.DemandaCreate) =>
    api<WhatsappChats.Demanda>(`/whatsapp/chats/${id}/demandas`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  excluirDemanda: (id: number, demandaId: number) =>
    api<void>(`/whatsapp/chats/${id}/demandas/${demandaId}`, { method: 'DELETE' }),
  atualizarDemanda: (id: number, demandaId: number, data: WhatsappChats.DemandaUpdate) =>
    api<WhatsappChats.Demanda>(`/whatsapp/chats/${id}/demandas/${demandaId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  assumir: (id: number, data?: { empresa_id?: number | null; setor_id?: number | null }) => {
    const params = new URLSearchParams()
    if (data?.empresa_id != null && data.empresa_id !== undefined) {
      params.set('empresa_id', String(data.empresa_id))
    }
    if (data?.setor_id != null && data.setor_id !== undefined) {
      params.set('setor_id', String(data.setor_id))
    }
    const qs = params.toString() ? `?${params.toString()}` : ''
    return api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/assumir${qs}`, { method: 'POST' })
  },
  atualizarFotoPerfil: (id: number) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/foto-perfil`, { method: 'POST' }),
  definirEmpresaContexto: (id: number, empresa_id: number) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/empresa-contexto`, {
      method: 'POST',
      body: JSON.stringify({ empresa_id }),
    }),
  encerrar: (id: number) => api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/encerrar`, { method: 'POST' }),
  transferir: (id: number, data: { setor_id: number; atendente_id?: number | null }) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/transferir`, { method: 'POST', body: JSON.stringify(data) }),
  enviar: (id: number, texto: string, quotedWaMessageId?: string | null) =>
    api<WhatsappChats.Mensagem>(`/whatsapp/chats/${id}/mensagens`, {
      method: 'POST',
      body: JSON.stringify({ texto, quoted_wa_message_id: quotedWaMessageId }),
    }),
  comentarInterno: (id: number, texto: string) =>
    api<WhatsappChats.Mensagem>(`/whatsapp/chats/${id}/comentarios-internos`, {
      method: 'POST',
      body: JSON.stringify({ texto }),
    }),
  definirReacao: (chatId: number, mensagemId: number, emoji: string) =>
    api<WhatsappChats.Mensagem>(`/whatsapp/chats/${chatId}/mensagens/${mensagemId}/reacoes`, {
      method: 'PUT',
      body: JSON.stringify({ emoji }),
    }),
  removerReacao: (chatId: number, mensagemId: number) =>
    api<WhatsappChats.Mensagem>(`/whatsapp/chats/${chatId}/mensagens/${mensagemId}/reacoes`, {
      method: 'DELETE',
    }),
  editarMensagem: (chatId: number, mensagemId: number, texto: string) =>
    api<WhatsappChats.Mensagem>(`/whatsapp/chats/${chatId}/mensagens/${mensagemId}`, {
      method: 'PATCH',
      body: JSON.stringify({ texto }),
    }),
  apagarMensagem: (chatId: number, mensagemId: number) =>
    api<WhatsappChats.Mensagem>(`/whatsapp/chats/${chatId}/mensagens/${mensagemId}`, {
      method: 'DELETE',
    }),
  marcarVisto: (id: number) => api<void>(`/whatsapp/chats/${id}/visto`, { method: 'POST' }),
  pausarInatividade: (id: number) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/inatividade/pausar`, { method: 'POST' }),
  retomarInatividade: (id: number) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/inatividade/retomar`, { method: 'POST' }),
  concluirClassificacaoDemanda: (id: number) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/classificacao-demanda/concluir`, { method: 'POST' }),
  vincularTicket: (id: number, ticketId: number) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/vincular-ticket`, {
      method: 'POST',
      body: JSON.stringify({ ticket_id: ticketId }),
    }),
  vincularFuncionario: (id: number, data: { funcionario_rede_id: number; empresa_id?: number | null }) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/vincular-funcionario`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  desvincularFuncionario: (id: number) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/desvincular-funcionario`, { method: 'POST' }),
  buscarFuncionarios: (busca: string, limit = 20) =>
    api<WhatsappChats.FuncionarioOpcao[]>(
      `/whatsapp/chats/funcionarios?${new URLSearchParams({ busca, limit: String(limit) }).toString()}`,
    ),
  buscarFuncionariosSimilares: (nome: string, limit = 5) =>
    api<WhatsappChats.FuncionarioOpcao[]>(
      `/whatsapp/chats/funcionarios/similares?${new URLSearchParams({
        nome,
        limit: String(limit),
      }).toString()}`,
    ),
  catalogoFuncionarios: () => api<WhatsappChats.FuncionarioCatalogo>('/whatsapp/chats/funcionarios/catalogo'),
  cadastrarFuncionario: (
    id: number,
    data: {
      nome: string
      email?: string | null
      rede_id: number
      tipo?: 'colaborador' | 'supervisor'
      escopo_empresas?: 'all' | 'selected'
      empresa_ids?: number[]
      empresa_id?: number | null
    },
  ) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/cadastrar-funcionario`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  abrirTicket: (
    id: number,
    data: {
      empresa_id: number
      setor_id: number
      assunto: string
      descricao?: string | null
      natureza_id?: number | null
      motivo_id?: number | null
    },
  ) =>
    api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/abrir-ticket`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  porTicket: (ticketId: number) => api<WhatsappChats.Chat[]>(`/whatsapp/chats/por-ticket/${ticketId}`),
  setoresParaTransferencia: () => api<Array<{ id: number; nome: string }>>('/whatsapp/chats/transfer/setores'),
  enviarFigurinha: (id: number, file: File, quotedWaMessageId?: string | null) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('mediatipo', 'figurinha')
    formData.append('caption', '')
    if (quotedWaMessageId) {
      formData.append('quoted_wa_message_id', quotedWaMessageId)
    }
    return api<WhatsappChats.Mensagem>(`/whatsapp/chats/${id}/mensagens/midia`, {
      method: 'POST',
      body: formData,
    })
  },
  enviarMidia: (id: number, file: File, caption?: string, quotedWaMessageId?: string | null) => {
    const formData = new FormData()
    formData.append('file', file)

    // Infere o tipo de mídia
    let mediatipo = 'documento'
    const nome = file.name.toLowerCase()
    if (file.type.startsWith('image/')) {
      mediatipo = 'imagem'
    } else if (file.type.startsWith('audio/') || nome.endsWith('.webm') || nome.endsWith('.ogg') || nome.endsWith('.m4a')) {
      mediatipo = 'audio'
    } else if (file.type.startsWith('video/')) {
      mediatipo = 'video'
    }

    formData.append('mediatipo', mediatipo)
    formData.append('caption', caption || '')
    if (quotedWaMessageId) {
      formData.append('quoted_wa_message_id', quotedWaMessageId)
    }

    return api<WhatsappChats.Mensagem>(`/whatsapp/chats/${id}/mensagens/midia`, {
      method: 'POST',
      body: formData,
    })
  }
}

export const tickets = {
  list: (params?: {
    empresa_id?: number;
    rede_id?: number;
    setor_id?: number;
    status_id?: number;
    situacao?: 'abertos' | 'fechados' | 'todos';
    protocolo?: string;
    busca?: string;
    sem_responsavel?: boolean;
    com_responsavel?: boolean;
    meus?: boolean;
    atendente_id?: number;
    /** Coluna para ordenar (omitir = mais recentes primeiro). */
    ordenar_por?: 'protocolo' | 'rede' | 'empresa' | 'setor' | 'assunto' | 'status' | 'responsavel' | 'fechado_em' | 'fila_desde_at';
    ordem?: 'asc' | 'desc';
    sla_violado?: boolean;
    sla_em_risco?: boolean;
    offset?: number;
    limit?: number;
  }) => listPaginated<Tickets.Ticket>('/tickets', params),
  get: (id: number) => api<Tickets.Ticket>(`/tickets/${id}`),
  getSla: (id: number) => api<Tickets.TicketSla>(`/tickets/${id}/sla`),
  getHistorico: (id: number) => api<Tickets.Historico[]>(`/tickets/${id}/historico`),
  listMensagens: (id: number) => api<Tickets.Mensagem[]>(`/tickets/${id}/mensagens`),
  addMensagem: (id: number, data: Tickets.MensagemCreate) =>
    api<Tickets.Mensagem>(`/tickets/${id}/mensagens`, { method: 'POST', body: JSON.stringify(data) }),
  startEditMensagem: (ticketId: number, mensagemId: number) =>
    api<Tickets.MensagemStartEdit>(`/tickets/${ticketId}/mensagens/${mensagemId}/start-edit`, { method: 'POST' }),
  updateMensagem: (ticketId: number, mensagemId: number, data: Tickets.MensagemUpdate) =>
    api<Tickets.Mensagem>(`/tickets/${ticketId}/mensagens/${mensagemId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  cancelMensagemEmail: (ticketId: number, mensagemId: number) =>
    api<Tickets.Mensagem>(`/tickets/${ticketId}/mensagens/${mensagemId}/cancel`, { method: 'POST' }),
  sendNowMensagemEmail: (ticketId: number, mensagemId: number) =>
    api<Tickets.Mensagem>(`/tickets/${ticketId}/mensagens/${mensagemId}/send-now`, { method: 'POST' }),
  reabrir: (id: number) => api<Tickets.Ticket>(`/tickets/${id}/reabrir`, { method: 'POST' }),
  /** Apenas desenvolvimento: gera link CSAT sem enviar e-mail. */
  csatLinkDev: (id: number) =>
    api<{ link: string; expires_at: string }>(`/tickets/${id}/csat/link-dev`, { method: 'POST' }),
  create: (data: Tickets.Create) => api<Tickets.Ticket>('/tickets', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Tickets.Update) => api<Tickets.Ticket>(`/tickets/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  addVinculo: (ticketId: number, data: Tickets.VinculoCreate) =>
    api<Tickets.TicketVinculo>(`/tickets/${ticketId}/vinculos`, { method: 'POST', body: JSON.stringify(data) }),
  removeVinculo: (ticketId: number, vinculoId: number) =>
    api<void>(`/tickets/${ticketId}/vinculos/${vinculoId}`, { method: 'DELETE' }),
  filhosMassaOpcoes: (ticketId: number) =>
    api<Tickets.FilhosMassaOpcoes>(`/tickets/${ticketId}/filhos-em-massa/opcoes`),
  criarFilhosMassa: (ticketId: number, data: Tickets.FilhosMassaCreate) =>
    api<Tickets.FilhosMassaResult>(`/tickets/${ticketId}/filhos-em-massa`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  anexosList: (id: number) => api<Tickets.Anexo[]>(`/tickets/${id}/anexos`),
  uploadAnexo: (id: number, file: File, mensagemId?: number | null) => {
    const fd = new FormData()
    fd.append('file', file)
    if (mensagemId != null) fd.append('mensagem_id', String(mensagemId))
    return api<Tickets.AnexoUploadResponse>(`/tickets/${id}/anexos`, { method: 'POST', body: fd })
  },
};

export const dashboard = {
  get: () => api<Dashboard.Response>('/dashboard'),
  getGeral: (params?: { de?: string; ate?: string }) =>
    api<Dashboard.GeralResponse>(withParams('/dashboard/geral', params)),
  getTickets: (params?: {
    de?: string;
    ate?: string;
    rede_id?: number;
    setor_id?: number;
    prioridade?: string;
    atendente_filtro_id?: number;
    drill_tipo?: string;
    drill_valor?: string;
  }) => api<Dashboard.TicketsResponse>(withParams('/dashboard/tickets', params)),
  getChats: (params?: {
    de?: string;
    ate?: string;
    setor_id?: number;
    empresa_id?: number;
    rede_id?: number;
    atendente_filtro_id?: number;
    drill_tipo?: string;
    drill_valor?: string;
  }) => api<Dashboard.ChatsResponse>(withParams('/dashboard/chats', params)),
  getChatsDemandas: (params?: {
    de?: string;
    ate?: string;
    setor_id?: number;
    empresa_id?: number;
    rede_id?: number;
    natureza_id?: number;
    motivo_id?: number;
    skip?: number;
    limit?: number;
  }) =>
    api<Dashboard.DemandasDrillResponse>(withParams('/dashboard/chats/demandas', params)),
  aceitarSugestaoMotivoOutros: (body: {
    natureza_id: number;
    texto_normalizado: string;
    nome?: string;
    slug?: string;
  }) =>
    api<TicketClassificacao.Motivo>('/dashboard/chats/demandas/sugestoes-motivo/aceitar', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  ignorarSugestaoMotivoOutros: (body: {
    natureza_id: number;
    texto_normalizado: string;
    texto_exemplo?: string;
  }) =>
    api<void>('/dashboard/chats/demandas/sugestoes-motivo/ignorar', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};

export const relatorios = {
  tickets: (params?: {
    de?: string;
    ate?: string;
    rede_id?: number;
    setor_id?: number;
    prioridade?: string;
    offset?: number;
    limit?: number;
  }) => api<Relatorios.TicketsResponse>(withParams('/relatorios/tickets', params)),
  exportTicketsCsv: async (params?: {
    de?: string;
    ate?: string;
    rede_id?: number;
    setor_id?: number;
    prioridade?: string;
  }) => {
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (isMultiTenantMode()) {
      headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname());
    }
    if (token) headers.Authorization = `Bearer ${token}`;
    const url = `${apiOrigin()}${API_VERSION_PREFIX}${withParams('/relatorios/tickets', { ...params, format: 'csv' })}`;
    const res = await fetch(url, { headers });
    if (res.status === 401) {
      invalidateSessionAndRedirectToLogin();
      throw new ApiError('Sessão expirada ou inválida.', 401, {});
    }
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody);
    }
    return res.blob();
  },
  chats: (params?: {
    de?: string;
    ate?: string;
    setor_id?: number;
    atendente_filtro_id?: number;
    offset?: number;
    limit?: number;
  }) => api<Relatorios.ChatsResponse>(withParams('/relatorios/chats', params)),
  exportChatsCsv: async (params?: {
    de?: string;
    ate?: string;
    setor_id?: number;
    atendente_filtro_id?: number;
  }) => {
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (isMultiTenantMode()) {
      headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname());
    }
    if (token) headers.Authorization = `Bearer ${token}`;
    const url = `${apiOrigin()}${API_VERSION_PREFIX}${withParams('/relatorios/chats', { ...params, format: 'csv' })}`;
    const res = await fetch(url, { headers });
    if (res.status === 401) {
      invalidateSessionAndRedirectToLogin();
      throw new ApiError('Sessão expirada ou inválida.', 401, {});
    }
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody);
    }
    return res.blob();
  },
};

export namespace Notificacoes {
  export interface Resumo {
    sem_responsavel_count: number;
    nao_lidas_count: number;
    wpp_fila_count: number;
    wpp_respostas_count: number;
    portal_fila_count: number;
    portal_respostas_count: number;
    chat_interno_nao_lidas_count: number;
    total_pendencias: number;
  }
  export interface Item {
    tipo:
      | 'fila_sem_responsavel'
      | 'mensagens_nao_lidas'
      | 'wpp_chats_na_fila'
      | 'wpp_chats_com_resposta'
      | 'chat_interno';
    ticket_id: number | null;
    chat_id?: number | null;
    conversa_id?: number | null;
    titulo: string;
    descricao: string;
    count: number;
    href: string;
    created_at?: string | null;
  }
  export interface ItensResponse {
    itens: Item[];
  }
  export interface Preferencias {
    email_habilitado: boolean;
    email_ticket_atribuido: boolean;
    email_nova_mensagem: boolean;
    email_sla_em_risco: boolean;
    email_sla_violado: boolean;
    push_habilitado: boolean;
    push_fila: boolean;
  }
}

export const notificacoes = {
  resumo: () => api<Notificacoes.Resumo>('/notificacoes/resumo'),
  itens: (params?: { limit?: number }) =>
    api<Notificacoes.ItensResponse>(withParams('/notificacoes/itens', params)),
  marcarVisto: (ticketId: number) =>
    api<void>(`/notificacoes/tickets/${ticketId}/visto`, { method: 'POST' }),
  preferenciasGet: () => api<Notificacoes.Preferencias>('/notificacoes/preferencias'),
  preferenciasUpdate: (data: Partial<Notificacoes.Preferencias>) =>
    api<Notificacoes.Preferencias>('/notificacoes/preferencias', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};

export namespace WebPush {
  export interface Vapid {
    configurado: boolean
    public_key: string | null
  }
  export interface Subscription {
    id: number
    endpoint: string
    user_agent: string | null
  }
  export interface RegistrarBody {
    endpoint: string
    p256dh: string
    auth: string
    user_agent?: string | null
  }
}

export const webPush = {
  vapid: () => api<WebPush.Vapid>('/web-push/vapid'),
  listar: () => api<WebPush.Subscription[]>('/web-push/subscriptions'),
  registrar: (body: WebPush.RegistrarBody) =>
    api<WebPush.Subscription>('/web-push/subscriptions', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  apagar: (id: number) =>
    api<void>(`/web-push/subscriptions/${id}`, { method: 'DELETE' }),
  apagarEndpoint: (endpoint: string) =>
    api<void>(`/web-push/subscriptions?endpoint=${encodeURIComponent(endpoint)}`, { method: 'DELETE' }),
};

export namespace ChatInterno {
  export type ConversaTipo = 'direta' | 'setor' | 'grupo';

  export interface ParticipanteGrupo {
    atendente_id: number;
    nome: string;
    papel: 'admin' | 'membro';
  }

  export interface ConversaInbox {
    id: number;
    tipo: ConversaTipo;
    titulo: string;
    setor_id: number | null;
    ultima_mensagem_corpo: string | null;
    ultima_mensagem_em: string | null;
    nao_lidas_count: number;
    silenciado?: boolean;
    created_at: string;
  }

  export interface Conversa {
    id: number;
    tipo: ConversaTipo;
    setor_id: number | null;
    setor_nome: string | null;
    titulo: string | null;
    participantes?: ParticipanteGrupo[] | null;
    sou_admin_grupo?: boolean;
    silenciado?: boolean;
    created_at: string;
  }

  export type TipoMidia = 'texto' | 'imagem' | 'video' | 'audio' | 'documento';

  export interface ReacaoMensagem {
    emoji: string;
    count: number;
    reagiu_eu: boolean;
  }

  export interface MencaoMensagem {
    tipo: 'user' | 'all';
    atendente_id?: number | null;
    rotulo?: string | null;
  }

  export interface Mensagem {
    id: number;
    conversa_id: number;
    atendente_id: number | null;
    atendente_nome: string | null;
    corpo: string;
    tipo_midia?: TipoMidia;
    mimetype?: string | null;
    nome_arquivo?: string | null;
    tamanho_bytes?: number | null;
    midia_disponivel?: boolean;
    status_entrega?: 'enviada' | 'entregue' | 'lida' | null;
    apagada?: boolean;
    editada?: boolean;
    editada_em?: string | null;
    reacoes?: ReacaoMensagem[];
    mencoes?: MencaoMensagem[];
    pode_editar?: boolean;
    pode_apagar_para_todos?: boolean;
    pode_apagar_para_mim?: boolean;
    reply_to_message_id?: number | null;
    reply_preview?: string | null;
    reply_autor_nome?: string | null;
    created_at: string;
  }

  export interface MensagensPagina {
    items: Mensagem[];
    total: number;
    tem_mais_antigas: boolean;
  }
}

export const chatInterno = {
  listarConversas: () => api<ChatInterno.ConversaInbox[]>('/chat-interno/conversas'),
  obterConversa: (conversaId: number) => api<ChatInterno.Conversa>(`/chat-interno/conversas/${conversaId}`),
  criarDireta: (atendente_id: number) =>
    api<ChatInterno.Conversa>('/chat-interno/conversas/direta', {
      method: 'POST',
      body: JSON.stringify({ atendente_id }),
    }),
  criarGrupo: (titulo: string, atendente_ids: number[]) =>
    api<ChatInterno.Conversa>('/chat-interno/conversas/grupo', {
      method: 'POST',
      body: JSON.stringify({ titulo, atendente_ids }),
    }),
  atualizarParticipantesGrupo: (
    conversaId: number,
    data: {
      adicionar?: number[];
      remover?: number[];
      promover_admin?: number[];
      rebaixar_admin?: number[];
    },
  ) =>
    api<ChatInterno.Conversa>(`/chat-interno/conversas/${conversaId}/participantes`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  silenciarConversa: (conversaId: number, silenciado: boolean) =>
    api<ChatInterno.Conversa>(`/chat-interno/conversas/${conversaId}/silenciar`, {
      method: 'PATCH',
      body: JSON.stringify({ silenciado }),
    }),
  mensagens: (conversaId: number, params?: { antesDeId?: number }) =>
    api<ChatInterno.MensagensPagina>(
      withParams(`/chat-interno/conversas/${conversaId}/mensagens`, {
        antes_de_id: params?.antesDeId,
      }),
    ),
  enviar: (
    conversaId: number,
    corpo: string,
    replyToMessageId?: number | null,
    mencoes?: ChatInterno.MencaoMensagem[] | null,
  ) =>
    api<ChatInterno.Mensagem>(`/chat-interno/conversas/${conversaId}/mensagens`, {
      method: 'POST',
      body: JSON.stringify({
        corpo,
        ...(replyToMessageId != null ? { reply_to_message_id: replyToMessageId } : {}),
        ...(mencoes && mencoes.length > 0 ? { mencoes } : {}),
      }),
    }),
  enviarMidia: (conversaId: number, file: File, caption?: string, replyToMessageId?: number | null) => {
    const formData = new FormData();
    formData.append('file', file);
    let mediatipo: ChatInterno.TipoMidia = 'documento';
    if (file.type.startsWith('image/')) mediatipo = 'imagem';
    else if (file.type.startsWith('audio/') || file.name.endsWith('.webm') || file.name.endsWith('.ogg')) {
      mediatipo = 'audio';
    } else if (file.type.startsWith('video/')) mediatipo = 'video';
    formData.append('mediatipo', mediatipo);
    formData.append('caption', caption || '');
    if (replyToMessageId != null) formData.append('reply_to_message_id', String(replyToMessageId));
    return api<ChatInterno.Mensagem>(`/chat-interno/conversas/${conversaId}/mensagens/midia`, {
      method: 'POST',
      body: formData,
    });
  },
  marcarVisto: (conversaId: number) =>
    api<void>(`/chat-interno/conversas/${conversaId}/visto`, { method: 'POST' }),
  editarMensagem: (conversaId: number, mensagemId: number, corpo: string) =>
    api<ChatInterno.Mensagem>(`/chat-interno/conversas/${conversaId}/mensagens/${mensagemId}`, {
      method: 'PATCH',
      body: JSON.stringify({ corpo }),
    }),
  apagarMensagem: (conversaId: number, mensagemId: number, escopo: 'todos' | 'para_mim') =>
    api<ChatInterno.Mensagem | void>(
      `/chat-interno/conversas/${conversaId}/mensagens/${mensagemId}?escopo=${escopo}`,
      { method: 'DELETE' },
    ),
  limparConversa: (conversaId: number) =>
    api<void>(`/chat-interno/conversas/${conversaId}/limpar`, { method: 'POST' }),
  definirReacao: (conversaId: number, mensagemId: number, emoji: string) =>
    api<ChatInterno.Mensagem>(`/chat-interno/conversas/${conversaId}/mensagens/${mensagemId}/reacoes`, {
      method: 'PUT',
      body: JSON.stringify({ emoji }),
    }),
  removerReacao: (conversaId: number, mensagemId: number) =>
    api<ChatInterno.Mensagem>(`/chat-interno/conversas/${conversaId}/mensagens/${mensagemId}/reacoes`, {
      method: 'DELETE',
    }),
  obterCanalSetor: (setorId: number) =>
    api<ChatInterno.Conversa>(`/chat-interno/setores/${setorId}/canal`),
  publicarCanalSetor: (setorId: number, corpo: string) =>
    api<ChatInterno.Mensagem>(`/chat-interno/setores/${setorId}/canal/mensagens`, {
      method: 'POST',
      body: JSON.stringify({ corpo }),
    }),
};

export namespace Dashboard {
  export interface StatusCount {
    status_id: number;
    status_nome: string;
    total: number;
  }
  export interface Resumo {
    total_tickets: number;
    abertos_hoje: number;
    por_status: StatusCount[];
  }
  export interface ChatEstadoCount {
    estado: string;
    rotulo: string;
    total: number;
  }
  export interface ChatsResumo {
    total_chats: number;
    iniciados_hoje: number;
    por_estado: ChatEstadoCount[];
  }
  export interface ChatRecente {
    id: number;
    protocolo: string;
    cliente_nome: string | null;
    estado: string;
    created_at: string;
  }
  export interface Response {
    resumo: Resumo;
    resumo_chats: ChatsResumo;
    ultimos_tickets: Tickets.Ticket[];
    ultimos_chats: ChatRecente[];
  }
  export interface CsatResumo {
    media: number | null;
    total_avaliacoes: number;
    periodo_dias: number;
  }
  export interface GeralResponse {
    tickets_abertos: number;
    tickets_sem_responsavel: number;
    chats_aguardando_atendente: number;
    chats_em_atendimento: number;
    csat_tickets: CsatResumo;
    csat_chats: CsatResumo;
    sla_violacoes_abertas: number;
    sla_em_risco_abertas: number;
    de: string;
    ate: string;
    gerado_em: string;
    cache_ttl_segundos: number;
  }
  export interface SerieVolumeDia {
    dia: string;
    abertos: number;
    fechados: number;
  }
  export interface ContagemIdNome {
    id: number;
    nome: string;
    total: number;
  }
  export interface ContagemPrioridade {
    prioridade: string;
    total: number;
  }
  export interface ContagemCanal {
    canal: string;
    rotulo: string;
    total: number;
  }
  export interface CsatDistribuicao {
    media: number | null;
    total_avaliacoes: number;
    por_nota: Record<string, number>;
  }
  export interface TicketsResponse {
    de: string;
    ate: string;
    volume_por_dia: SerieVolumeDia[];
    por_status: ContagemIdNome[];
    por_prioridade: ContagemPrioridade[];
    por_motivo: ContagemIdNome[];
    por_rede: ContagemIdNome[];
    por_empresa: ContagemIdNome[];
    mttr_horas: number | null;
    fila_tempo_medio_horas: number | null;
    csat: CsatDistribuicao;
    por_canal: ContagemCanal[];
    por_atendente: ContagemIdNome[];
    gerado_em: string;
    cache_ttl_segundos: number;
  }
  export interface SnapshotCanais {
    tickets_abertos: number;
    tickets_sem_responsavel: number;
    chats_aguardando: number;
    chats_em_atendimento: number;
  }
  export interface ContagemRotulo {
    chave?: string | null;
    rotulo: string;
    total: number;
  }
  export interface ContagemEncerramentoChat {
    tipo: string;
    rotulo: string;
    total: number;
  }
  export interface DemandaEmpresaRanking {
    empresa_id: number | null;
    empresa_nome: string;
    total: number;
    natureza_dominante_id: number | null;
    natureza_dominante_nome: string | null;
    natureza_dominante_slug: string | null;
  }
  export interface DemandaInsight {
    tipo: string;
    titulo: string;
    detalhe: string;
    natureza_id: number | null;
    motivo_id: number | null;
    total: number;
    limiar: number;
  }
  export interface SugestaoMotivoOutros {
    natureza_id: number;
    natureza_nome: string;
    texto_normalizado: string;
    texto_exemplo: string;
    ocorrencias: number;
    limiar: number;
  }
  export interface DemandaDrillItem {
    demanda_id: number;
    chat_id: number;
    protocolo: string;
    cliente_nome: string | null;
    empresa_id: number | null;
    empresa_nome: string | null;
    natureza_id: number;
    natureza_nome: string;
    motivo_id: number | null;
    motivo_nome: string | null;
    desfecho: string;
    descricao_curta: string | null;
    created_at: string;
  }
  export interface DemandasDrillResponse {
    items: DemandaDrillItem[];
    total: number;
  }
  export interface ChatsResponse {
    de: string;
    ate: string;
    volume_por_dia: SerieVolumeDia[];
    tempo_espera_medio_horas: number | null;
    tempo_atendimento_medio_horas: number | null;
    avaliacoes: CsatDistribuicao;
    encerramentos: ContagemEncerramentoChat[];
    pct_com_ticket_vinculado: number | null;
    por_atendente: ContagemIdNome[];
    por_estado_atual: ContagemRotulo[];
    demandas_por_natureza: ContagemIdNome[];
    demandas_por_motivo: ContagemIdNome[];
    demandas_por_empresa: DemandaEmpresaRanking[];
    demanda_maior: ContagemIdNome | null;
    insights_demandas: DemandaInsight[];
    sugestoes_motivo_outros: SugestaoMotivoOutros[];
    snapshot: SnapshotCanais;
    gerado_em: string;
    cache_ttl_segundos: number;
  }
}

export namespace Relatorios {
  export interface TicketLinha {
    protocolo: string;
    assunto: string;
    status_nome: string;
    prioridade: string;
    rede_nome: string;
    empresa_nome: string;
    setor_nome: string;
    aberto_em: string | null;
    fechado_em: string | null;
    responsavel_nome: string;
    canal: string;
  }
  export interface TicketsResponse {
    de: string;
    ate: string;
    total: number;
    offset: number;
    limit: number;
    itens: TicketLinha[];
  }
  export interface ChatLinha {
    protocolo: string;
    cliente_nome: string | null;
    wa_id: string;
    estado: string;
    estado_rotulo: string;
    setor_nome: string;
    atendente_nome: string;
    empresa_nome: string;
    aberto_em: string | null;
    inicio_atendimento: string | null;
    encerrado_em: string | null;
    avaliacao_nota: number | null;
  }
  export interface ChatsResponse {
    de: string;
    ate: string;
    total: number;
    offset: number;
    limit: number;
    itens: ChatLinha[];
  }
}

export namespace Redes {
  export interface Rede {
    id: number;
    nome: string;
    login_retaguarda?: string | null;
    ativo: boolean;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface FuncionarioComVinculo extends FuncionariosRede.Funcionario {
    vinculado_a: string;
  }
  export interface Create {
    nome: string;
    login_retaguarda?: string | null;
    ativo?: boolean;
  }
  export interface Update {
    nome?: string;
    login_retaguarda?: string | null;
    ativo?: boolean;
  }
}

export namespace Empresas {
  /** Item de GET /empresas para atendentes (sem PII). */
  export interface EmpresaListaResumo {
    id: number;
    nome: string;
    ativo: boolean;
    rede: { id: number; nome: string };
  }
  /** Lista: admin recebe Empresa completa; atendente recebe EmpresaListaResumo. */
  export type EmpresaListaItem = Empresa | EmpresaListaResumo;

  export interface Empresa {
    id: number;
    rede_id: number;
    tipo_negocio_id: number | null;
    nome: string;
    cnpj_cpf: string | null;
    razao_social: string | null;
    nome_fantasia: string | null;
    inscricao_estadual: string | null;
    endereco: string | null;
    numero: string | null;
    complemento: string | null;
    bairro: string | null;
    cidade: string | null;
    estado: string | null;
    cep: string | null;
    email: string | null;
    telefone: string | null;
    resp_legal_nome: string | null;
    resp_legal_cpf: string | null;
    resp_legal_rg: string | null;
    resp_legal_orgao_emissor: string | null;
    resp_legal_nacionalidade: string | null;
    resp_legal_estado_civil: string | null;
    resp_legal_cargo: string | null;
    resp_legal_email: string | null;
    resp_legal_telefone: string | null;
    resp_legal_endereco: string | null;
    resp_legal_numero: string | null;
    resp_legal_complemento: string | null;
    resp_legal_bairro: string | null;
    resp_legal_cidade: string | null;
    resp_legal_estado: string | null;
    resp_legal_cep: string | null;
    ativo: boolean;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface ConsultaCNPJ {
    cnpj: string;
    razao_social: string;
    nome_fantasia: string | null;
    situacao: string | null;
    endereco: string;
    numero: string | null;
    complemento: string | null;
    bairro: string | null;
    cidade: string | null;
    estado: string | null;
    cep: string | null;
    email: string | null;
    telefone: string | null;
    abertura: string | null;
    natureza_juridica: string | null;
    atividade_principal: string | null;
  }
  export interface Create {
    rede_id: number;
    tipo_negocio_id?: number | null;
    nome: string;
    cnpj_cpf?: string | null;
    razao_social?: string | null;
    nome_fantasia?: string | null;
    inscricao_estadual?: string | null;
    endereco?: string | null;
    numero?: string | null;
    complemento?: string | null;
    bairro?: string | null;
    cidade?: string | null;
    estado?: string | null;
    cep?: string | null;
    email?: string | null;
    telefone?: string | null;
    resp_legal_nome?: string | null;
    resp_legal_cpf?: string | null;
    resp_legal_rg?: string | null;
    resp_legal_orgao_emissor?: string | null;
    resp_legal_nacionalidade?: string | null;
    resp_legal_estado_civil?: string | null;
    resp_legal_cargo?: string | null;
    resp_legal_email?: string | null;
    resp_legal_telefone?: string | null;
    resp_legal_endereco?: string | null;
    resp_legal_numero?: string | null;
    resp_legal_complemento?: string | null;
    resp_legal_bairro?: string | null;
    resp_legal_cidade?: string | null;
    resp_legal_estado?: string | null;
    resp_legal_cep?: string | null;
    ativo?: boolean;
  }
  export interface Update {
    rede_id?: number;
    tipo_negocio_id?: number | null;
    nome?: string;
    cnpj_cpf?: string | null;
    razao_social?: string | null;
    nome_fantasia?: string | null;
    inscricao_estadual?: string | null;
    endereco?: string | null;
    numero?: string | null;
    complemento?: string | null;
    bairro?: string | null;
    cidade?: string | null;
    estado?: string | null;
    cep?: string | null;
    email?: string | null;
    telefone?: string | null;
    resp_legal_nome?: string | null;
    resp_legal_cpf?: string | null;
    resp_legal_rg?: string | null;
    resp_legal_orgao_emissor?: string | null;
    resp_legal_nacionalidade?: string | null;
    resp_legal_estado_civil?: string | null;
    resp_legal_cargo?: string | null;
    resp_legal_email?: string | null;
    resp_legal_telefone?: string | null;
    resp_legal_endereco?: string | null;
    resp_legal_numero?: string | null;
    resp_legal_complemento?: string | null;
    resp_legal_bairro?: string | null;
    resp_legal_cidade?: string | null;
    resp_legal_estado?: string | null;
    resp_legal_cep?: string | null;
    ativo?: boolean;
  }
}

export namespace TiposNegocio {
  export interface Tipo {
    id: number;
    nome: string;
    ativo: boolean;
  }
  export interface Create {
    nome: string;
    ativo?: boolean;
  }
  export interface Update {
    nome?: string;
    ativo?: boolean;
  }
}

export namespace Setores {
  export type DistribuicaoModo = 'manual' | 'auto_apos_timeout' | 'auto_imediato'
  export type DistribuicaoEstrategia = 'round_robin' | 'menor_carga_abertos' | 'menor_carga_setor'

  export interface Distribuicao {
    modo: DistribuicaoModo
    timeout_minutos: number
    estrategia: DistribuicaoEstrategia
    atendentes_elegiveis: number[] | null
  }

  export interface Setor {
    id: number;
    nome: string;
    slug: string;
    ativo: boolean;
    distribuicao?: Distribuicao | null;
  }
  export interface Create {
    nome: string;
    slug: string;
    ativo?: boolean;
  }
  export interface Update {
    nome?: string;
    slug?: string;
    ativo?: boolean;
  }
  export interface DistribuicaoUpdate {
    modo: DistribuicaoModo;
    timeout_minutos: number;
    estrategia: DistribuicaoEstrategia;
    atendentes_elegiveis?: number[] | null;
  }
}

export namespace Atendentes {
  export interface Atendente {
    id: number;
    email: string;
    nome: string;
    role: string;
    ativo: boolean;
    setor_ids: number[];
    must_change_password?: boolean;
    usa_escala?: boolean;
    escala_horas_trabalho?: number | null;
    escala_horas_folga?: number | null;
    escala_inicio_em?: string | null;
    horario_previsto_entrada?: string | null;
    horario_previsto_saida?: string | null;
    tolerancia_atraso_minutos?: number;
  }
  export interface Create {
    email: string;
    nome: string;
    senha: string;
    role?: string;
    ativo?: boolean;
    setor_ids?: number[];
    usa_escala?: boolean;
    escala_horas_trabalho?: number | null;
    escala_horas_folga?: number | null;
    escala_inicio_em?: string | null;
    horario_previsto_entrada?: string | null;
    horario_previsto_saida?: string | null;
    tolerancia_atraso_minutos?: number;
  }
  export interface Update {
    email?: string;
    nome?: string;
    senha?: string;
    role?: string;
    ativo?: boolean;
    setor_ids?: number[];
    usa_escala?: boolean;
    escala_horas_trabalho?: number | null;
    escala_horas_folga?: number | null;
    escala_inicio_em?: string | null;
    horario_previsto_entrada?: string | null;
    horario_previsto_saida?: string | null;
    tolerancia_atraso_minutos?: number;
  }
  export interface AvaliacaoResumo {
    media: number | null;
    total: number;
  }
  export interface AvaliacoesResumo {
    geral: AvaliacaoResumo;
    whatsapp: AvaliacaoResumo;
    tickets: AvaliacaoResumo;
  }
}

export namespace FuncionariosRede {
  export type EscopoEmpresas = 'all' | 'selected';
  export interface Funcionario {
    id: number;
    nome: string;
    email: string | null;
    telefone?: string | null;
    tipo: string;
    escopo_empresas: EscopoEmpresas;
    ativo: boolean;
    rede_id?: number;
    empresa_id?: number;
    empresa_ids: number[];
    portal_habilitado?: boolean;
    must_change_password?: boolean;
    notificar_email_portal?: boolean;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface Create {
    nome: string;
    email?: string | null;
    telefone?: string | null;
    tipo: string;
    escopo_empresas?: EscopoEmpresas;
    ativo?: boolean;
    rede_id?: number;
    empresa_id?: number;
    empresa_ids?: number[];
    senha_portal?: string | null;
    must_change_password?: boolean;
  }
  export interface Update {
    nome?: string;
    email?: string | null;
    telefone?: string | null;
    tipo?: string;
    escopo_empresas?: EscopoEmpresas;
    ativo?: boolean;
    rede_id?: number;
    empresa_id?: number;
    empresa_ids?: number[];
    senha_portal?: string | null;
    must_change_password?: boolean;
    notificar_email_portal?: boolean;
    revogar_sessoes_portal?: boolean;
  }
}

/** Portal do cliente — tokens separados do painel interno (#263). */
const PORTAL_TOKEN_KEY = 'portal_token'
const PORTAL_REFRESH_TOKEN_KEY = 'portal_refresh_token'

function getPortalToken(): string | null {
  return sessionStorage.getItem(PORTAL_TOKEN_KEY) || localStorage.getItem(PORTAL_TOKEN_KEY)
}

function getPortalRefreshToken(): string | null {
  return sessionStorage.getItem(PORTAL_REFRESH_TOKEN_KEY) || localStorage.getItem(PORTAL_REFRESH_TOKEN_KEY)
}

export function clearPortalAuthToken(): void {
  sessionStorage.removeItem(PORTAL_TOKEN_KEY)
  localStorage.removeItem(PORTAL_TOKEN_KEY)
  sessionStorage.removeItem(PORTAL_REFRESH_TOKEN_KEY)
  localStorage.removeItem(PORTAL_REFRESH_TOKEN_KEY)
}

function setPortalTokens(
  tokens: { access_token: string; refresh_token?: string | null },
  lembrarMe = true,
) {
  const store = lembrarMe ? localStorage : sessionStorage
  store.setItem(PORTAL_TOKEN_KEY, tokens.access_token)
  if (tokens.refresh_token) store.setItem(PORTAL_REFRESH_TOKEN_KEY, tokens.refresh_token)
}

function invalidatePortalAndRedirectToLogin(): void {
  clearPortalAuthToken()
  const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`
  const qs =
    returnTo && !returnTo.startsWith('/portal/login')
      ? `?returnTo=${encodeURIComponent(returnTo)}`
      : ''
  window.location.replace(`/portal/login${qs}`)
}

let portalRefreshInFlight: Promise<{
  access_token: string
  refresh_token?: string | null
  must_change_password?: boolean
} | null> | null = null

async function refreshPortalAccessToken(): Promise<{
  access_token: string
  refresh_token?: string | null
  must_change_password?: boolean
} | null> {
  if (portalRefreshInFlight) return portalRefreshInFlight
  const refresh_token = getPortalRefreshToken()
  if (!refresh_token) return null
  portalRefreshInFlight = (async () => {
    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json', 'X-DX-Skip-Refresh': '1' }
      if (isMultiTenantMode()) {
        ;(headers as Record<string, string>)['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
      }
      const res = await fetch(`${apiOrigin()}${API_VERSION_PREFIX}/portal/auth/refresh`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ refresh_token }),
      })
      if (!res.ok) return null
      const data = (await res.json()) as {
        access_token: string
        refresh_token?: string | null
        must_change_password?: boolean
      }
      const lembrarMe = Boolean(localStorage.getItem(PORTAL_REFRESH_TOKEN_KEY))
      setPortalTokens(data, lembrarMe)
      return data
    } catch {
      return null
    } finally {
      portalRefreshInFlight = null
    }
  })()
  return portalRefreshInFlight
}

async function portalApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getPortalToken()
  const isFormData =
    typeof FormData !== 'undefined' && options.body != null && options.body instanceof FormData
  const headers: HeadersInit = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers as object),
  }
  if (token) {
    ;(headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
  }
  if (isMultiTenantMode()) {
    ;(headers as Record<string, string>)['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
  }
  const res = await fetch(`${apiOrigin()}${API_VERSION_PREFIX}${path}`, { ...options, headers })

  if (res.status === 401 && path.startsWith('/portal/auth/login')) {
    const err = await res.json().catch(() => ({}))
    let msg = mensagemErroApi(err, 401)
    if (msg.startsWith('Não foi possível concluir')) msg = 'E-mail ou senha inválidos.'
    throw new ApiError(msg, 401, err)
  }

  if (res.status === 401) {
    const err = await res.json().catch(() => ({}))
    const skipRefresh =
      headers instanceof Headers
        ? headers.has('X-DX-Skip-Refresh')
        : typeof headers === 'object' &&
          headers != null &&
          'X-DX-Skip-Refresh' in (headers as Record<string, unknown>)
    if (!skipRefresh && !path.startsWith('/portal/auth/refresh')) {
      const refreshed = await refreshPortalAccessToken()
      if (refreshed?.access_token) {
        return portalApi<T>(path, options)
      }
    }
    invalidatePortalAndRedirectToLogin()
    throw new ApiError(mensagemErroApi(err, 401), 401, err)
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new ApiError(mensagemErroApi(err, res.status), res.status, err)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export namespace PortalCliente {
  export interface PublicBranding {
    nome_exibicao: string
    portal_titulo: string
    logo_url: string | null
    texto_boas_vindas: string | null
    cor_primaria: string
    cor_header: string
    cor_sidebar: string
    cor_texto_header: string
    cor_texto_corpo: string
    cor_fundo: string
    cor_link: string
    exibir_marca_deskrudder: boolean
    chat_habilitado: boolean
  }
  export interface Token {
    access_token: string
    refresh_token?: string | null
    must_change_password?: boolean
  }
  export interface Empresa {
    id: number
    nome: string
    rede_id: number
  }
  export interface Me {
    id: number
    nome: string
    email: string
    tipo: string
    rede_id: number | null
    empresas: Empresa[]
    must_change_password: boolean
    notificar_email_portal: boolean
  }
  export interface Setor {
    id: number
    nome: string
    slug?: string | null
  }
  export interface Pdv {
    id: number
    codigo: string
    papel?: string | null
    ativo: boolean
  }
  export interface TicketListItem {
    id: number
    protocolo: string
    assunto: string
    status_nome?: string | null
    status_slug?: string | null
    empresa_id?: number | null
    empresa_nome?: string | null
    setor_nome?: string | null
    prioridade?: string | null
    created_at?: string | null
    updated_at?: string | null
    fechado_em?: string | null
    ultima_mensagem_em?: string | null
  }
  export interface TicketDetail extends TicketListItem {
    descricao?: string | null
    pode_responder: boolean
    csat_token?: string | null
    csat_pendente: boolean
  }
  export interface Anexo {
    id: number
    nome_original: string
    content_type?: string | null
    tamanho_bytes: number
    mensagem_id?: number | null
    created_at?: string | null
    download_url: string
  }
  export interface Mensagem {
    id: number
    tipo: string
    corpo: string
    autor_nome?: string | null
    autor_papel: 'equipe' | 'voce' | 'sistema'
    created_at?: string | null
    anexos: Anexo[]
  }
  export interface CreateTicket {
    empresa_id: number
    setor_id?: number | null
    assunto: string
    descricao?: string | null
    pdv_codigo?: string | null
    motivo_id?: number | null
    motivo_outro_texto?: string | null
  }
  export interface WhatsappChatListItem {
    id: number
    protocolo: string
    estado: string
    empresa_id?: number | null
    empresa_nome?: string | null
    setor_nome?: string | null
    created_at?: string | null
    encerramento_at?: string | null
    ultima_mensagem_em?: string | null
    ultima_mensagem_preview?: string | null
  }
  export interface WhatsappChatDetail extends WhatsappChatListItem {
    encerrado: boolean
  }
  export interface WhatsappMensagem {
    id: number
    direcao: string
    corpo: string
    tipo_midia?: string | null
    midia_disponivel: boolean
    autor_nome?: string | null
    autor_papel: 'equipe' | 'voce' | 'sistema'
    created_at?: string | null
  }
  export interface EquipeFuncionario {
    id: number
    nome: string
    email?: string | null
    telefone?: string | null
    tipo: string
    ativo: boolean
    empresa_id?: number | null
    empresa_ids: number[]
    portal_habilitado: boolean
    must_change_password: boolean
    notificar_email_portal: boolean
    editavel: boolean
  }
  export interface EquipeCreate {
    nome: string
    email: string
    telefone?: string | null
    tipo: 'colaborador' | 'supervisor'
    ativo?: boolean
    empresa_id?: number
    empresa_ids?: number[]
    senha_portal?: string
    must_change_password?: boolean
  }
  export interface EquipeUpdate {
    nome?: string
    email?: string
    telefone?: string | null
    tipo?: 'colaborador' | 'supervisor'
    ativo?: boolean
    empresa_id?: number
    empresa_ids?: number[]
    senha_portal?: string
    must_change_password?: boolean
    notificar_email_portal?: boolean
  }
}

export const portalCliente = {
  branding: () => publicApi<PortalCliente.PublicBranding>('/portal/public/branding'),
  logoAssetUrl: () => `${apiOrigin()}${API_VERSION_PREFIX}/kb/public/logo`,
  login: (email: string, senha: string) =>
    publicApi<PortalCliente.Token>('/portal/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, senha }),
    }),
  setSession: (tokens: PortalCliente.Token, lembrarMe = true) => {
    setPortalTokens(tokens, lembrarMe)
  },
  clearSession: () => clearPortalAuthToken(),
  hasSession: () => Boolean(getPortalToken()),
  me: () => portalApi<PortalCliente.Me>('/portal/me'),
  trocarSenha: (senha_atual: string, senha_nova: string) =>
    portalApi<PortalCliente.Token>('/portal/me/trocar-senha', {
      method: 'POST',
      body: JSON.stringify({ senha_atual, senha_nova }),
    }),
  atualizarPreferencias: (data: { notificar_email_portal?: boolean }) =>
    portalApi<PortalCliente.Me>('/portal/me/preferencias', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  listSetores: () => portalApi<PortalCliente.Setor[]>('/portal/catalogos/setores'),
  listPdvs: (empresaId: number) =>
    portalApi<PortalCliente.Pdv[]>(`/portal/empresas/${empresaId}/pdvs`),
  listTickets: (params?: {
    situacao?: string
    busca?: string
    offset?: number
    limit?: number
  }) =>
    portalApi<{ items: PortalCliente.TicketListItem[]; total: number }>(
      withParams('/portal/tickets', params),
    ),
  getTicket: (id: number) => portalApi<PortalCliente.TicketDetail>(`/portal/tickets/${id}`),
  createTicket: (data: PortalCliente.CreateTicket) =>
    portalApi<PortalCliente.TicketDetail>('/portal/tickets', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  listMensagens: (ticketId: number) =>
    portalApi<PortalCliente.Mensagem[]>(`/portal/tickets/${ticketId}/mensagens`),
  sendMensagem: (ticketId: number, corpo: string) =>
    portalApi<PortalCliente.Mensagem>(`/portal/tickets/${ticketId}/mensagens`, {
      method: 'POST',
      body: JSON.stringify({ corpo }),
    }),
  uploadAnexo: async (ticketId: number, file: File, mensagemId?: number) => {
    const fd = new FormData()
    fd.append('file', file)
    if (mensagemId != null) fd.append('mensagem_id', String(mensagemId))
    return portalApi<PortalCliente.Anexo>(`/portal/tickets/${ticketId}/anexos`, {
      method: 'POST',
      body: fd,
    })
  },
  anexoDownloadUrl: (ticketId: number, anexoId: number) =>
    `${apiOrigin()}${API_VERSION_PREFIX}/portal/tickets/${ticketId}/anexos/${anexoId}/download`,
  fetchAnexoBlob: async (ticketId: number, anexoId: number) => {
    const token = getPortalToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    if (isMultiTenantMode()) {
      headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
    }
    const res = await fetch(
      `${apiOrigin()}${API_VERSION_PREFIX}/portal/tickets/${ticketId}/anexos/${anexoId}/download`,
      { headers },
    )
    if (!res.ok) throw new ApiError('Falha ao baixar anexo', res.status, null)
    return res.blob()
  },
  csatLink: (ticketId: number) =>
    portalApi<{ link: string; expires_at: string }>(`/portal/tickets/${ticketId}/csat-link`, {
      method: 'POST',
    }),
  listChats: (params?: { situacao?: string; busca?: string; offset?: number; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.situacao) q.set('situacao', params.situacao)
    if (params?.busca) q.set('busca', params.busca)
    if (params?.offset != null) q.set('offset', String(params.offset))
    if (params?.limit != null) q.set('limit', String(params.limit))
    const qs = q.toString()
    return portalApi<{ items: PortalCliente.WhatsappChatListItem[]; total: number }>(
      `/portal/chats${qs ? `?${qs}` : ''}`,
    )
  },
  getChat: (id: number) => portalApi<PortalCliente.WhatsappChatDetail>(`/portal/chats/${id}`),
  listChatMensagens: (chatId: number) =>
    portalApi<PortalCliente.WhatsappMensagem[]>(`/portal/chats/${chatId}/mensagens`),
  fetchChatMidiaBlob: async (chatId: number, mensagemId: number) => {
    const token = getPortalToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    if (isMultiTenantMode()) {
      headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
    }
    const res = await fetch(
      `${apiOrigin()}${API_VERSION_PREFIX}/portal/chats/${chatId}/mensagens/${mensagemId}/midia`,
      { headers },
    )
    if (!res.ok) throw new ApiError('Falha ao abrir mídia', res.status, null)
    return res.blob()
  },
  listEquipe: (params?: { incluir_inativos?: boolean; busca?: string; offset?: number; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.incluir_inativos) q.set('incluir_inativos', 'true')
    if (params?.busca) q.set('busca', params.busca)
    if (params?.offset != null) q.set('offset', String(params.offset))
    if (params?.limit != null) q.set('limit', String(params.limit))
    const qs = q.toString()
    return portalApi<{ items: PortalCliente.EquipeFuncionario[]; total: number }>(
      `/portal/equipe/funcionarios${qs ? `?${qs}` : ''}`,
    )
  },
  listEquipeEmpresas: () => portalApi<PortalCliente.Empresa[]>('/portal/equipe/empresas'),
  getEquipeFuncionario: (id: number) => portalApi<PortalCliente.EquipeFuncionario>(`/portal/equipe/funcionarios/${id}`),
  createEquipeFuncionario: (data: PortalCliente.EquipeCreate) =>
    portalApi<PortalCliente.EquipeFuncionario>('/portal/equipe/funcionarios', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateEquipeFuncionario: (id: number, data: PortalCliente.EquipeUpdate) =>
    portalApi<PortalCliente.EquipeFuncionario>(`/portal/equipe/funcionarios/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
}

export const ticketClassificacao = {
  listNaturezas: (params?: {
    incluir_inativos?: boolean
    busca?: string
    offset?: number
    limit?: number
    ordenar_por?: 'nome' | 'slug' | 'ordem' | 'ativo'
    ordem?: 'asc' | 'desc'
  }) => listPaginated<TicketClassificacao.Natureza>('/ticket-naturezas', params),
  createNatureza: (data: TicketClassificacao.NaturezaCreate) =>
    api<TicketClassificacao.Natureza>('/ticket-naturezas', { method: 'POST', body: JSON.stringify(data) }),
  updateNatureza: (id: number, data: TicketClassificacao.NaturezaUpdate) =>
    api<TicketClassificacao.Natureza>(`/ticket-naturezas/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  listMotivos: (params?: {
    natureza_id?: number
    incluir_inativos?: boolean
    busca?: string
    offset?: number
    limit?: number
    ordenar_por?: 'nome' | 'slug' | 'ordem' | 'ativo'
    ordem?: 'asc' | 'desc'
  }) => listPaginated<TicketClassificacao.Motivo>('/ticket-motivos', params),
  createMotivo: (data: TicketClassificacao.MotivoCreate) =>
    api<TicketClassificacao.Motivo>('/ticket-motivos', { method: 'POST', body: JSON.stringify(data) }),
  updateMotivo: (id: number, data: TicketClassificacao.MotivoUpdate) =>
    api<TicketClassificacao.Motivo>(`/ticket-motivos/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
}

export namespace TicketClassificacao {
  export interface Natureza {
    id: number
    nome: string
    slug: string
    ordem: number
    ativo: boolean
    created_at?: string | null
    updated_at?: string | null
  }
  export interface NaturezaCreate {
    nome: string
    slug: string
    ordem?: number
    ativo?: boolean
  }
  export interface NaturezaUpdate {
    nome?: string
    slug?: string
    ordem?: number
    ativo?: boolean
  }
  export interface Motivo {
    id: number
    natureza_id: number
    nome: string
    slug: string
    ordem: number
    ativo: boolean
    natureza_nome?: string | null
    created_at?: string | null
    updated_at?: string | null
  }
  export interface MotivoCreate {
    natureza_id: number
    nome: string
    slug: string
    ordem?: number
    ativo?: boolean
  }
  export interface MotivoUpdate {
    natureza_id?: number
    nome?: string
    slug?: string
    ordem?: number
    ativo?: boolean
  }
}

export const comercialSalarioMinimo = {
  list: (params?: {
    offset?: number;
    limit?: number;
    ordenar_por?: 'vigencia_inicio' | 'valor' | 'id';
    ordem?: 'asc' | 'desc';
  }) => listPaginated<ComercialCustos.SalarioMinimo>('/comercial/salario-minimo', params),
  naData: (data: string) =>
    api<ComercialCustos.SalarioMinimo | null>(withParams('/comercial/salario-minimo/na-data', { data })),
  create: (data: ComercialCustos.SalarioMinimoCreate) =>
    api<ComercialCustos.SalarioMinimo>('/comercial/salario-minimo', { method: 'POST', body: JSON.stringify(data) }),
  /** Fecha o vigente e cria novo valor a partir da data (histórico preservado). */
  atualizarValor: (data: ComercialCustos.SalarioMinimoAtualizarValor) =>
    api<ComercialCustos.SalarioMinimo>('/comercial/salario-minimo/atualizar-valor', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: number, data: ComercialCustos.SalarioMinimoUpdate) =>
    api<ComercialCustos.SalarioMinimo>(`/comercial/salario-minimo/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  delete: (id: number) => api<void>(`/comercial/salario-minimo/${id}`, { method: 'DELETE' }),
};

export const comercialCustosItens = {
  list: (params?: {
    incluir_inativos?: boolean;
    busca?: string;
    tipo?: string;
    offset?: number;
    limit?: number;
    ordenar_por?: 'nome' | 'slug' | 'ordem' | 'tipo' | 'ativo';
    ordem?: 'asc' | 'desc';
  }) => listPaginated<ComercialCustos.Item>('/comercial/custos/itens', params),
  create: (data: ComercialCustos.ItemCreate) =>
    api<ComercialCustos.Item>('/comercial/custos/itens', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: ComercialCustos.ItemUpdate) =>
    api<ComercialCustos.Item>(`/comercial/custos/itens/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => api<void>(`/comercial/custos/itens/${id}`, { method: 'DELETE' }),
  simular: (data: ComercialCustos.SimularRequest) =>
    api<ComercialCustos.SimularResponse>('/comercial/custos/simular', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export namespace ComercialCustos {
  export type Tipo = 'percentual_sm' | 'valor_fixo' | 'composto_tef';

  export interface SalarioMinimo {
    id: number;
    valor: string;
    vigencia_inicio: string;
    vigencia_fim?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface SalarioMinimoCreate {
    valor: string | number;
    vigencia_inicio: string;
    vigencia_fim?: string | null;
  }
  export interface SalarioMinimoAtualizarValor {
    valor: string | number;
    vigencia_inicio: string;
  }
  export interface SalarioMinimoUpdate {
    valor?: string | number;
    vigencia_inicio?: string;
    vigencia_fim?: string | null;
  }

  export interface Item {
    id: number;
    nome: string;
    slug: string;
    descricao?: string | null;
    tipo: Tipo | string;
    percentual_sm?: string | null;
    valor_fixo?: string | null;
    tef_base?: string | null;
    tef_adicional?: string | null;
    aplica_tier_posto?: boolean;
    ordem: number;
    ativo: boolean;
    vigencia_inicio?: string | null;
    vigencia_fim?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface ItemCreate {
    nome: string;
    slug: string;
    descricao?: string | null;
    tipo: Tipo;
    percentual_sm?: string | number | null;
    valor_fixo?: string | number | null;
    tef_base?: string | number | null;
    tef_adicional?: string | number | null;
    aplica_tier_posto?: boolean;
    ordem?: number;
    ativo?: boolean;
    vigencia_inicio?: string | null;
    vigencia_fim?: string | null;
  }
  export interface ItemUpdate {
    nome?: string;
    slug?: string;
    descricao?: string | null;
    tipo?: Tipo;
    percentual_sm?: string | number | null;
    valor_fixo?: string | number | null;
    tef_base?: string | number | null;
    tef_adicional?: string | number | null;
    aplica_tier_posto?: boolean;
    ordem?: number;
    ativo?: boolean;
    vigencia_inicio?: string | null;
    vigencia_fim?: string | null;
  }

  export interface TefOverride {
    tef_custo_base?: string | number | null;
    tef_custo_adicional?: string | number | null;
    tef_valor_cliente_base?: string | number | null;
    tef_valor_cliente_adicional?: string | number | null;
  }
  export interface SimularRequest {
    item_ids: number[];
    quantidade_pdvs?: number;
    data_referencia?: string | null;
    desconto_posto_100k?: boolean;
    tef_override?: TefOverride | null;
  }
  export interface SimularLinha {
    item_id: number;
    nome: string;
    slug: string;
    tipo: string;
    valor: string;
    percentual_usado?: string | null;
    override_custo?: boolean;
    tef_valor_cliente?: string | null;
  }
  export interface SimularResponse {
    data_referencia: string;
    salario_minimo: string | null;
    salario_minimo_id: number | null;
    quantidade_pdvs: number;
    desconto_posto_100k?: boolean;
    linhas: SimularLinha[];
    total: string;
    total_custo?: string;
    snapshot?: Record<string, unknown>;
  }
}

export namespace ComercialProposta {
  export interface Template {
    id: number;
    nome: string;
    versao: number;
    conteudo_html: string;
    vigencia_inicio?: string | null;
    ativo: boolean;
    created_at: string;
  }
  export interface TemplateCreate {
    nome: string;
    conteudo_html: string;
    vigencia_inicio?: string | null;
    ativo?: boolean;
  }
  export interface TemplateUpdate {
    nome?: string;
    conteudo_html?: string;
    vigencia_inicio?: string | null;
    ativo?: boolean;
  }
  export interface Proposta {
    id: number;
    negociacao_id: number;
    template_id: number;
    template_nome?: string | null;
    template_versao?: number | null;
    gerado_por_id: number;
    status: 'rascunho' | 'enviada' | 'substituida' | string;
    conteudo_html_snapshot: string;
    conteudo_hash: string;
    linha_ids: number[];
    canal?: string | null;
    enviado_em?: string | null;
    created_at: string;
  }
  export interface GerarRequest {
    negociacao_id: number;
    template_id?: number | null;
    linha_ids?: number[] | null;
    condicoes?: string | null;
  }
  export interface MarcarEnviadaRequest {
    canal: 'email' | 'impresso' | 'outro';
    enviado_em?: string | null;
    avancar_funil?: boolean;
  }
}

export const comercialPropostaTemplates = {
  list: (params?: { incluir_inativos?: boolean }) =>
    api<ComercialProposta.Template[]>(withParams('/comercial/proposta-templates', params)),
  create: (data: ComercialProposta.TemplateCreate) =>
    api<ComercialProposta.Template>('/comercial/proposta-templates', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: number, data: ComercialProposta.TemplateUpdate) =>
    api<ComercialProposta.Template>(`/comercial/proposta-templates/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  preview: (conteudo_html: string) =>
    api<{ html: string }>('/comercial/proposta-templates/preview', {
      method: 'POST',
      body: JSON.stringify({ conteudo_html }),
    }),
};

export const comercialPropostas = {
  list: (negociacao_id: number) =>
    api<ComercialProposta.Proposta[]>(withParams('/comercial/propostas', { negociacao_id })),
  get: (id: number) => api<ComercialProposta.Proposta>(`/comercial/propostas/${id}`),
  gerar: (data: ComercialProposta.GerarRequest) =>
    api<ComercialProposta.Proposta>('/comercial/propostas', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  marcarEnviada: (id: number, data: ComercialProposta.MarcarEnviadaRequest) =>
    api<ComercialProposta.Proposta>(`/comercial/propostas/${id}/marcar-enviada`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  downloadPdf: async (id: number) => {
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (isMultiTenantMode()) {
      headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname());
    }
    if (token) headers.Authorization = `Bearer ${token}`;
    const url = `${apiOrigin()}${API_VERSION_PREFIX}/comercial/propostas/${id}/pdf`;
    const res = await fetch(url, { headers });
    if (res.status === 401) {
      invalidateSessionAndRedirectToLogin();
      throw new ApiError('Sessão expirada ou inválida.', 401, {});
    }
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody);
    }
    return res.blob();
  },
};

export namespace ComercialContrato {
  export interface Template {
    id: number;
    nome: string;
    versao: number;
    conteudo_html: string;
    vigencia_inicio?: string | null;
    ativo: boolean;
    created_at: string;
  }
  export interface TemplateCreate {
    nome: string;
    conteudo_html: string;
    vigencia_inicio?: string | null;
    ativo?: boolean;
  }
  export interface TemplateUpdate {
    nome?: string;
    conteudo_html?: string;
    vigencia_inicio?: string | null;
    ativo?: boolean;
  }
  export interface ChaveCatalogo {
    grupo: string;
    chave: string;
    descricao: string;
  }
  export interface Interno {
    total_custo?: string | number | null;
    margem_calculada?: string | number | null;
    margem_percentual?: string | number | null;
    lucro_bruto?: string | number | null;
  }
  export interface Pdf {
    id: number;
    contrato_id: number;
    gerado_por_id: number;
    conteudo_hash: string;
    created_at: string;
  }
  export interface MultaRescisao {
    aplicavel: boolean;
    dentro_fidelidade: boolean;
    meses_restantes: number;
    multa_max_mensalidades: number;
    mensalidades_estimadas: number;
    valor_mensalidade: string | number;
    valor_estimado?: string | number | null;
    aviso: string;
  }
  export interface Contrato {
    id: number;
    negociacao_linha_cnpj_id: number;
    negociacao_id?: number | null;
    empresa_id?: number | null;
    rede_id?: number | null;
    template_id: number;
    template_nome?: string | null;
    template_versao?: number | null;
    gerado_por_id: number;
    status: 'rascunho' | 'enviado' | 'assinado' | 'cancelado' | 'renovado' | string;
    valor_mensalidade: string | number;
    snapshot_itens: unknown[];
    data_inicio: string;
    data_fim_fidelidade: string;
    fidelidade_meses: number;
    setup_valor?: string | number | null;
    setup_isento: boolean;
    deslocamento_cliente: boolean;
    alimentacao_cliente: boolean;
    hospedagem_cliente: boolean;
    multa_max_mensalidades: number;
    reajuste_percentual?: string | number;
    reajuste_rotulo?: string;
    pdf_assinado_nome_original?: string | null;
    tem_pdf_assinado?: boolean;
    referencia_externa?: string | null;
    enviado_em?: string | null;
    assinado_em?: string | null;
    created_at: string;
    pdf_atual_id?: number | null;
    pdfs: Pdf[];
    cnpj?: string | null;
    razao_social?: string | null;
    responsavel_id?: number | null;
    responsavel_nome?: string | null;
    lead_nome?: string | null;
    conteudo_html_snapshot?: string | null;
    dias_restantes_fidelidade?: number | null;
    multa_rescisao?: MultaRescisao | null;
    interno?: Interno | null;
  }
  export interface GerarRequest {
    linha_id: number;
    template_id?: number | null;
    data_inicio?: string | null;
    fidelidade_meses?: number;
    setup_valor?: string | null;
    setup_isento?: boolean;
    deslocamento_cliente?: boolean;
    alimentacao_cliente?: boolean;
    hospedagem_cliente?: boolean;
    multa_max_mensalidades?: number;
    sem_reajuste?: boolean;
    reajuste_percentual?: string | number | null;
    reajuste_rotulo?: string | null;
  }
  export interface MarcarEnviadoRequest {
    enviado_em?: string | null;
  }
  export interface MarcarAssinadoRequest {
    assinado_em?: string | null;
    avancar_funil?: boolean;
    referencia_externa?: string | null;
  }
  export interface Politica {
    reajuste_percentual: string | number;
    reajuste_rotulo: string;
  }
}

export const comercialContratoTemplates = {
  list: (params?: { incluir_inativos?: boolean }) =>
    api<ComercialContrato.Template[]>(withParams('/comercial/contrato-templates', params)),
  chaves: () => api<ComercialContrato.ChaveCatalogo[]>('/comercial/contrato-templates/chaves'),
  create: (data: ComercialContrato.TemplateCreate) =>
    api<ComercialContrato.Template>('/comercial/contrato-templates', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: number, data: ComercialContrato.TemplateUpdate) =>
    api<ComercialContrato.Template>(`/comercial/contrato-templates/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  preview: (conteudo_html: string) =>
    api<{ html: string }>('/comercial/contrato-templates/preview', {
      method: 'POST',
      body: JSON.stringify({ conteudo_html }),
    }),
};

export const comercialContratos = {
  list: (params?: {
    negociacao_id?: number;
    status?: string;
    cnpj?: string;
    so_minhas?: boolean;
    responsavel_id?: number;
  }) =>
    api<ComercialContrato.Contrato[]>(withParams('/comercial/contratos', params)),
  get: (id: number) => api<ComercialContrato.Contrato>(`/comercial/contratos/${id}`),
  gerar: (data: ComercialContrato.GerarRequest) =>
    api<ComercialContrato.Contrato>('/comercial/contratos', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  marcarEnviado: (id: number, data: ComercialContrato.MarcarEnviadoRequest = {}) =>
    api<ComercialContrato.Contrato>(`/comercial/contratos/${id}/marcar-enviado`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  marcarAssinado: (id: number, data: ComercialContrato.MarcarAssinadoRequest = {}) =>
    api<ComercialContrato.Contrato>(`/comercial/contratos/${id}/marcar-assinado`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  cancelar: (id: number) =>
    api<ComercialContrato.Contrato>(`/comercial/contratos/${id}/cancelar`, { method: 'POST' }),
  anexarPdfAssinado: (id: number, file: File, referenciaExterna?: string) => {
    const fd = new FormData()
    fd.append('arquivo', file)
    if (referenciaExterna?.trim()) fd.append('referencia_externa', referenciaExterna.trim())
    return api<ComercialContrato.Contrato>(`/comercial/contratos/${id}/pdf-assinado`, {
      method: 'POST',
      body: fd,
    })
  },
  downloadPdf: async (id: number, pdfId?: number) => {
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (isMultiTenantMode()) {
      headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname());
    }
    if (token) headers.Authorization = `Bearer ${token}`;
    const url = `${apiOrigin()}${API_VERSION_PREFIX}/comercial/contratos/${id}/pdf${
      pdfId != null ? `?pdf_id=${pdfId}` : ''
    }`;
    const res = await fetch(url, { headers });
    if (res.status === 401) {
      invalidateSessionAndRedirectToLogin();
      throw new ApiError('Sessão expirada ou inválida.', 401, {});
    }
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody);
    }
    return res.blob();
  },
  downloadPdfAssinado: async (id: number) => {
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (isMultiTenantMode()) {
      headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname());
    }
    if (token) headers.Authorization = `Bearer ${token}`;
    const url = `${apiOrigin()}${API_VERSION_PREFIX}/comercial/contratos/${id}/pdf-assinado`;
    const res = await fetch(url, { headers });
    if (res.status === 401) {
      invalidateSessionAndRedirectToLogin();
      throw new ApiError('Sessão expirada ou inválida.', 401, {});
    }
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new ApiError(mensagemErroApi(errBody, res.status), res.status, errBody);
    }
    return res.blob();
  },
};

export const comercialContratoPolitica = {
  get: () => api<ComercialContrato.Politica>('/comercial/contrato-politica'),
  update: (data: Partial<ComercialContrato.Politica>) =>
    api<ComercialContrato.Politica>('/comercial/contrato-politica', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};

export const crmFunil = {
  list: (params?: { incluir_inativos?: boolean }) =>
    api<Crm.FunilEstagio[]>(withParams('/crm/funil-estagios', params)),
  create: (data: Crm.FunilEstagioCreate) =>
    api<Crm.FunilEstagio>('/crm/funil-estagios', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Crm.FunilEstagioUpdate) =>
    api<Crm.FunilEstagio>(`/crm/funil-estagios/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};

export const crmLeads = {
  list: (params?: {
    offset?: number;
    limit?: number;
    q?: string;
    responsavel_id?: number;
    estagio_id?: number;
    so_minhas?: boolean;
    ativo?: boolean;
  }) => listPaginated<Crm.Lead>('/crm/leads', params),
  get: (id: number) => api<Crm.Lead>(`/crm/leads/${id}`),
  create: (data: Crm.LeadCreate) =>
    api<Crm.Lead>('/crm/leads', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Crm.LeadUpdate) =>
    api<Crm.Lead>(`/crm/leads/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
};

export const crmNegociacoes = {
  list: (params?: {
    offset?: number;
    limit?: number;
    lead_id?: number;
    responsavel_id?: number;
    estagio_id?: number;
    ativa?: boolean;
    q?: string;
    so_minhas?: boolean;
  }) => listPaginated<Crm.Negociacao>('/crm/negociacoes', params),
  get: (id: number) => api<Crm.Negociacao>(`/crm/negociacoes/${id}`),
  create: (data: Crm.NegociacaoCreate) =>
    api<Crm.Negociacao>('/crm/negociacoes', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Crm.NegociacaoUpdate) =>
    api<Crm.Negociacao>(`/crm/negociacoes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  moverEstagio: (id: number, data: Crm.MoverEstagioRequest) =>
    api<Crm.Negociacao>(`/crm/negociacoes/${id}/mover-estagio`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  addLinha: (negociacaoId: number, data: Crm.LinhaCreate) =>
    api<Crm.Linha>(`/crm/negociacoes/${negociacaoId}/linhas`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateLinha: (negociacaoId: number, linhaId: number, data: Crm.LinhaUpdate) =>
    api<Crm.Linha>(`/crm/negociacoes/${negociacaoId}/linhas/${linhaId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteLinha: (negociacaoId: number, linhaId: number) =>
    api<void>(`/crm/negociacoes/${negociacaoId}/linhas/${linhaId}`, { method: 'DELETE' }),
  listAtividades: (negociacaoId: number, params?: { offset?: number; limit?: number }) =>
    listPaginated<Crm.Atividade>(`/crm/negociacoes/${negociacaoId}/atividades`, params),
  addAtividade: (negociacaoId: number, data: Crm.AtividadeCreate) =>
    api<Crm.Atividade>(`/crm/negociacoes/${negociacaoId}/atividades`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export namespace Crm {
  export interface FunilEstagio {
    id: number;
    slug: string;
    nome: string;
    ordem: number;
    tipo: string;
    ativo: boolean;
  }

  export interface FunilEstagioCreate {
    slug: string;
    nome: string;
    ordem?: number;
    tipo?: string;
    ativo?: boolean;
  }

  export interface FunilEstagioUpdate {
    nome?: string;
    ordem?: number;
    tipo?: string;
    ativo?: boolean;
  }

  export interface Lead {
    id: number;
    nome: string;
    telefone?: string | null;
    email?: string | null;
    empresa_texto?: string | null;
    origem?: string | null;
    notas?: string | null;
    responsavel_id: number;
    estagio_id: number;
    estagio_slug?: string | null;
    estagio_nome?: string | null;
    perdido_em?: string | null;
    ativo: boolean;
    negociacao_ativa_id?: number | null;
    created_at?: string | null;
    updated_at?: string | null;
  }

  export interface LeadCreate {
    nome: string;
    telefone?: string | null;
    email?: string | null;
    empresa_texto?: string | null;
    origem?: string | null;
    notas?: string | null;
    responsavel_id?: number | null;
    criar_negociacao?: boolean;
    titulo_negociacao?: string | null;
  }

  export interface LeadUpdate {
    nome?: string;
    telefone?: string | null;
    email?: string | null;
    empresa_texto?: string | null;
    origem?: string | null;
    notas?: string | null;
    responsavel_id?: number | null;
    ativo?: boolean;
  }

  export interface DadosFiscais {
    nome?: string | null;
    nome_fantasia?: string | null;
    inscricao_estadual?: string | null;
    endereco?: string | null;
    numero?: string | null;
    complemento?: string | null;
    bairro?: string | null;
    cidade?: string | null;
    estado?: string | null;
    cep?: string | null;
    email?: string | null;
    telefone?: string | null;
    resp_legal_nome?: string | null;
    resp_legal_cpf?: string | null;
    resp_legal_rg?: string | null;
    resp_legal_orgao_emissor?: string | null;
    resp_legal_nacionalidade?: string | null;
    resp_legal_estado_civil?: string | null;
    resp_legal_cargo?: string | null;
    resp_legal_email?: string | null;
    resp_legal_telefone?: string | null;
    resp_legal_endereco?: string | null;
    resp_legal_numero?: string | null;
    resp_legal_complemento?: string | null;
    resp_legal_bairro?: string | null;
    resp_legal_cidade?: string | null;
    resp_legal_estado?: string | null;
    resp_legal_cep?: string | null;
  }

  export interface Linha {
    id: number;
    negociacao_id: number;
    cnpj?: string | null;
    razao_social?: string | null;
    dados_fiscais?: DadosFiscais | null;
    item_ids: number[];
    quantidade_pdvs: number;
    desconto_posto_100k: boolean;
    tef_override?: Record<string, unknown> | null;
    valor_negociado: string;
    snapshot_custo?: Record<string, unknown> | null;
    total_custo?: string | null;
    margem_calculada?: string | null;
    empresa_id?: number | null;
    ordem: number;
    created_at?: string | null;
    updated_at?: string | null;
  }

  export interface LinhaCreate {
    cnpj?: string | null;
    razao_social?: string | null;
    dados_fiscais?: DadosFiscais | null;
    item_ids?: number[];
    quantidade_pdvs?: number;
    desconto_posto_100k?: boolean;
    tef_override?: ComercialCustos.TefOverride | null;
    valor_negociado?: string | number;
    ordem?: number;
  }

  export interface LinhaUpdate {
    cnpj?: string | null;
    razao_social?: string | null;
    dados_fiscais?: DadosFiscais | null;
    item_ids?: number[];
    quantidade_pdvs?: number;
    desconto_posto_100k?: boolean;
    tef_override?: ComercialCustos.TefOverride | null;
    limpar_tef_override?: boolean;
    valor_negociado?: string | number;
    ordem?: number;
  }

  export interface Negociacao {
    id: number;
    lead_id: number;
    responsavel_id: number;
    estagio_id: number;
    estagio_slug?: string | null;
    estagio_nome?: string | null;
    ativa: boolean;
    titulo?: string | null;
    nome_base_webposto?: string | null;
    linhas: Linha[];
    created_at?: string | null;
    updated_at?: string | null;
  }

  export interface NegociacaoCreate {
    lead_id: number;
    titulo?: string | null;
    responsavel_id?: number | null;
    linhas?: LinhaCreate[];
  }

  export interface NegociacaoUpdate {
    titulo?: string | null;
    nome_base_webposto?: string | null;
    responsavel_id?: number | null;
  }

  export interface MoverEstagioRequest {
    estagio_id?: number | null;
    estagio_slug?: string | null;
    nota?: string | null;
  }

  export interface Atividade {
    id: number;
    negociacao_id: number;
    autor_id: number;
    tipo: string;
    texto: string;
    created_at?: string | null;
  }

  export interface AtividadeCreate {
    tipo?: string;
    texto: string;
  }
}

export const pdvRotulos = {
  list: (params?: { incluir_inativos?: boolean; busca?: string; offset?: number; limit?: number }) =>
    listPaginated<PdvCatalogo.Item>('/pdv-rotulos', params),
  create: (data: PdvCatalogo.Create) => api<PdvCatalogo.Item>('/pdv-rotulos', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: PdvCatalogo.Update) =>
    api<PdvCatalogo.Item>(`/pdv-rotulos/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
};

export const pdvTiposAcessoRemoto = {
  list: (params?: { incluir_inativos?: boolean; busca?: string; offset?: number; limit?: number }) =>
    listPaginated<PdvCatalogo.Item>('/pdv-tipos-acesso-remoto', params),
  create: (data: PdvCatalogo.Create) =>
    api<PdvCatalogo.Item>('/pdv-tipos-acesso-remoto', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: PdvCatalogo.Update) =>
    api<PdvCatalogo.Item>(`/pdv-tipos-acesso-remoto/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
};

export const empresaPdvs = {
  list: (empresaId: number, params?: { incluir_inativos?: boolean }) =>
    listPaginated<EmpresaPdv.Item>(`/empresas/${empresaId}/pdvs`, params),
  create: (empresaId: number, data: EmpresaPdv.Create) =>
    api<EmpresaPdv.Item>(`/empresas/${empresaId}/pdvs`, { method: 'POST', body: JSON.stringify(data) }),
  update: (empresaId: number, pdvId: number, data: EmpresaPdv.Update) =>
    api<EmpresaPdv.Item>(`/empresas/${empresaId}/pdvs/${pdvId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  revelarCredencial: (empresaId: number, pdvId: number) =>
    api<EmpresaPdv.Credencial>(`/empresas/${empresaId}/pdvs/${pdvId}/credencial`),
};

export namespace PdvCatalogo {
  export interface Item {
    id: number;
    nome: string;
    ativo: boolean;
    ordem_exibicao: number;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface Create {
    nome: string;
    ativo?: boolean;
    ordem_exibicao?: number;
  }
  export interface Update {
    nome?: string;
    ativo?: boolean;
    ordem_exibicao?: number;
  }
}

export namespace EmpresaPdv {
  export interface Item {
    id: number;
    empresa_id: number;
    codigo: string;
    rotulo_id: number;
    rotulo_nome?: string | null;
    papel: 'principal' | 'auxiliar';
    usa_tef: boolean;
    tipo_acesso_remoto_id?: number | null;
    tipo_acesso_remoto_nome?: string | null;
    acesso_remoto_id?: string | null;
    observacoes?: string | null;
    ativo: boolean;
    tem_senha_remota: boolean;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface Create {
    codigo: string;
    rotulo_id: number;
    papel: 'principal' | 'auxiliar';
    usa_tef?: boolean;
    tipo_acesso_remoto_id?: number | null;
    acesso_remoto_id?: string | null;
    acesso_remoto_senha?: string | null;
    observacoes?: string | null;
    ativo?: boolean;
  }
  export interface Update {
    codigo?: string;
    rotulo_id?: number;
    papel?: 'principal' | 'auxiliar';
    usa_tef?: boolean;
    tipo_acesso_remoto_id?: number | null;
    acesso_remoto_id?: string | null;
    acesso_remoto_senha?: string | null;
    observacoes?: string | null;
    ativo?: boolean;
  }
  export interface Credencial {
    acesso_remoto_senha: string;
  }
}

export namespace StatusTicket {
  export interface Status {
    id: number;
    nome: string;
    slug: string;
    ordem: number;
    ativo: boolean;
    pausa_sla: boolean;
  }
  export interface Create {
    nome: string;
    slug: string;
    ordem?: number;
    ativo?: boolean;
    pausa_sla?: boolean;
  }
  export interface Update {
    nome?: string;
    slug?: string;
    ordem?: number;
    ativo?: boolean;
    pausa_sla?: boolean;
  }
}

export namespace Sla {
  export type Prioridade = 'baixa' | 'normal' | 'alta' | 'urgente';

  export interface PrioridadesDisponiveis {
    prioridades: Prioridade[];
  }

  export interface Policy {
    id: number;
    setor_id: number;
    setor_nome?: string | null;
    prioridade: Prioridade | null;
    natureza_id: number | null;
    natureza_nome?: string | null;
    business_calendar_id: number | null;
    business_calendar_nome?: string | null;
    meta_primeira_resposta_min: number | null;
    meta_resolucao_min: number | null;
    ativo: boolean;
    created_at?: string | null;
    updated_at?: string | null;
  }

  export interface PolicyCreate {
    setor_id: number;
    prioridade?: Prioridade | null;
    natureza_id?: number | null;
    business_calendar_id?: number | null;
    meta_primeira_resposta_min?: number | null;
    meta_resolucao_min?: number | null;
    ativo?: boolean;
  }

  export interface PolicyUpdate {
    setor_id?: number;
    prioridade?: Prioridade | null;
    natureza_id?: number | null;
    business_calendar_id?: number | null;
    meta_primeira_resposta_min?: number | null;
    meta_resolucao_min?: number | null;
    ativo?: boolean;
  }

  export interface BusinessCalendar {
    id: number;
    nome: string;
    setor_id: number | null;
    horario_timezone: string;
    horario_inicio: string | null;
    horario_fim: string | null;
    horario_semana?: Record<string, { ativo?: boolean; inicio?: string; fim?: string }> | null;
    usar_feriados_nacionais: boolean;
    ativo: boolean;
  }

  export interface BusinessCalendarCreate {
    nome: string;
    setor_id?: number | null;
    horario_timezone?: string;
    horario_inicio?: string | null;
    horario_fim?: string | null;
    horario_semana?: Record<string, { ativo?: boolean; inicio?: string; fim?: string }> | null;
    usar_feriados_nacionais?: boolean;
    ativo?: boolean;
  }

  export interface BusinessCalendarUpdate {
    nome?: string;
    setor_id?: number | null;
    horario_timezone?: string;
    horario_inicio?: string | null;
    horario_fim?: string | null;
    horario_semana?: Record<string, { ativo?: boolean; inicio?: string; fim?: string }> | null;
    usar_feriados_nacionais?: boolean;
    ativo?: boolean;
  }
}

export namespace RoutingRules {
  export type Campo = 'email_from' | 'email_to' | 'assunto' | 'canal';
  export type Operador = 'contains' | 'equals' | 'regex';
  export type Canal = 'email' | 'manual';
  export type Prioridade = 'baixa' | 'normal' | 'alta' | 'urgente';

  export interface Condicao {
    campo: Campo;
    operador: Operador;
    valor: string;
  }

  export interface Acoes {
    setor_id?: number | null;
    prioridade?: Prioridade | null;
    natureza_id?: number | null;
    motivo_id?: number | null;
    atendente_id?: number | null;
  }

  export interface Regra {
    id: number;
    nome: string;
    ativo: boolean;
    ordem: number;
    rede_id: number | null;
    condicoes: Condicao[];
    acoes: Acoes;
  }

  export interface Create {
    nome: string;
    ativo?: boolean;
    rede_id?: number | null;
    condicoes: Condicao[];
    acoes: Acoes;
  }

  export interface Update {
    nome?: string;
    ativo?: boolean;
    rede_id?: number | null;
    condicoes?: Condicao[];
    acoes?: Acoes;
  }

  export interface Simulate {
    email_from?: string | null;
    email_to?: string | null;
    assunto?: string | null;
    canal?: Canal;
    rede_id?: number | null;
    setor_id_atual?: number | null;
    aplicar_setor?: boolean;
  }

  export interface Resultado {
    matched: boolean;
    rule_id?: number | null;
    rule_nome?: string | null;
    setor_id?: number | null;
    prioridade?: Prioridade | null;
    natureza_id?: number | null;
    motivo_id?: number | null;
    atendente_id?: number | null;
  }
}

export namespace RespostasProntas {
  export interface Resposta {
    id: number;
    titulo: string;
    corpo: string;
    setor_id: number | null;
    setor_nome?: string | null;
    ordem: number;
    ativo: boolean;
  }
  export interface Create {
    titulo: string;
    corpo: string;
    setor_id?: number | null;
    ordem?: number;
    ativo?: boolean;
  }
  export interface Update {
    titulo?: string;
    corpo?: string;
    setor_id?: number | null;
    ordem?: number;
    ativo?: boolean;
  }
}

export namespace Tickets {
  export interface TicketParentBrief {
    id: number;
    protocolo: string;
    assunto: string;
    status_nome?: string | null;
    fechado_em?: string | null;
  }
  export interface TicketChildBrief {
    id: number;
    protocolo: string;
    assunto: string;
    status_nome?: string | null;
    atendente_nome?: string | null;
    fechado_em?: string | null;
  }
  export interface EmpresaVinculoSugerida {
    id: number;
    nome: string;
  }
  export interface TriagemInbound {
    requer_cadastro_funcionario: boolean;
    remetente_email?: string | null;
    conflito_multiplas_redes?: boolean;
    empresas_vinculo_sugeridas?: EmpresaVinculoSugerida[];
    rede_id_inferida?: number | null;
    rede_nome_inferida?: string | null;
  }
  export interface SolicitanteBrief {
    id?: number | null;
    nome?: string | null;
    email?: string | null;
    cadastrado: boolean;
  }
  export interface Ticket {
    id: number;
    protocolo: string;
    empresa_id: number | null;
    setor_id: number;
    status_id: number;
    atendente_id?: number;
    aberto_por_id?: number;
    assunto: string;
    descricao?: string;
    fechado_em?: string;
    created_at?: string;
    updated_at?: string;
    rede_id?: number | null;
    empresa_nome?: string | null;
    rede_nome?: string;
    coordenacao_rede?: boolean;
    setor_nome?: string;
    status_nome?: string;
    atendente_nome?: string;
    parent_ticket_id?: number | null;
    prioridade?: import('../lib/ticketPrioridade').PrioridadeTicket;
    motivo_id?: number | null;
    motivo_nome?: string | null;
    motivo_outro_texto?: string | null;
    natureza_id?: number | null;
    natureza_nome?: string | null;
    parent?: TicketParentBrief | null;
    children?: TicketChildBrief[];
    vinculos?: TicketVinculo[];
    triagem_inbound?: TriagemInbound | null;
    solicitante?: SolicitanteBrief | null;
    avaliacao_nota?: number | null;
    avaliacao_comentario?: string | null;
    avaliacao_respondida_em?: string | null;
    csat_pendente?: boolean;
    fila_desde_at?: string | null;
    distribuicao_modo_setor?: string | null;
    distribuicao_auto_em_minutos?: number | null;
    sla_policy_id?: number | null;
    sla_violado?: boolean;
    sla_estado?: 'dentro' | 'em_risco' | 'violado' | 'cumprido' | null;
  }
  export interface SlaMetaDetalhe {
    meta_minutos: number | null;
    vence_em: string | null;
    vence_em_efetivo: string | null;
    cumprido_em: string | null;
    estado: string;
    percentual_decorrido: number | null;
  }
  export interface TicketSla {
    ticket_id: number;
    sla_policy_id: number | null;
    sla_violado: boolean;
    inicio_em: string;
    usa_horario_comercial: boolean;
    pausado_agora: boolean;
    minutos_pausados: number;
    primeira_resposta: SlaMetaDetalhe;
    resolucao: SlaMetaDetalhe;
  }
  export type TicketVinculoTipo = 'duplicado_de' | 'relacionado_a';
  export interface TicketVinculoOutro {
    id: number;
    protocolo: string;
    assunto: string;
    status_nome?: string | null;
  }
  export interface TicketVinculo {
    id: number;
    tipo: TicketVinculoTipo;
    rotulo: string;
    outro_ticket: TicketVinculoOutro;
    duplicado_fechado?: boolean;
  }
  export interface VinculoCreate {
    related_ticket_id: number;
    tipo: TicketVinculoTipo;
    fechar_como_duplicado?: boolean;
    motivo_id?: number | null;
    motivo_outro_texto?: string | null;
  }
  export interface FilhoMassaEmpresaOpcao {
    id: number;
    nome: string;
    ja_tem_filho: boolean;
  }
  export interface FilhosMassaOpcoes {
    rede_id: number;
    rede_nome?: string | null;
    assunto_padrao: string;
    descricao_padrao?: string | null;
    setor_id: number;
    empresas: FilhoMassaEmpresaOpcao[];
  }
  export interface FilhosMassaCreate {
    empresa_ids: number[];
    assunto?: string | null;
    descricao?: string | null;
    setor_id?: number | null;
  }
  export interface FilhoMassaCriado {
    id: number;
    protocolo: string;
    empresa_id: number;
    empresa_nome: string;
  }
  export interface FilhosMassaResult {
    criados: FilhoMassaCriado[];
    total: number;
  }
  export interface Historico {
    id: number;
    ticket_id: number;
    atendente_id?: number;
    atendente_nome?: string | null;
    campo: string;
    valor_antigo?: string;
    valor_novo?: string;
    created_at: string;
  }
  export interface Create {
    empresa_id?: number | null;
    rede_id?: number | null;
    setor_id: number;
    assunto: string;
    descricao?: string;
    aberto_por_id?: number;
    parent_ticket_id?: number | null;
    prioridade?: import('../lib/ticketPrioridade').PrioridadeTicket;
  }
  export type MensagemTipo = 'abertura' | 'publico' | 'interno';

  export interface Mensagem {
    id: number;
    ticket_id: number;
    atendente_id?: number | null;
    atendente_nome?: string | null;
    autor_externo?: string | null;
    tipo: MensagemTipo | string;
    corpo: string;
    created_at: string;
    cliente_notificado_por_email?: boolean;
    status?: string | null;
    scheduled_at?: string | null;
    sent_at?: string | null;
    updated_at?: string | null;
  }

  export interface MensagemCreate {
    corpo: string;
    tipo: 'publico' | 'interno';
    notificar_cliente_por_email?: boolean;
  }

  export interface MensagemUpdate {
    corpo: string;
    edit_lock_token: string;
  }

  export interface MensagemStartEdit {
    edit_lock_token: string;
    mensagem: Mensagem;
  }

  export interface Update {
    empresa_id?: number | null;
    setor_id?: number;
    status_id?: number;
    atendente_id?: number | null;
    parent_ticket_id?: number | null;
    prioridade?: import('../lib/ticketPrioridade').PrioridadeTicket;
    motivo_id?: number | null;
    motivo_outro_texto?: string | null;
  }

  export type AnexoVisibilidade = 'publico' | 'interno'

  export interface Anexo {
    id: number
    ticket_id: number
    mensagem_id?: number | null
    atendente_id?: number | null
    atendente_nome?: string | null
    visibilidade: AnexoVisibilidade
    nome_original: string
    content_type?: string | null
    tamanho_bytes: number
    created_at: string
  }

  export interface AnexoUploadResponse {
    anexo: Anexo
    download_url: string
  }
}

export namespace Kb {
  export interface Category {
    id: number;
    nome: string;
    slug: string;
    ordem: number;
    parent_id: number | null;
    parent_nome?: string | null;
    artigos_count: number;
  }
  export interface CategoryCreate {
    nome: string;
    slug?: string | null;
    ordem?: number;
    parent_id?: number | null;
  }
  export interface CategoryUpdate {
    nome?: string;
    slug?: string | null;
    ordem?: number;
    parent_id?: number | null;
  }
  export interface ArticleBrief {
    id: number;
    titulo: string;
    slug: string;
    category_id: number | null;
    category_nome: string | null;
    status: string;
    interno_only: boolean;
    autor_nome: string | null;
    published_at: string | null;
    updated_at: string | null;
  }
  export interface Article extends ArticleBrief {
    conteudo_markdown: string;
    autor_atendente_id: number | null;
    archived_at: string | null;
    created_at: string;
    feedback_util_count?: number;
    feedback_nao_util_count?: number;
  }
  export interface ArticleFeedback {
    util: boolean;
    ja_avaliado: boolean;
    feedback_util_count: number;
    feedback_nao_util_count: number;
  }
  export interface ArticleCreate {
    titulo: string;
    slug?: string | null;
    category_id?: number | null;
    conteudo_markdown?: string;
    interno_only?: boolean;
  }
  export interface ArticleUpdate {
    titulo?: string;
    slug?: string | null;
    category_id?: number | null;
    conteudo_markdown?: string;
    interno_only?: boolean;
  }
  export interface ArticleVersion {
    id: number;
    article_id: number;
    titulo: string;
    status: string;
    autor_atendente_id: number | null;
    autor_nome: string | null;
    created_at: string;
  }
  export interface ArticleVersionDetail extends ArticleVersion {
    conteudo_markdown: string;
  }
  export interface ImageUpload {
    url: string;
    filename: string;
  }
  export interface MotivoLinkItem {
    id?: number | null;
    motivo_id?: number | null;
    natureza_id?: number | null;
    ordem?: number;
    motivo_nome?: string | null;
    natureza_nome?: string | null;
  }
  export interface PublicBranding {
    nome_exibicao: string;
    portal_titulo: string;
    logo_url: string | null;
    texto_boas_vindas: string | null;
    cor_primaria: string;
    cor_header: string;
    cor_sidebar: string;
    cor_texto_header: string;
    cor_texto_corpo: string;
    cor_fundo: string;
    cor_link: string;
    exibir_marca_deskrudder: boolean;
    feedback_habilitado: boolean;
    chat_habilitado: boolean;
  }
  export interface PortalChatSessionCreate {
    visitante_nome: string;
    visitante_email?: string | null;
  }
  export interface PortalChatMensagem {
    id: number;
    chat_id: number;
    direcao: string;
    corpo: string;
    tipo_midia?: string;
    mimetype?: string | null;
    midia_disponivel?: boolean;
    atendente_id: number | null;
    atendente_nome?: string | null;
    evento_sistema?: string | null;
    created_at: string;
  }
  export interface PortalChat {
    id: number;
    protocolo: string;
    visitante_nome: string;
    visitante_email: string | null;
    estado: string;
    setor_id: number | null;
    setor_nome?: string | null;
    atendente_id: number | null;
    atendente_nome?: string | null;
    created_at: string;
    atendimento_inicio_at: string | null;
    encerramento_at: string | null;
    ultima_mensagem_preview?: string | null;
  }
  export interface PortalChatSession {
    visitor_token: string;
    chat: PortalChat;
    mensagens: PortalChatMensagem[];
  }
  export interface PortalChatPublicSession {
    protocolo: string;
    estado: string;
    visitante_nome: string;
    mensagens: PortalChatMensagem[];
  }
  export interface PortalChatDemanda {
    id: number;
    chat_id: number;
    natureza_id: number;
    natureza_nome?: string | null;
    motivo_id?: number | null;
    motivo_nome?: string | null;
    desfecho: string;
    ticket_id?: number | null;
    descricao_curta?: string | null;
    atendente_id?: number | null;
    atendente_nome?: string | null;
    created_at?: string | null;
  }
  export interface PortalChatDemandaCreate {
    natureza_id: number;
    motivo_id?: number | null;
    descricao_curta?: string | null;
  }
  export interface PortalChatDemandaUpdate {
    natureza_id?: number | null;
    motivo_id?: number | null;
    descricao_curta?: string | null;
  }
  export interface PortalSettings {
    portal_titulo: string | null;
    texto_boas_vindas: string | null;
    cor_header: string;
    cor_sidebar: string;
    cor_primaria: string;
    cor_texto_header: string;
    cor_texto_corpo: string;
    cor_fundo: string;
    cor_link: string | null;
    exibir_marca_deskrudder: boolean;
    feedback_habilitado: boolean;
    chat_habilitado: boolean;
    chat_setor_id: number | null;
    chat_texto_boas_vindas: string | null;
    public_url_preview: string | null;
  }
  export interface PortalSettingsUpdate {
    portal_titulo?: string | null;
    texto_boas_vindas?: string | null;
    cor_header?: string;
    cor_sidebar?: string;
    cor_primaria?: string;
    cor_texto_header?: string;
    cor_texto_corpo?: string;
    cor_fundo?: string;
    cor_link?: string | null;
    exibir_marca_deskrudder?: boolean;
    feedback_habilitado?: boolean;
    chat_habilitado?: boolean;
    chat_setor_id?: number | null;
    chat_texto_boas_vindas?: string | null;
  }
}

export namespace PortalChats {
  export type Chat = Kb.PortalChat;
  export type Mensagem = Kb.PortalChatMensagem;
  export type Demanda = Kb.PortalChatDemanda;
  export type DemandaCreate = Kb.PortalChatDemandaCreate;
  export type DemandaUpdate = Kb.PortalChatDemandaUpdate;
}

export namespace Audit {
  export interface AuditLogEntry {
    id: number;
    entity_type: string;
    entity_id: number;
    action: string;
    atendente_id: number | null;
    atendente_nome: string | null;
    payload_json: Record<string, unknown> | null;
    ip_address: string | null;
    user_agent: string | null;
    request_id: string | null;
    created_at: string;
  }
}

export namespace Presenca {
  export interface SetorResumo {
    id: number;
    nome: string;
  }
  export interface ItemOnline {
    atendente_id: number;
    nome: string;
    email: string;
    role: string;
    online_desde: string;
    setores: SetorResumo[];
  }
  export interface ListaOnline {
    itens: ItemOnline[];
  }
}

export namespace Ponto {
  export type Tipo = 'entrada' | 'saida' | 'pausa_inicio' | 'pausa_fim'
  export type Origem = 'web' | 'mobile' | 'admin' | 'sistema'
  export type StatusDia =
    | 'ok'
    | 'falta'
    | 'parcial'
    | 'folga'
    | 'folga_com_ponto'
    | 'livre'
    | 'atraso'
    | 'feriado'
  export interface Bater {
    tipo: Tipo
    origem?: Origem
  }
  export interface Batida {
    id: number
    atendente_id: number
    tipo: Tipo | string
    registrado_em: string
    origem: string | null
    anulada?: boolean
  }
  export interface BatidaAdmin {
    id: number
    atendente_id: number
    atendente_nome: string
    tipo: string
    registrado_em: string
    origem: string | null
    anulada?: boolean
  }
  export interface Intervalo {
    data: string
    entrada_em: string
    saida_em: string | null
    duracao_segundos: number | null
    segundos_pausa?: number
    aberto: boolean
  }
  export interface EstadoMe {
    em_jornada: boolean
    em_pausa?: boolean
    entrada_aberta_em: string | null
    ultima_batida: Batida | null
    usa_escala: boolean
    hoje_esperado: boolean | null
    escala_rotulo: string | null
  }
  export interface Historico {
    intervalos: Intervalo[]
    total_segundos_fechados: number
    total_segundos_pausa?: number
    total: number
  }
  export interface DiaCalendario {
    data: string
    esperado: boolean
    tem_entrada: boolean
    tem_saida: boolean
    status: StatusDia
    atrasado?: boolean
    feriado?: boolean
  }
  export interface Calendario {
    atendente_id: number
    ano: number
    mes: number
    usa_escala: boolean
    escala_rotulo: string | null
    dias: DiaCalendario[]
  }
  export interface HojeItem {
    atendente_id: number
    nome: string
    esperado: boolean
    em_jornada: boolean
    em_pausa?: boolean
    entrada_em: string | null
    status: StatusDia
    online?: boolean
    online_sem_ponto?: boolean
    atrasado?: boolean
    feriado?: boolean
  }
  export interface HojeLista {
    data: string
    itens: HojeItem[]
  }
  export interface BancoHoras {
    atendente_id: number
    atendente_nome?: string | null
    desde: string
    ate: string
    segundos_esperados: number
    segundos_realizados: number
    saldo_segundos: number
    dias_escala: number
    dias_feriado?: number
  }
  export interface Digest {
    data: string
    faltas: number
    atrasos: number
    jornadas_abertas: number
    online_sem_ponto: number
    justificativas_pendentes: number
    itens: HojeItem[]
  }
  export interface Settings {
    usar_feriados_nacionais: boolean
    fecho_automatico_ativo: boolean
    fecho_apos_horas: number
  }
  export interface SettingsUpdate {
    usar_feriados_nacionais?: boolean
    fecho_automatico_ativo?: boolean
    fecho_apos_horas?: number
  }
  export interface Feriado {
    id: number
    data: string
    nome: string
    ativo: boolean
  }
  export interface FeriadoCreate {
    data: string
    nome: string
    ativo?: boolean
  }
  export interface AlertasMe {
    sem_entrada_em_dia_escala: boolean
    online_sem_ponto: boolean
    jornada_aberta_longa: boolean
    horas_jornada_aberta: number | null
    mensagens: string[]
  }
  export interface AjusteCreate {
    atendente_id: number
    tipo: Tipo
    registrado_em: string
    motivo: string
  }
  export interface AjusteUpdate {
    tipo?: Tipo
    registrado_em?: string
    motivo: string
  }
  export interface JustificativaCreate {
    data_ref: string
    tipo: 'falta' | 'esquecimento' | 'folga_com_ponto' | 'outro'
    motivo: string
  }
  export interface Justificativa {
    id: number
    atendente_id: number
    atendente_nome?: string | null
    data_ref: string
    tipo: string
    motivo: string
    estado: string
    decisao_motivo?: string | null
    decidido_por_id?: number | null
    decidido_em?: string | null
    created_at?: string | null
  }
  export interface JustificativaDecisao {
    estado: 'aprovada' | 'rejeitada'
    decisao_motivo: string
    aplicar_batidas?: { tipo: Tipo; registrado_em: string; motivo: string }[]
  }
}

export namespace System {
  export interface Info {
    version: string | null;
    version_display: string | null;
    git_sha: string | null;
    environment: string;
    saas_control_plane?: boolean;
  }
  export interface ReleaseChange {
    category: string;
    text: string;
    product?: string | null;
  }
  export interface Release {
    version: string;
    version_display: string;
    date: string;
    status: string;
    changes: ReleaseChange[];
  }
  export interface ReleaseNotes {
    current_version: string | null;
    current_version_display: string | null;
    current: Release | null;
    releases: Release[];
    upcoming: ReleaseChange[];
  }
}

export const system = {
  info: () => api<System.Info>('/system/info'),
  releaseNotes: () => api<System.ReleaseNotes>('/system/release-notes'),
};

/** Release notes do control-plane (RBAC saas_ops). */
export const saasReleaseNotes = {
  get: () => api<System.ReleaseNotes>('/saas/release-notes'),
};

export const saasClientes = {
  resumo: () => api<SaasClientes.Resumo>('/saas/resumo'),
  list: (params?: {
    busca?: string;
    status?: string;
    plano_id?: number;
    aprovacao_status?: string;
    provisionamento_status?: string;
    provisionamento_fila?: boolean;
    vencendo?: boolean;
    vencidas?: boolean;
    ordenar_por?: 'nome' | 'slug' | 'status' | 'data_renovacao';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<SaasClientes.Cliente>('/saas/clientes', params),
  get: (id: number) => api<SaasClientes.Cliente>(`/saas/clientes/${id}`),
  timeline: (id: number, params?: { limit?: number }) =>
    api<SaasClientes.TimelineEvent[]>(
      withParams(`/saas/clientes/${id}/timeline`, params),
    ),
  create: (data: SaasClientes.Create) =>
    api<SaasClientes.Cliente>('/saas/clientes', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: SaasClientes.Update) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  suspender: (id: number) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/suspender`, { method: 'POST' }),
  reativar: (id: number) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/reativar`, { method: 'POST' }),
  renovar: (id: number, data?: { dias?: number; nova_data?: string }) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/renovar`, {
      method: 'POST',
      body: JSON.stringify(data ?? { dias: 30 }),
    }),
  registrarInstancia: (id: number, data: { instancia_url: string }) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/registrar-instancia`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  solicitarProvisionamento: (id: number) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/solicitar-provisionamento`, { method: 'POST' }),
  confirmarProvisionamento: (id: number, data?: { instancia_url?: string }) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/confirmar-provisionamento`, {
      method: 'POST',
      body: JSON.stringify(data ?? {}),
    }),
  aprovar: (
    id: number,
    data?: { notas?: string | null; ativar?: boolean; provisionar?: boolean; plano_id?: number | null },
  ) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/aprovar`, {
      method: 'POST',
      body: JSON.stringify(data ?? {}),
    }),
  rejeitar: (id: number, data?: { notas?: string | null }) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/rejeitar`, {
      method: 'POST',
      body: JSON.stringify(data ?? {}),
    }),
  confirmarStack: (id: number) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/confirmar-stack`, { method: 'POST' }),
  reenviarEntrega: (id: number) =>
    api<SaasClientes.Cliente>(`/saas/clientes/${id}/reenviar-entrega`, { method: 'POST' }),
};

export const saasPlanos = {
  list: (params?: { ativo?: boolean }) => {
    const q = new URLSearchParams()
    if (params?.ativo != null) q.set('ativo', String(params.ativo))
    const qs = q.toString()
    return api<SaasCatalogo.Plano[]>(`/saas/planos${qs ? `?${qs}` : ''}`)
  },
  get: (id: number) => api<SaasCatalogo.Plano>(`/saas/planos/${id}`),
  create: (data: SaasCatalogo.PlanoCreate) =>
    api<SaasCatalogo.Plano>('/saas/planos', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: SaasCatalogo.PlanoUpdate) =>
    api<SaasCatalogo.Plano>(`/saas/planos/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  ativar: (id: number) =>
    api<SaasCatalogo.Plano>(`/saas/planos/${id}/ativar`, { method: 'POST' }),
  desativar: (id: number) =>
    api<SaasCatalogo.Plano>(`/saas/planos/${id}/desativar`, { method: 'POST' }),
};

export const saasModulos = {
  list: (params?: { ativo?: boolean }) => {
    const q = new URLSearchParams()
    if (params?.ativo != null) q.set('ativo', String(params.ativo))
    const qs = q.toString()
    return api<SaasCatalogo.Modulo[]>(`/saas/modulos${qs ? `?${qs}` : ''}`)
  },
  get: (id: number) => api<SaasCatalogo.Modulo>(`/saas/modulos/${id}`),
  create: (data: SaasCatalogo.ModuloCreate) =>
    api<SaasCatalogo.Modulo>('/saas/modulos', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: SaasCatalogo.ModuloUpdate) =>
    api<SaasCatalogo.Modulo>(`/saas/modulos/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  ativar: (id: number) =>
    api<SaasCatalogo.Modulo>(`/saas/modulos/${id}/ativar`, { method: 'POST' }),
  desativar: (id: number) =>
    api<SaasCatalogo.Modulo>(`/saas/modulos/${id}/desativar`, { method: 'POST' }),
};

export const saasPublic = {
  trial: (data: SaasPublic.TrialCreate) =>
    publicApi<SaasPublic.TrialRead>('/saas/public/trial', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  contato: (data: SaasPublic.ContatoCreate) =>
    publicApi<SaasPublic.ContatoRead>('/saas/public/contato', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export const saasLeads = {
  list: (params?: {
    busca?: string;
    status?: string;
    ordenar_por?: 'created_at' | 'nome' | 'status';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<SaasLeads.Lead>('/saas/leads', params),
  get: (id: number) => api<SaasLeads.Lead>(`/saas/leads/${id}`),
  update: (id: number, data: SaasLeads.Update) =>
    api<SaasLeads.Lead>(`/saas/leads/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  converter: (
    id: number,
    data?: {
      slug?: string | null;
      plano?: string | null;
      plano_id?: number | null;
      status?: SaasClientes.Status;
      enfileirar_provisionamento?: boolean;
      notas_extra?: string | null;
    },
  ) =>
    api<SaasClientes.Cliente>(`/saas/leads/${id}/converter`, {
      method: 'POST',
      body: JSON.stringify(data ?? {}),
    }),
};

export namespace SaasLeads {
  export type Status = 'novo' | 'em_atendimento' | 'fechado';
  export interface Lead {
    id: number;
    nome: string;
    email: string;
    empresa?: string | null;
    mensagem: string;
    status: Status;
    origem: string;
    notas_internas?: string | null;
    cliente_saas_id?: number | null;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface Update {
    status?: Status;
    notas_internas?: string | null;
  }
}

export namespace SaasPublic {
  export interface TrialCreate {
    empresa: string;
    slug: string;
    contato_nome: string;
    contato_email: string;
    notas?: string | null;
    solicitar_provisionamento?: boolean;
  }
  export interface TrialRead {
    id: number;
    nome: string;
    slug: string;
    status: string;
    data_renovacao?: string | null;
    mensagem: string;
  }
  export interface ContatoCreate {
    nome: string;
    email: string;
    empresa?: string | null;
    mensagem: string;
  }
  export interface ContatoRead {
    id: number;
    mensagem: string;
  }
}

export namespace SaasClientes {
  export type Status = 'trial' | 'ativo' | 'suspenso' | 'churn';
  export type ProvisionamentoStatus = 'pendente' | 'em_progresso' | 'aguardando_ops' | 'sucesso' | 'falha';
  export type AprovacaoStatus = 'pendente' | 'aprovado' | 'rejeitado';
  export interface Resumo {
    clientes_total: number;
    por_status: Record<string, number>;
    vencendo_em_breve: number;
    vencidas_ativas: number;
    provisionamento_pendente: number;
    provisionamento_falha: number;
    aprovacoes_pendentes: number;
    leads_novos: number;
    leads_em_atendimento: number;
    janela_renovacao_dias: number;
    base_dominio_provisionamento?: string;
    instancias?: Array<{
      id: number;
      slug: string;
      nome: string;
      status: string;
      api_port?: number | null;
      stack_status?: string | null;
      provisionamento_status?: string | null;
      instancia_url?: string | null;
    }>;
  }
  export interface TimelineEvent {
    id: number;
    action: string;
    label: string;
    atendente_id?: number | null;
    payload?: Record<string, unknown> | null;
    created_at?: string | null;
  }
  export interface Cliente {
    id: number;
    nome: string;
    slug: string;
    status: Status;
    plano?: string | null;
    plano_id?: number | null;
    plano_modulos?: Array<{ id: number; codigo: string; nome: string; ativo?: boolean }>;
    modulos_snapshot?: string[];
    max_postos?: number | null;
    max_usuarios?: number | null;
    data_inicio: string;
    data_renovacao?: string | null;
    instancia_url?: string | null;
    contato_email?: string | null;
    contato_nome?: string | null;
    api_port?: number | null;
    provisionamento_solicitado: boolean;
    provisionamento_status?: ProvisionamentoStatus | null;
    provisionamento_mensagem?: string | null;
    provisionamento_atualizado_em?: string | null;
    aprovacao_status?: AprovacaoStatus;
    aprovacao_notas?: string | null;
    aprovacao_em?: string | null;
    stack_status?: string | null;
    stack_ops_pendente?: 'down' | 'up' | null;
    stack_ops_mensagem?: string | null;
    stack_ops_atualizado_em?: string | null;
    lead_comercial_id?: number | null;
    entrega_notificada_em?: string | null;
    comandos_ops?: string | null;
    comandos_stack?: string | null;
    dias_para_renovacao?: number | null;
    notas?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface Create {
    nome: string;
    slug: string;
    status?: Status;
    plano?: string | null;
    plano_id?: number | null;
    data_inicio: string;
    data_renovacao?: string | null;
    instancia_url?: string | null;
    contato_email?: string | null;
    contato_nome?: string | null;
    notas?: string | null;
    lead_comercial_id?: number | null;
  }
  export type Update = Partial<Create>;
}

export namespace SaasCatalogo {
  export interface Modulo {
    id: number;
    codigo: string;
    nome: string;
    descricao?: string | null;
    ativo: boolean;
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface ModuloBrief {
    id: number;
    codigo: string;
    nome: string;
    ativo?: boolean;
  }
  export interface Plano {
    id: number;
    codigo: string;
    nome: string;
    descricao?: string | null;
    ativo: boolean;
    ordem: number;
    preco_mensal?: number | null;
    max_postos?: number | null;
    max_usuarios?: number | null;
    modulos: ModuloBrief[];
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface PlanoCreate {
    codigo: string;
    nome: string;
    descricao?: string | null;
    ordem?: number;
    preco_mensal?: number | null;
    max_postos?: number | null;
    max_usuarios?: number | null;
    modulo_ids?: number[];
  }
  export type PlanoUpdate = Partial<Omit<PlanoCreate, 'codigo'>>;
  export interface ModuloCreate {
    codigo: string;
    nome: string;
    descricao?: string | null;
  }
  export type ModuloUpdate = Partial<Omit<ModuloCreate, 'codigo'>>;
}
