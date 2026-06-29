import type { Kb } from '../api/client'
import { kbCategoriasRaiz, kbSubcategorias } from './kbCategorias'

export function kbCategoriaTemArtigosPublicos(categoria: Kb.Category, todas: Kb.Category[]): boolean {
  if (categoria.artigos_count > 0) return true
  return kbSubcategorias(todas, categoria.id).some((sub) => sub.artigos_count > 0)
}

export function kbCategoriasRaizPublicas(todas: Kb.Category[]): Kb.Category[] {
  return kbCategoriasRaiz(todas).filter((c) => kbCategoriaTemArtigosPublicos(c, todas))
}

export function kbSubcategoriasPublicas(todas: Kb.Category[], parentId: number): Kb.Category[] {
  return kbSubcategorias(todas, parentId).filter((c) => c.artigos_count > 0)
}

export function kbCategoriaPorId(todas: Kb.Category[], id: number): Kb.Category | undefined {
  return todas.find((c) => c.id === id)
}
