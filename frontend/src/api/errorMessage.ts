/**
 * Converte corpo JSON típico do FastAPI (detail string | lista | objeto) em texto para o usuário.
 */
export function mensagemErroApi(body: unknown, status: number): string {
  function sanitizarTextoUsuario(input: string): string {
    let s = input

    // Remove URLs completas (http/https) e também "www.".
    s = s.replace(/\bhttps?:\/\/[^\s)]+/gi, '')
    s = s.replace(/\bwww\.[^\s)]+/gi, '')

    // Remove hostnames comuns (ex.: api.exemplo.com.br) e IPs.
    s = s.replace(/\b[a-z0-9-]+(\.[a-z0-9-]+)+\b/gi, '')
    s = s.replace(/\b\d{1,3}(?:\.\d{1,3}){3}\b/g, '')

    // Remove caminhos aparentes de API (ex.: /v1/tickets/2/reabrir) e trechos com /api/.
    s = s.replace(/(?:\s|^)(\/(?:v\d+|api)\/[^\s)]+)(?=\s|$)/gi, ' ')

    // Remove métodos + paths (ex.: "POST /v1/..." ou "GET /...")
    s = s.replace(/\b(GET|POST|PUT|PATCH|DELETE)\s+\/[^\s)]+/gi, '')

    // Normaliza espaços/pontuação residual.
    s = s.replace(/\s{2,}/g, ' ').trim()
    s = s.replace(/^[\-–—:;,. ]+|[\-–—:;,. ]+$/g, '').trim()

    return s
  }

  if (body !== null && typeof body === 'object') {
    const o = body as Record<string, unknown>
    const detail = o.detail

    if (typeof detail === 'string' && detail.trim()) {
      const d = detail.trim()
      // Alguns proxies/backends retornam mensagens genéricas ("Not Found") que não ajudam o usuário
      // e podem vazar detalhes técnicos. Para esses casos, preferimos o fallback por status.
      if (!/^not found$/i.test(d) && !/^404\b/i.test(d)) {
        const safe = sanitizarTextoUsuario(d)
        if (safe) return safe
      }
    }

    if (Array.isArray(detail)) {
      const linhas: string[] = []
      for (const item of detail) {
        if (typeof item === 'string' && item.trim()) linhas.push(sanitizarTextoUsuario(item.trim()))
        else if (item !== null && typeof item === 'object') {
          const row = item as Record<string, unknown>
          if (typeof row.msg === 'string' && row.msg.trim()) linhas.push(sanitizarTextoUsuario(row.msg.trim()))
          else if (typeof row.message === 'string' && row.message.trim()) linhas.push(sanitizarTextoUsuario(row.message.trim()))
        }
      }
      if (linhas.length) {
        const resumo = [...new Set(linhas.filter(Boolean))].join(' ')
        return `Os dados da solicitação não são aceitos pelo servidor. ${resumo}`
      }
    }

    if (detail !== null && typeof detail === 'object') {
      const d = detail as Record<string, unknown>
      if (typeof d.msg === 'string' && d.msg.trim()) {
        const safe = sanitizarTextoUsuario(d.msg.trim())
        if (safe) return safe
      }
      if (typeof d.message === 'string' && d.message.trim()) {
        const safe = sanitizarTextoUsuario(d.message.trim())
        if (safe) return safe
      }
    }

    if (typeof o.message === 'string' && o.message.trim()) {
      const safe = sanitizarTextoUsuario(o.message.trim())
      if (safe) return safe
    }
  }

  if (status === 404) return 'Registro não encontrado.'
  if (status === 403) return 'Você não tem permissão para esta ação.'
  if (status === 422) return 'Dados inválidos. Verifique os campos e tente novamente.'
  if (status >= 500) return 'Serviço indisponível no momento. Tente novamente em instantes.'
  return `Não foi possível concluir a solicitação (código ${status}).`
}

/** Falhas antes de resposta HTTP (rede, CORS, host inexistente). */
export function isErroRedeOuConexao(err: unknown): boolean {
  if (typeof TypeError !== 'undefined' && err instanceof TypeError) return true
  if (err instanceof DOMException && err.name === 'AbortError') return false
  const msg = err instanceof Error ? err.message : String(err)
  return /failed to fetch|networkerror|load failed|network request failed/i.test(msg)
}

function statusEmErroApi(err: unknown): number | null {
  if (err !== null && typeof err === 'object' && 'status' in err) {
    const s = (err as { status: unknown }).status
    return typeof s === 'number' && Number.isFinite(s) ? s : null
  }
  return null
}

function corpoEmErroApi(err: unknown): unknown {
  if (err !== null && typeof err === 'object' && 'body' in err) {
    return (err as { body: unknown }).body
  }
  return undefined
}

/**
 * Mensagens para telas que substituem o conteúdo por erro (detalhe, edição).
 * @param textoNaoEncontrado Frase exibida quando a API responde 404 (ex.: "Empresa não encontrada.").
 */
export function interpretarFalhaCarregamento(
  err: unknown,
  textoNaoEncontrado: string,
): { titulo: string; detalhe?: string } {
  const status = statusEmErroApi(err)
  if (status === 404) {
    return { titulo: textoNaoEncontrado }
  }
  if (err instanceof Error && err.name === 'ApiError' && status != null) {
    const m = err.message.trim() || mensagemErroApi(corpoEmErroApi(err), status)
    if (status >= 500) {
      return {
        titulo: m || 'Serviço indisponível no momento.',
        detalhe: 'Tente novamente em alguns instantes.',
      }
    }
    return { titulo: m || 'Não foi possível carregar os dados.' }
  }
  if (isErroRedeOuConexao(err)) {
    return {
      titulo: 'Não foi possível conectar ao servidor.',
      detalhe: 'Verifique sua internet ou se o serviço está no ar e tente de novo.',
    }
  }
  if (err instanceof Error && err.message.trim()) {
    return { titulo: err.message.trim() }
  }
  return {
    titulo: 'Não foi possível carregar os dados.',
    detalhe: 'Tente novamente em alguns instantes.',
  }
}

/**
 * Toast / alerta curto quando uma listagem ou ação falha (sem tela dedicada).
 * @param texto404 Frase quando a API responde 404 (padrão: registro genérico).
 */
export function mensagemFalhaParaToast(err: unknown, texto404 = 'Registro não encontrado.'): string {
  return interpretarFalhaCarregamento(err, texto404).titulo
}
