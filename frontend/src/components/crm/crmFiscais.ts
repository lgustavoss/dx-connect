import type { Crm, Empresas } from '../../api/client'
import { maskCnpjCpf } from '../../utils/maskCnpjCpf'
import { digitsOnly, maskCep, maskTelefoneBr } from '../../utils/masks'

export const emptyFiscal = (): Crm.DadosFiscais => ({
  endereco: '',
  numero: '',
  complemento: '',
  bairro: '',
  cidade: '',
  estado: '',
  cep: '',
  inscricao_estadual: '',
  email: '',
  telefone: '',
  resp_legal_nome: '',
  resp_legal_cpf: '',
  resp_legal_rg: '',
  resp_legal_cargo: '',
})

export function fiscaisDaEmpresa(emp: Empresas.Empresa, lead?: Crm.Lead | null): Crm.DadosFiscais {
  return fiscaisDaLinha(
    {
      id: 0,
      negociacao_id: 0,
      item_ids: [],
      quantidade_pdvs: 1,
      desconto_posto_100k: false,
      valor_negociado: '0',
      ordem: 0,
      dados_fiscais: {
        endereco: emp.endereco,
        numero: emp.numero,
        complemento: emp.complemento,
        bairro: emp.bairro,
        cidade: emp.cidade,
        estado: emp.estado,
        cep: emp.cep,
        inscricao_estadual: emp.inscricao_estadual,
        email: emp.email,
        telefone: emp.telefone,
        resp_legal_nome: emp.resp_legal_nome,
        resp_legal_cpf: emp.resp_legal_cpf,
        resp_legal_rg: emp.resp_legal_rg,
        resp_legal_cargo: emp.resp_legal_cargo,
      },
    },
    lead,
  )
}

export function fiscaisDaLinha(ln: Crm.Linha, lead?: Crm.Lead | null): Crm.DadosFiscais {
  const d = ln.dados_fiscais || {}
  const email = (d.email || lead?.email || '').trim()
  const telefoneFonte = d.telefone || lead?.telefone || ''
  return {
    ...emptyFiscal(),
    ...d,
    cep: d.cep ? maskCep(String(d.cep)) : '',
    resp_legal_cpf: d.resp_legal_cpf ? maskCnpjCpf(String(d.resp_legal_cpf)) : '',
    email,
    telefone: telefoneFonte ? maskTelefoneBr(String(telefoneFonte)) : '',
  }
}

export function fiscalIncompleto(d: Crm.DadosFiscais): boolean {
  const p = fiscalPayload(d)
  return (
    !p.endereco ||
    !p.numero ||
    !p.bairro ||
    !p.cidade ||
    !p.estado ||
    !p.cep ||
    !p.resp_legal_nome ||
    !p.resp_legal_cpf
  )
}

export function fiscalPayload(d: Crm.DadosFiscais): Crm.DadosFiscais {
  const trim = (v: string | null | undefined) => (v || '').trim() || null
  return {
    endereco: trim(d.endereco),
    numero: trim(d.numero),
    complemento: trim(d.complemento),
    bairro: trim(d.bairro),
    cidade: trim(d.cidade),
    estado: (d.estado || '').trim().toUpperCase().slice(0, 2) || null,
    cep: digitsOnly(d.cep || '') || null,
    inscricao_estadual: trim(d.inscricao_estadual),
    email: trim(d.email),
    telefone: digitsOnly(d.telefone || '') || null,
    resp_legal_nome: trim(d.resp_legal_nome),
    resp_legal_cpf: digitsOnly(d.resp_legal_cpf || '') || null,
    resp_legal_rg: trim(d.resp_legal_rg),
    resp_legal_cargo: trim(d.resp_legal_cargo),
  }
}

/** Ex.: 5.5 → "5,5"; 0.0000 → "0" */
export function formatPercentualPt(value: string | number | null | undefined): string {
  const n = Number(String(value ?? '0').replace(',', '.'))
  if (!Number.isFinite(n)) return '0'
  return n.toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 0 })
}

export function parsePercentualPt(value: string): number {
  return Number(String(value).replace(/\s/g, '').replace(',', '.'))
}
