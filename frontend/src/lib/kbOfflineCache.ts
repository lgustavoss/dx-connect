const STORAGE_KEY = 'dx-kb-offline-cache-v1'
const MAX_ITEMS = 10

export type KbCachedArticle = {
  id: number
  slug: string
  titulo: string
  category_nome: string | null
  conteudo_markdown: string
  cached_at: string
}

function readAll(): KbCachedArticle[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as KbCachedArticle[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeAll(items: KbCachedArticle[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, MAX_ITEMS)))
}

export function listKbOfflineCache(): KbCachedArticle[] {
  return readAll()
}

export function cacheKbArticle(article: {
  id: number
  slug: string
  titulo: string
  category_nome?: string | null
  conteudo_markdown: string
}) {
  const now = new Date().toISOString()
  const entry: KbCachedArticle = {
    id: article.id,
    slug: article.slug,
    titulo: article.titulo,
    category_nome: article.category_nome ?? null,
    conteudo_markdown: article.conteudo_markdown,
    cached_at: now,
  }
  const rest = readAll().filter((a) => a.id !== article.id)
  writeAll([entry, ...rest])
}

export function getKbOfflineById(id: number): KbCachedArticle | null {
  return readAll().find((a) => a.id === id) ?? null
}

export function getKbOfflineBySlug(slug: string): KbCachedArticle | null {
  return readAll().find((a) => a.slug === slug) ?? null
}
