/** Menções (@pessoa / @all) no chat interno. */

export type MencaoCandidato = {
  atendente_id: number
  nome: string
}

export type MencaoMensagem = {
  tipo: 'user' | 'all'
  atendente_id?: number | null
  rotulo?: string | null
}

export type SegmentoMencao =
  | { kind: 'text'; value: string }
  | { kind: 'mention'; value: string; self?: boolean }

/** Detecta query após `@` no cursor (ex.: "@lu" → { start, query }). */
export function detectarMencaoQuery(
  texto: string,
  cursor: number,
): { start: number; query: string } | null {
  const before = texto.slice(0, cursor)
  const m = before.match(/(^|[\s])@([^\s@]*)$/)
  if (!m) return null
  const atIndex = before.lastIndexOf('@')
  if (atIndex < 0) return null
  return { start: atIndex, query: m[2] ?? '' }
}

export function filtrarMencionaveis(
  candidatos: MencaoCandidato[],
  query: string,
  excluirId?: number | null,
): MencaoCandidato[] {
  const q = query.trim().toLowerCase()
  return candidatos
    .filter((c) => c.atendente_id !== excluirId)
    .filter((c) => !q || c.nome.toLowerCase().includes(q))
    .slice(0, 8)
}

export function inserirMencaoNoTexto(
  texto: string,
  cursor: number,
  start: number,
  rotulo: string,
): { texto: string; cursor: number } {
  const before = texto.slice(0, start)
  const after = texto.slice(cursor)
  const inserido = `@${rotulo} `
  const novo = `${before}${inserido}${after}`
  return { texto: novo, cursor: before.length + inserido.length }
}

export function montarMencoesDoCorpo(
  corpo: string,
  candidatos: MencaoCandidato[],
): MencaoMensagem[] {
  const out: MencaoMensagem[] = []
  if (/(?<!\w)@(all|todos)(?!\w)/i.test(corpo)) {
    out.push({ tipo: 'all', rotulo: 'all' })
  }
  const sorted = [...candidatos].sort((a, b) => b.nome.length - a.nome.length)
  const seen = new Set<number>()
  for (const c of sorted) {
    const re = new RegExp(`(?<!\\w)@${escapeRegExp(c.nome)}(?!\\w)`, 'i')
    if (re.test(corpo) && !seen.has(c.atendente_id)) {
      seen.add(c.atendente_id)
      out.push({ tipo: 'user', atendente_id: c.atendente_id, rotulo: c.nome })
    }
  }
  return out
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** Quebra o corpo em texto + spans de menção para highlight. */
export function segmentarCorpoComMencoes(
  corpo: string,
  mencoes: MencaoMensagem[] | undefined | null,
  meuId?: number | null,
): SegmentoMencao[] {
  if (!corpo) return [{ kind: 'text', value: '' }]
  const tokens: { token: string; self: boolean }[] = []
  const list = mencoes ?? []
  if (list.some((m) => m.tipo === 'all') || /(?<!\w)@(all|todos)(?!\w)/i.test(corpo)) {
    tokens.push({ token: 'all', self: true })
    tokens.push({ token: 'todos', self: true })
  }
  for (const m of list) {
    if (m.tipo === 'user' && m.rotulo) {
      tokens.push({
        token: m.rotulo,
        self: m.atendente_id != null && m.atendente_id === meuId,
      })
    }
  }
  tokens.sort((a, b) => b.token.length - a.token.length)
  if (tokens.length === 0) return [{ kind: 'text', value: corpo }]

  const uniqueTokens = [...new Map(tokens.map((t) => [t.token.toLowerCase(), t])).values()]
  const pattern = new RegExp(
    `(?<!\\w)@(${uniqueTokens.map((t) => escapeRegExp(t.token)).join('|')})(?!\\w)`,
    'gi',
  )
  const selfByLower = new Map(uniqueTokens.map((t) => [t.token.toLowerCase(), t.self]))
  const segments: SegmentoMencao[] = []
  let last = 0
  for (const match of corpo.matchAll(pattern)) {
    const idx = match.index ?? 0
    if (idx > last) segments.push({ kind: 'text', value: corpo.slice(last, idx) })
    const raw = match[0]
    const key = (match[1] || '').toLowerCase()
    segments.push({
      kind: 'mention',
      value: raw,
      self: selfByLower.get(key) ?? (key === 'all' || key === 'todos'),
    })
    last = idx + raw.length
  }
  if (last < corpo.length) segments.push({ kind: 'text', value: corpo.slice(last) })
  return segments.length ? segments : [{ kind: 'text', value: corpo }]
}
