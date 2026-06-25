import type { Kb } from '../api/client'

export function kbCategoriasRaiz(categorias: Kb.Category[]): Kb.Category[] {
  return categorias
    .filter((c) => c.parent_id == null)
    .sort((a, b) => a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR'))
}

export function kbSubcategorias(categorias: Kb.Category[], parentId: number): Kb.Category[] {
  return categorias
    .filter((c) => c.parent_id === parentId)
    .sort((a, b) => a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR'))
}

export type KbCategoriaArvoreItem = {
  categoria: Kb.Category
  depth: 0 | 1
}

/** Lista plana em ordem de árvore (raiz → subcategorias). */
export function kbCategoriasEmArvore(categorias: Kb.Category[]): KbCategoriaArvoreItem[] {
  const out: KbCategoriaArvoreItem[] = []
  for (const root of kbCategoriasRaiz(categorias)) {
    out.push({ categoria: root, depth: 0 })
    for (const sub of kbSubcategorias(categorias, root.id)) {
      out.push({ categoria: sub, depth: 1 })
    }
  }
  for (const orphan of categorias) {
    if (orphan.parent_id != null && !categorias.some((c) => c.id === orphan.parent_id)) {
      out.push({ categoria: orphan, depth: 1 })
    }
  }
  return out
}

/** Opções para Select de artigos/consulta (raiz e subcategoria). */
export function kbCategoriasOpcoesSelect(categorias: Kb.Category[]): { value: string; label: string }[] {
  return kbCategoriasEmArvore(categorias).map(({ categoria, depth }) => ({
    value: String(categoria.id),
    label:
      depth === 0 ? categoria.nome : `${categoria.parent_nome ?? '—'} › ${categoria.nome}`,
  }))
}

/** Apenas categorias raiz (pais de subcategorias). */
export function kbCategoriasPaiOpcoes(categorias: Kb.Category[]): { value: string; label: string }[] {
  return kbCategoriasRaiz(categorias).map((c) => ({ value: String(c.id), label: c.nome }))
}

export function kbCategoriaRotulo(categoria: Kb.Category): string {
  if (categoria.parent_id && categoria.parent_nome) {
    return `${categoria.parent_nome} › ${categoria.nome}`
  }
  return categoria.nome
}
