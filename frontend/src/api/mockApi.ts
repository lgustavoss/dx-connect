const DEMO_FLAG_KEY = 'dx-connect-demo-mode'
const DEMO_DB_KEY = 'dx-connect-demo-db'

type DemoDb = {
  user: Record<string, unknown>
  setores: Record<string, unknown>[]
  statusTicket: Record<string, unknown>[]
  redes: Record<string, unknown>[]
  tiposNegocio: Record<string, unknown>[]
  empresas: Record<string, unknown>[]
  atendentes: Record<string, unknown>[]
  funcionariosRede: Record<string, unknown>[]
  tickets: Record<string, unknown>[]
  ticketMensagens: Record<string, Record<string, unknown>[]>
  ticketHistorico: Record<string, Record<string, unknown>[]>
  whatsappConversations: Record<string, unknown>[]
  whatsappMessages: Record<string, Record<string, unknown>[]>
  audit: Record<string, unknown>[]
}

function nowIso() {
  return new Date().toISOString()
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function seedDb(): DemoDb {
  const now = nowIso()
  const setores = [
    { id: 1, nome: 'Suporte de pista', slug: 'suporte-pista', ativo: true },
    { id: 2, nome: 'Automacao', slug: 'automacao', ativo: true },
    { id: 3, nome: 'Financeiro', slug: 'financeiro', ativo: true },
  ]
  const statusTicket = [
    { id: 1, nome: 'Aberto', slug: 'aberto', ordem: 1, ativo: true },
    { id: 2, nome: 'Em atendimento', slug: 'em_atendimento', ordem: 2, ativo: true },
    { id: 3, nome: 'Fechado', slug: 'fechado', ordem: 3, ativo: true },
  ]
  const redes = [
    { id: 1, nome: 'Rede Aurora', ativo: true, created_at: now, updated_at: now },
    { id: 2, nome: 'Rede Horizonte', ativo: true, created_at: now, updated_at: now },
  ]
  const tiposNegocio = [
    { id: 1, nome: 'Posto urbano', ativo: true },
    { id: 2, nome: 'Posto rodoviario', ativo: true },
  ]
  const empresas = [
    {
      id: 1,
      rede_id: 1,
      tipo_negocio_id: 1,
      nome: 'Posto Aurora Centro',
      cnpj_cpf: '12.345.678/0001-90',
      razao_social: 'Aurora Centro Combustiveis LTDA',
      nome_fantasia: 'Aurora Centro',
      cidade: 'Sao Paulo',
      estado: 'SP',
      telefone: '(11) 99999-1001',
      email: 'centro@aurora.demo',
      ativo: true,
      created_at: now,
      updated_at: now,
    },
    {
      id: 2,
      rede_id: 1,
      tipo_negocio_id: 2,
      nome: 'Posto Aurora Rodovia',
      cnpj_cpf: '98.765.432/0001-10',
      razao_social: 'Aurora Rodovia Energia LTDA',
      nome_fantasia: 'Aurora Rodovia',
      cidade: 'Campinas',
      estado: 'SP',
      telefone: '(19) 99999-1002',
      email: 'rodovia@aurora.demo',
      ativo: true,
      created_at: now,
      updated_at: now,
    },
    {
      id: 3,
      rede_id: 2,
      tipo_negocio_id: 1,
      nome: 'Posto Horizonte Norte',
      cnpj_cpf: '11.222.333/0001-44',
      razao_social: 'Horizonte Norte Combustiveis LTDA',
      nome_fantasia: 'Horizonte Norte',
      cidade: 'Belo Horizonte',
      estado: 'MG',
      telefone: '(31) 99999-1003',
      email: 'norte@horizonte.demo',
      ativo: true,
      created_at: now,
      updated_at: now,
    },
  ]
  const atendentes = [
    { id: 1, email: 'admin@demo.local', nome: 'Admin Demo', role: 'admin', ativo: true, setor_ids: [1, 2, 3] },
    { id: 2, email: 'pista@demo.local', nome: 'Camila Pista', role: 'atendente', ativo: true, setor_ids: [1] },
    { id: 3, email: 'auto@demo.local', nome: 'Rafael Automacao', role: 'atendente', ativo: true, setor_ids: [2] },
  ]
  const funcionariosRede = [
    { id: 1, nome: 'Joao Gestor', email: 'joao@aurora.demo', tipo: 'socio', ativo: true, rede_id: 1, empresa_id: null, empresa_ids: [], created_at: now, updated_at: now },
    { id: 2, nome: 'Marina Supervisora', email: 'marina@aurora.demo', tipo: 'supervisor', ativo: true, rede_id: 1, empresa_id: null, empresa_ids: [1, 2], created_at: now, updated_at: now },
  ]
  const tickets = [
    {
      id: 1,
      protocolo: '10421',
      empresa_id: 1,
      setor_id: 1,
      status_id: 2,
      atendente_id: 2,
      aberto_por_id: 1,
      assunto: 'Bomba 04 trava ao finalizar a venda',
      descricao: 'Cliente informou que a bomba encerra sem imprimir o comprovante.',
      created_at: now,
      updated_at: now,
      empresa_nome: 'Posto Aurora Centro',
      rede_nome: 'Rede Aurora',
      setor_nome: 'Suporte de pista',
      status_nome: 'Em atendimento',
      atendente_nome: 'Camila Pista',
    },
    {
      id: 2,
      protocolo: '10422',
      empresa_id: 2,
      setor_id: 2,
      status_id: 1,
      atendente_id: null,
      aberto_por_id: 2,
      assunto: 'PDV nao comunica com o concentrador',
      descricao: 'Falha intermitente desde o inicio da manha.',
      created_at: now,
      updated_at: now,
      empresa_nome: 'Posto Aurora Rodovia',
      rede_nome: 'Rede Aurora',
      setor_nome: 'Automacao',
      status_nome: 'Aberto',
      atendente_nome: null,
    },
    {
      id: 3,
      protocolo: '10423',
      empresa_id: 3,
      setor_id: 3,
      status_id: 3,
      atendente_id: 1,
      aberto_por_id: 1,
      assunto: 'Conciliacao de cartoes divergente',
      descricao: 'Diferenca encontrada no fechamento do turno da madrugada.',
      created_at: now,
      updated_at: now,
      fechado_em: now,
      empresa_nome: 'Posto Horizonte Norte',
      rede_nome: 'Rede Horizonte',
      setor_nome: 'Financeiro',
      status_nome: 'Fechado',
      atendente_nome: 'Admin Demo',
    },
  ]
  const ticketMensagens = {
    '1': [
      { id: 1, ticket_id: 1, atendente_id: 2, atendente_nome: 'Camila Pista', tipo: 'abertura', corpo: 'Cliente informou que a bomba 04 trava ao finalizar a venda e nao imprime comprovante.', created_at: now },
      { id: 2, ticket_id: 1, atendente_id: null, atendente_nome: null, tipo: 'cliente', corpo: 'Isso acontece principalmente no horario de pico, com fila na pista.', created_at: now },
      { id: 3, ticket_id: 1, atendente_id: 2, atendente_nome: 'Camila Pista', tipo: 'publico', corpo: 'Estamos verificando a automacao da bomba e ja seguimos com a analise.', created_at: now },
    ],
    '2': [
      { id: 4, ticket_id: 2, atendente_id: 3, atendente_nome: 'Rafael Automacao', tipo: 'abertura', corpo: 'PDV perde comunicacao com o concentrador a cada 10 minutos.', created_at: now },
    ],
    '3': [
      { id: 5, ticket_id: 3, atendente_id: 1, atendente_nome: 'Admin Demo', tipo: 'abertura', corpo: 'Divergencia de conciliacao tratada com o financeiro da rede.', created_at: now },
      { id: 6, ticket_id: 3, atendente_id: 1, atendente_nome: 'Admin Demo', tipo: 'interno', corpo: 'Fechamento regularizado apos reprocessamento.', created_at: now },
    ],
  }
  const ticketHistorico = {
    '1': [
      { id: 1, ticket_id: 1, atendente_id: 2, atendente_nome: 'Camila Pista', campo: 'status_id', valor_antigo: '1', valor_novo: '2', created_at: now },
    ],
    '2': [],
    '3': [
      { id: 2, ticket_id: 3, atendente_id: 1, atendente_nome: 'Admin Demo', campo: 'status_id', valor_antigo: '2', valor_novo: '3', created_at: now },
    ],
  }
  const whatsappConversations = [
    {
      id: 1,
      wa_id: '5511999991001',
      profile_name: 'Gerente Aurora Centro',
      phone_number: '5511999991001',
      status: 'open',
      ai_enabled: true,
      ai_mode: 'assist',
      last_message_at: now,
      linked_ticket_id: 1,
      linked_ticket_protocolo: '10421',
      linked_ticket_assunto: 'Bomba 04 trava ao finalizar a venda',
      linked_ticket_empresa_nome: 'Posto Aurora Centro',
      created_at: now,
      updated_at: now,
    },
    {
      id: 2,
      wa_id: '5519999991002',
      profile_name: 'Supervisor Rodovia',
      phone_number: '5519999991002',
      status: 'pending',
      ai_enabled: false,
      ai_mode: 'copilot',
      last_message_at: now,
      linked_ticket_id: 2,
      linked_ticket_protocolo: '10422',
      linked_ticket_assunto: 'PDV nao comunica com o concentrador',
      linked_ticket_empresa_nome: 'Posto Aurora Rodovia',
      created_at: now,
      updated_at: now,
    },
  ]
  const whatsappMessages = {
    '1': [
      { id: 1, conversation_id: 1, ticket_id: 1, direction: 'inbound', message_type: 'text', body: 'A bomba 04 voltou a travar agora pouco.', status: 'received', created_at: now },
      { id: 2, conversation_id: 1, ticket_id: 1, direction: 'outbound', message_type: 'text', body: 'Recebemos sua mensagem e estamos acompanhando o ticket 10421.', status: 'sent', created_at: now },
    ],
    '2': [
      { id: 3, conversation_id: 2, ticket_id: 2, direction: 'inbound', message_type: 'text', body: 'O PDV voltou a perder comunicacao depois da troca do cabo.', status: 'received', created_at: now },
    ],
  }
  const audit = [
    { id: 1, entity_type: 'ticket', entity_id: 1, action: 'update', atendente_id: 2, atendente_nome: 'Camila Pista', created_at: now },
    { id: 2, entity_type: 'empresa', entity_id: 1, action: 'create', atendente_id: 1, atendente_nome: 'Admin Demo', created_at: now },
  ]

  return {
    user: atendentes[0],
    setores,
    statusTicket,
    redes,
    tiposNegocio,
    empresas,
    atendentes,
    funcionariosRede,
    tickets,
    ticketMensagens,
    ticketHistorico,
    whatsappConversations,
    whatsappMessages,
    audit,
  }
}

function hasWindow() {
  return typeof window !== 'undefined'
}

export function isDemoModeEnabled() {
  if (!hasWindow()) return import.meta.env.VITE_DEMO_MODE === 'true'
  const localFlag = window.localStorage.getItem(DEMO_FLAG_KEY)
  if (localFlag != null) return localFlag === 'true'
  return import.meta.env.VITE_DEMO_MODE === 'true'
}

export function enableDemoMode() {
  if (!hasWindow()) return
  window.localStorage.setItem(DEMO_FLAG_KEY, 'true')
}

function readDb(): DemoDb {
  if (!hasWindow()) return seedDb()
  const raw = window.localStorage.getItem(DEMO_DB_KEY)
  if (!raw) {
    const seeded = seedDb()
    window.localStorage.setItem(DEMO_DB_KEY, JSON.stringify(seeded))
    return seeded
  }
  try {
    return JSON.parse(raw) as DemoDb
  } catch {
    const seeded = seedDb()
    window.localStorage.setItem(DEMO_DB_KEY, JSON.stringify(seeded))
    return seeded
  }
}

function writeDb(db: DemoDb) {
  if (!hasWindow()) return
  window.localStorage.setItem(DEMO_DB_KEY, JSON.stringify(db))
}

function parseUrl(path: string) {
  const [pathname, queryString = ''] = path.split('?')
  const query = new URLSearchParams(queryString)
  return { pathname, query }
}

function paginate(items: Record<string, unknown>[], query: URLSearchParams) {
  const offset = Number(query.get('offset') ?? '0')
  const limit = Number(query.get('limit') ?? String(items.length || 20))
  return {
    items: items.slice(offset, offset + limit),
    total: items.length,
  }
}

function getTicketNames(db: DemoDb, ticket: Record<string, unknown>): Record<string, unknown> {
  const empresa = db.empresas.find((item) => item.id === ticket.empresa_id)
  const rede = db.redes.find((item) => item.id === empresa?.rede_id)
  const setor = db.setores.find((item) => item.id === ticket.setor_id)
  const status = db.statusTicket.find((item) => item.id === ticket.status_id)
  const atendente = db.atendentes.find((item) => item.id === ticket.atendente_id)
  return {
    ...ticket,
    empresa_nome: empresa?.nome ?? ticket.empresa_nome,
    rede_nome: rede?.nome ?? ticket.rede_nome,
    setor_nome: setor?.nome ?? ticket.setor_nome,
    status_nome: status?.nome ?? ticket.status_nome,
    atendente_nome: atendente?.nome ?? ticket.atendente_nome ?? null,
  }
}

function getConversation(db: DemoDb, id: number) {
  const conversation = db.whatsappConversations.find((item) => item.id === id)
  if (!conversation) return null
  return {
    ...conversation,
    messages: clone(db.whatsappMessages[String(id)] ?? []),
  }
}

function nextId(items: Record<string, unknown>[]) {
  return items.reduce((max, item) => Math.max(max, Number(item.id ?? 0)), 0) + 1
}

export async function mockApi(path: string, options: RequestInit = {}) {
  const db = readDb()
  const method = (options.method ?? 'GET').toUpperCase()
  const body = options.body ? JSON.parse(String(options.body)) : null
  const { pathname, query } = parseUrl(path)
  const parts = pathname.split('/').filter(Boolean)

  if (pathname === '/auth/login' && method === 'POST') {
    enableDemoMode()
    return { access_token: 'demo-token', must_change_password: false }
  }

  if (pathname === '/atendentes/me' && method === 'GET') return clone(db.user)
  if (pathname === '/dashboard' && method === 'GET') {
    return {
      resumo: {
        total_tickets: db.tickets.length,
        abertos_hoje: 2,
        por_status: db.statusTicket.map((status) => ({
          status_id: status.id,
          status_nome: status.nome,
          total: db.tickets.filter((ticket) => ticket.status_id === status.id).length,
        })),
      },
      ultimos_tickets: db.tickets.map((ticket) => getTicketNames(db, ticket)).slice(0, 5),
    }
  }

  if (pathname === '/setores' && method === 'GET') return paginate(clone(db.setores), query)
  if (pathname === '/status-ticket' && method === 'GET') return paginate(clone(db.statusTicket), query)
  if (pathname === '/redes' && method === 'GET') return paginate(clone(db.redes), query)
  if (pathname === '/empresas' && method === 'GET') return paginate(clone(db.empresas), query)
  if (pathname === '/atendentes' && method === 'GET') return paginate(clone(db.atendentes), query)
  if (pathname === '/tipos-negocio' && method === 'GET') return paginate(clone(db.tiposNegocio), query)
  if (pathname === '/funcionarios-rede' && method === 'GET') return paginate(clone(db.funcionariosRede), query)
  if (pathname === '/audit' && method === 'GET') return paginate(clone(db.audit), query)

  if (pathname === '/tickets' && method === 'GET') {
    let tickets = db.tickets.map((ticket) => getTicketNames(db, ticket))
    const busca = (query.get('busca') ?? '').trim().toLowerCase()
    if (busca) {
      tickets = tickets.filter((ticket) =>
        [ticket.protocolo, ticket.assunto, ticket.empresa_nome, ticket.rede_nome]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(busca)),
      )
    }
    return paginate(clone(tickets), query)
  }

  if (pathname === '/tickets' && method === 'POST') {
    const id = nextId(db.tickets)
    const protocolo = String(10420 + id)
    const setor = db.setores.find((item) => item.id === body.setor_id)
    const empresa = db.empresas.find((item) => item.id === body.empresa_id)
    const rede = db.redes.find((item) => item.id === empresa?.rede_id)
    const status = db.statusTicket[0]
    const ticket = {
      id,
      protocolo,
      empresa_id: body.empresa_id,
      setor_id: body.setor_id,
      status_id: status.id,
      atendente_id: null,
      aberto_por_id: null,
      assunto: body.assunto,
      descricao: body.descricao,
      created_at: nowIso(),
      updated_at: nowIso(),
      empresa_nome: empresa?.nome ?? `Empresa #${body.empresa_id}`,
      rede_nome: rede?.nome ?? null,
      setor_nome: setor?.nome ?? null,
      status_nome: status.nome,
      atendente_nome: null,
    }
    db.tickets.unshift(ticket)
    db.ticketMensagens[String(id)] = [
      {
        id: Date.now(),
        ticket_id: id,
        atendente_id: 1,
        atendente_nome: String((db.user as { nome?: string }).nome ?? 'Admin Demo'),
        tipo: 'abertura',
        corpo: body.descricao,
        created_at: nowIso(),
      },
    ]
    db.ticketHistorico[String(id)] = []
    writeDb(db)
    return clone(ticket)
  }

  if (parts[0] === 'tickets' && parts.length >= 2) {
    const ticketId = Number(parts[1])
    const ticket = db.tickets.find((item) => Number(item.id) === ticketId)
    if (!ticket) throw new Error('Ticket nao encontrado')

    if (parts.length === 2 && method === 'GET') return clone(getTicketNames(db, ticket))

    if (parts.length === 2 && method === 'PATCH') {
      const previous = { ...ticket }
      Object.assign(ticket, body, { updated_at: nowIso() })
      const status = db.statusTicket.find((item) => item.id === ticket.status_id)
      if (status) ticket.status_nome = status.nome
      const setor = db.setores.find((item) => item.id === ticket.setor_id)
      if (setor) ticket.setor_nome = setor.nome
      const atendente = db.atendentes.find((item) => item.id === ticket.atendente_id)
      ticket.atendente_nome = atendente?.nome ?? null
      const history = db.ticketHistorico[String(ticketId)] ?? []
      ;(['status_id', 'setor_id', 'atendente_id'] as const).forEach((field) => {
        if (body[field] !== undefined && previous[field] !== body[field]) {
          history.unshift({
            id: Date.now() + history.length,
            ticket_id: ticketId,
            atendente_id: 1,
            atendente_nome: String((db.user as { nome?: string }).nome ?? 'Admin Demo'),
            campo: field,
            valor_antigo: previous[field] == null ? '' : String(previous[field]),
            valor_novo: body[field] == null ? '' : String(body[field]),
            created_at: nowIso(),
          })
        }
      })
      db.ticketHistorico[String(ticketId)] = history
      writeDb(db)
      return clone(getTicketNames(db, ticket))
    }

    if (parts[2] === 'historico' && method === 'GET') return clone(db.ticketHistorico[String(ticketId)] ?? [])
    if (parts[2] === 'mensagens' && method === 'GET') return clone(db.ticketMensagens[String(ticketId)] ?? [])
    if (parts[2] === 'mensagens' && method === 'POST') {
      const messages = db.ticketMensagens[String(ticketId)] ?? []
      const message = {
        id: Date.now(),
        ticket_id: ticketId,
        atendente_id: 1,
        atendente_nome: String((db.user as { nome?: string }).nome ?? 'Admin Demo'),
        tipo: body.tipo,
        corpo: body.corpo,
        created_at: nowIso(),
      }
      messages.push(message)
      db.ticketMensagens[String(ticketId)] = messages
      writeDb(db)
      return clone(message)
    }
  }

  if (pathname === '/whatsapp/conversations' && method === 'GET') {
    return paginate(
      db.whatsappConversations.map((conversation) => ({
        ...conversation,
        messages: clone(db.whatsappMessages[String(conversation.id)] ?? []),
      })),
      query,
    )
  }

  if (parts[0] === 'whatsapp' && parts[1] === 'conversations' && parts[2]) {
    const conversationId = Number(parts[2])
    const conversation = db.whatsappConversations.find((item) => Number(item.id) === conversationId)
    if (!conversation) throw new Error('Conversa nao encontrada')

    if (parts.length === 3 && method === 'GET') return clone(getConversation(db, conversationId))
    if (parts.length === 3 && method === 'PATCH') {
      Object.assign(conversation, body, { updated_at: nowIso() })
      if (body.linked_ticket_id) {
        const ticket = db.tickets.find((item) => item.id === body.linked_ticket_id)
        conversation.linked_ticket_protocolo = ticket?.protocolo ?? null
        conversation.linked_ticket_assunto = ticket?.assunto ?? null
        conversation.linked_ticket_empresa_nome = ticket?.empresa_nome ?? null
      } else if (body.linked_ticket_id === null) {
        conversation.linked_ticket_protocolo = null
        conversation.linked_ticket_assunto = null
        conversation.linked_ticket_empresa_nome = null
      }
      writeDb(db)
      return clone(getConversation(db, conversationId))
    }
    if (parts[3] === 'messages' && method === 'POST') {
      const messages = db.whatsappMessages[String(conversationId)] ?? []
      messages.push({
        id: Date.now(),
        conversation_id: conversationId,
        ticket_id: conversation.linked_ticket_id ?? null,
        direction: 'outbound',
        message_type: 'text',
        body: body.body,
        status: 'sent',
        created_at: nowIso(),
      })
      conversation.last_message_at = nowIso()
      db.whatsappMessages[String(conversationId)] = messages
      writeDb(db)
      return clone(getConversation(db, conversationId))
    }
    if (parts[3] === 'assist' && method === 'POST') {
      const reply = conversation.linked_ticket_id
        ? `Recebemos sua mensagem e seguimos acompanhando o ticket ${conversation.linked_ticket_protocolo}. Se puder, envie o horario exato da ocorrencia para acelerarmos a tratativa.`
        : 'Recebemos sua mensagem no WhatsApp do suporte. Envie a unidade, o problema e o impacto na operacao para iniciarmos a triagem.'
      if (body.auto_send) {
        const messages = db.whatsappMessages[String(conversationId)] ?? []
        messages.push({
          id: Date.now(),
          conversation_id: conversationId,
          ticket_id: conversation.linked_ticket_id ?? null,
          direction: 'outbound',
          message_type: 'text',
          body: reply,
          status: 'sent',
          created_at: nowIso(),
        })
        conversation.last_message_at = nowIso()
        db.whatsappMessages[String(conversationId)] = messages
        writeDb(db)
        return { reply, sent: true, source: 'fallback' }
      }
      return { reply, sent: false, source: 'fallback' }
    }
  }

  throw new Error(`Rota demo nao implementada: ${method} ${pathname}`)
}
