import { empresas, type Empresas } from '../api/client'
import type { ItemSelectPesquisa } from '../components/ui/SelectComPesquisa'
import { maskCnpjCpf } from '../utils/maskCnpjCpf'

/**
 * Opção do `SelectComPesquisa` para uma empresa.
 *
 * O rótulo traz o CNPJ quando a API devolve o documento (quem tem `empresas.ver`);
 * para atendentes sem a permissão o resumo vem sem CNPJ — nesse caso a busca
 * acontece no servidor (`/v1/empresas?busca=`), que já aceita o documento
 * formatado ou só com dígitos (#S202611-0001).
 */
export function opcaoEmpresa(e: Empresas.EmpresaListaItem): ItemSelectPesquisa {
  const cnpj = 'cnpj_cpf' in e ? e.cnpj_cpf : null
  const digitos = cnpj ? cnpj.replace(/\D/g, '') : ''
  return {
    id: e.id,
    label: digitos ? `${e.nome} · ${maskCnpjCpf(digitos)}` : e.nome,
    detalhe: digitos || undefined,
    createdAt: 'created_at' in e ? e.created_at : undefined,
  }
}

/** Busca empresas no servidor para o picker (devolve as opções já rotuladas). */
export async function buscarOpcoesEmpresa(termo: string): Promise<ItemSelectPesquisa[]> {
  const pagina = await empresas.list({ busca: termo, limit: 30 })
  return pagina.items.map(opcaoEmpresa)
}
