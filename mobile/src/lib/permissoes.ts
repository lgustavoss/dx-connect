import type { AtendenteMe } from '../api/client'

export function temPermissao(me: AtendenteMe | null | undefined, codigo: string): boolean {
  if (!me || me.role === 'saas_ops') return false
  if (me.role === 'admin' || me.permissoes?.includes('admin')) return true
  return Boolean(me.permissoes?.includes(codigo))
}

export function podeVerTodosAtendimentos(me: AtendenteMe | null | undefined): boolean {
  return temPermissao(me, 'atendimento.ver_todos')
}
