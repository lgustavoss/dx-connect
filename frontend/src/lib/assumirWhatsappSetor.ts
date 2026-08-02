import type { Atendentes } from '../api/client'

/** Atendente com vários setores precisa escolher ao assumir chat sem setor (#628). */
export function precisaEscolherSetorAoAssumir(
  user: Atendentes.Atendente | null | undefined,
  chatJaTemSetor?: boolean,
): boolean {
  if (chatJaTemSetor) return false
  return (user?.setor_ids?.length ?? 0) > 1
}
