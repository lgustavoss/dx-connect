/** Códigos do catálogo de grupos. `admin` (ou o perfil administrador) libera todos. */

export type UsuarioPermissao = {
  role?: string | null
  permissoes?: string[] | null
}

export function temPermissao(user: UsuarioPermissao | null | undefined, codigo: string): boolean {
  if (!user || user.role === 'saas_ops') return false
  if (user.role === 'admin' || user.permissoes?.includes('admin')) return true
  if (user.permissoes?.includes(codigo)) return true
  if (
    codigo === 'chat.encerrar_sem_demanda' &&
    (!user.permissoes || user.permissoes.length === 0) &&
    (user.role === 'atendente' || user.role === 'comercial')
  ) {
    return true
  }
  return false
}

/** Cadastro completo, ou só a aba de PDVs quando a pessoa pode ver o acesso remoto. */
export function destinoEmpresa(user: UsuarioPermissao | null | undefined, empresaId: number): string | null {
  if (temPermissao(user, 'empresas.ver')) return `/empresas/${empresaId}`
  if (temPermissao(user, 'pdv.acessos.ver') || temPermissao(user, 'empresas.editar')) {
    return `/empresas/${empresaId}?aba=pdvs`
  }
  return null
}
