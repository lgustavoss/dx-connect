import { mensagemErroApi } from './errorMessage'

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

const TOKEN_KEY = 'token'

function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
}

export function getAuthToken(): string | null {
  return getToken();
}

export function clearAuthToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(TOKEN_KEY)
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as object),
  };
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${API_VERSION_PREFIX}${path}`, { ...options, headers });

  // Tratamento especial para login: não redirecionar nem recarregar a página,
  // apenas devolver a mensagem para o formulário exibir via toast.
  if (res.status === 401 && path.startsWith('/auth/login')) {
    const err = await res.json().catch(() => ({}));
    let msg = mensagemErroApi(err, 401);
    if (msg.startsWith('Não foi possível concluir')) msg = 'E-mail ou senha inválidos.';
    throw new Error(msg);
  }

  if (res.status === 401) {
    const err = await res.json().catch(() => ({}));
    clearAuthToken();
    window.location.href = '/login';
    throw new Error(mensagemErroApi(err, 401));
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(mensagemErroApi(err, res.status));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const auth = {
  login: (email: string, senha: string) =>
    api<{ access_token: string; must_change_password?: boolean }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, senha }),
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

export const audit = {
  list: (params?: {
    entity_type?: string;
    entity_id?: number;
    busca?: string;
    ordenar_por?: 'created_at' | 'entity_type' | 'entity_id' | 'action' | 'atendente';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<Audit.AuditLogEntry>('/audit', params),
};

export const tickets = {
  list: (params?: {
    empresa_id?: number;
    rede_id?: number;
    setor_id?: number;
    status_id?: number;
    protocolo?: string;
    busca?: string;
    sem_responsavel?: boolean;
    meus?: boolean;
    atendente_id?: number;
    /** Coluna para ordenar (omitir = mais recentes primeiro). */
    ordenar_por?: 'protocolo' | 'rede' | 'empresa' | 'setor' | 'assunto' | 'status' | 'responsavel';
    ordem?: 'asc' | 'desc';
    offset?: number;
    limit?: number;
  }) => listPaginated<Tickets.Ticket>('/tickets', params),
  get: (id: number) => api<Tickets.Ticket>(`/tickets/${id}`),
  getHistorico: (id: number) => api<Tickets.Historico[]>(`/tickets/${id}/historico`),
  listMensagens: (id: number) => api<Tickets.Mensagem[]>(`/tickets/${id}/mensagens`),
  addMensagem: (id: number, data: Tickets.MensagemCreate) =>
    api<Tickets.Mensagem>(`/tickets/${id}/mensagens`, { method: 'POST', body: JSON.stringify(data) }),
  create: (data: Tickets.Create) => api<Tickets.Ticket>('/tickets', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Tickets.Update) => api<Tickets.Ticket>(`/tickets/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
};

export const dashboard = {
  get: () => api<Dashboard.Response>('/dashboard'),
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
  export interface Response {
    resumo: Resumo;
    ultimos_tickets: Tickets.Ticket[];
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
  export interface Setor {
    id: number;
    nome: string;
    slug: string;
    ativo: boolean;
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
}

export namespace FuncionariosRede {
  export interface Funcionario {
    id: number;
    nome: string;
    email: string;
    tipo: string;
    ativo: boolean;
    rede_id?: number;
    empresa_id?: number;
    empresa_ids: number[];
    created_at?: string | null;
    updated_at?: string | null;
  }
  export interface Create {
    nome: string;
    email: string;
    tipo: string;
    ativo?: boolean;
    rede_id?: number;
    empresa_id?: number;
    empresa_ids?: number[];
  }
  export interface Update {
    nome?: string;
    email?: string;
    tipo?: string;
    ativo?: boolean;
    rede_id?: number;
    empresa_id?: number;
    empresa_ids?: number[];
  }
}

export namespace StatusTicket {
  export interface Status {
    id: number;
    nome: string;
    slug: string;
    ordem: number;
    ativo: boolean;
  }
  export interface Create {
    nome: string;
    slug: string;
    ordem?: number;
    ativo?: boolean;
  }
  export interface Update {
    nome?: string;
    slug?: string;
    ordem?: number;
    ativo?: boolean;
  }
}

export namespace Tickets {
  export interface Ticket {
    id: number;
    protocolo: string;
    empresa_id: number;
    setor_id: number;
    status_id: number;
    atendente_id?: number;
    aberto_por_id?: number;
    assunto: string;
    descricao?: string;
    fechado_em?: string;
    created_at?: string;
    updated_at?: string;
    empresa_nome?: string;
    rede_nome?: string;
    setor_nome?: string;
    status_nome?: string;
    atendente_nome?: string;
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
    empresa_id: number;
    setor_id: number;
    assunto: string;
    descricao?: string;
    aberto_por_id?: number;
  }
  export type MensagemTipo = 'abertura' | 'publico' | 'interno';

  export interface Mensagem {
    id: number;
    ticket_id: number;
    atendente_id?: number | null;
    atendente_nome?: string | null;
    tipo: MensagemTipo | string;
    corpo: string;
    created_at: string;
  }

  export interface MensagemCreate {
    corpo: string;
    tipo: 'publico' | 'interno';
  }

  export interface Update {
    setor_id?: number;
    status_id?: number;
    atendente_id?: number | null;
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
    created_at: string;
  }
}
