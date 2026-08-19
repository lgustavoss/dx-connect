import type { Crm } from '../../api/client'
import { maskCnpjCpf } from '../../utils/maskCnpjCpf'
import { digitsOnly, maskCep, maskTelefoneBr } from '../../utils/masks'

export const FISCAIS_OBRIGATORIOS = [
  'endereco',
  'numero',
  'bairro',
  'cidade',
  'estado',
  'cep',
  'resp_legal_nome',
  'resp_legal_cpf',
] as const

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

export function linhaProntaParaContrato(ln: Crm.Linha): boolean {
  const d = ln.dados_fiscais || {}
  return FISCAIS_OBRIGATORIOS.every((c) => String(d[c] || '').trim().length > 0)
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
