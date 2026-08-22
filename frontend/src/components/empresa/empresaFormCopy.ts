/** Textos de apoio — formulário de empresa. */

export const EMPRESA_SECAO_DOCUMENTO_NOMES =
  'Preencha razão social e nome fantasia conforme o CNPJ. O nome exibido em listas e telas do sistema usa automaticamente o nome fantasia; se estiver vazio, usamos a razão social.'

export const EMPRESA_HINT_ATIVA = 'Empresas inativas somem dos filtros padrão, mas o histórico permanece.'
export const EMPRESA_HINT_EMITE_NFSE =
  'Quando desligado, a fatura interna marca que este cliente não recebe NFS-e. Boleto e nota só são emitidos depois da aprovação do financeiro.'

export const EMPRESA_SECAO_RESPONSAVEL_LEGAL =
  'Dados da pessoa que representa a empresa em contratos de prestação de serviço e documentos correlatos. Todos os campos são opcionais; preencha conforme o instrumento exigir.'

/** Valor do campo `nome` na API: obrigatório no banco; derivado dos dois rótulos oficiais. */
export function nomeParaApiEmpresa(nomeFantasia: string, razaoSocial: string): string {
  return nomeFantasia.trim() || razaoSocial.trim()
}
