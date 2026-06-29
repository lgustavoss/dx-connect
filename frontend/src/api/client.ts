import { mensagemErroApi } from './errorMessage'
import { isMultiTenantMode, resolveTenantIdFromHostname } from '../lib/tenant'

function apiBaseUrl(): string {
  if (import.meta.env.DEV) return '/api'
  const url = import.meta.env.VITE_API_URL as string | undefined
  if (!url?.trim()) {
    throw new Error('VITE_API_URL não definido — o build de produção deveria ter falhado no vite.config.')
  }
  return url.replace(/\/+$/, '')
}

const BASE = apiBaseUrl()

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
  const res = await fetch(`${BASE}${API_VERSION_PREFIX}${path}`, { ...options, headers });

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
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as object),
  };
  const res = await fetch(`${BASE}${API_VERSION_PREFIX}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(mensagemErroApi(err, res.status), res.status, err);
  }
  return res.json();
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
  listPublicCategories: () => api<Kb.Category[]>('/kb/public/categories'),
  listPublicArticles: (params?: { busca?: string; category_id?: number; limit?: number }) =>
    api<Kb.ArticleBrief[]>(withParams('/kb/public/articles', params)),
  getPublicArticleBySlug: (slug: string) => api<Kb.Article>(`/kb/public/articles/${encodeURIComponent(slug)}`),
  listArticleVersions: (articleId: number) => api<Kb.ArticleVersion[]>(`/kb/articles/${articleId}/versions`),
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
    const url = `${BASE}${API_VERSION_PREFIX}${withParams('/audit', { ...params, format: 'csv' })}`;
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
    auto_msg_avaliacao_ativa?: boolean
    auto_msg_avaliacao_texto?: string | null
    auto_msg_avaliacao_obrigado_texto?: string | null
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
    auto_msg_avaliacao_ativa?: boolean | null
    auto_msg_avaliacao_texto?: string | null
    auto_msg_avaliacao_obrigado_texto?: string | null
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
  const res = await fetch(`${BASE}${API_VERSION_PREFIX}/settings/empresa-sistema/logo`, { headers })
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
  }
  export interface EmpresaOpcao {
    id: number
    nome: string
  }
  export interface FuncionarioOpcao {
    id: number
    nome: string
    email: string
    tipo: string
    empresas: EmpresaOpcao[]
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
  export interface Mensagem {
    id: number
    chat_id: number
    direcao: string
    corpo: string
    tipo_midia?: string | null
    mimetype?: string | null
    midia_disponivel?: boolean
    evento_sistema?: string | null
    wa_message_id?: string | null
    quoted_wa_message_id?: string | null
    quoted_corpo_preview?: string | null
    atendente_id?: number | null
    atendente_nome?: string | null
    created_at?: string | null
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
    `${BASE}${API_VERSION_PREFIX}/whatsapp/chats/${chatId}/mensagens/${mensagemId}/midia`,
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
    `${BASE}${API_VERSION_PREFIX}/tickets/${ticketId}/anexos/${anexoId}/download`,
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

export const whatsappChats = {
  fila: () => api<WhatsappChats.Chat[]>('/whatsapp/chats/fila'),
  meus: () => api<WhatsappChats.Chat[]>('/whatsapp/chats/meus'),
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
  assumir: (id: number) => api<WhatsappChats.Chat>(`/whatsapp/chats/${id}/assumir`, { method: 'POST' }),
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
  marcarVisto: (id: number) => api<void>(`/whatsapp/chats/${id}/visto`, { method: 'POST' }),
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
  getGeral: () => api<Dashboard.GeralResponse>('/dashboard/geral'),
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
    const url = `${BASE}${API_VERSION_PREFIX}${withParams('/relatorios/tickets', { ...params, format: 'csv' })}`;
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
    const url = `${BASE}${API_VERSION_PREFIX}${withParams('/relatorios/chats', { ...params, format: 'csv' })}`;
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
    total_pendencias: number;
  }
  export interface Item {
    tipo: 'fila_sem_responsavel' | 'mensagens_nao_lidas' | 'wpp_chats_na_fila' | 'wpp_chats_com_resposta';
    ticket_id: number | null;
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
  }
  export interface Create {
    email: string;
    nome: string;
    senha: string;
    role?: string;
    ativo?: boolean;
    setor_ids?: number[];
  }
  export interface Update {
    email?: string;
    nome?: string;
    senha?: string;
    role?: string;
    ativo?: boolean;
    setor_ids?: number[];
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
    tipo: string;
    escopo_empresas: EscopoEmpresas;
    ativo: boolean;
    rede_id?: number;
    empresa_id?: number;
    empresa_ids: number[];
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface Create {
    nome: string;
    email?: string | null;
    tipo: string;
    escopo_empresas?: EscopoEmpresas;
    ativo?: boolean;
    rede_id?: number;
    empresa_id?: number;
    empresa_ids?: number[];
  }
  export interface Update {
    nome?: string;
    email?: string | null;
    tipo?: string;
    escopo_empresas?: EscopoEmpresas;
    ativo?: boolean;
    rede_id?: number;
    empresa_id?: number;
    empresa_ids?: number[];
  }
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

export namespace System {
  export interface Info {
    version: string | null;
    version_display: string | null;
    git_sha: string | null;
    environment: string;
  }
  export interface ReleaseChange {
    category: string;
    text: string;
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
