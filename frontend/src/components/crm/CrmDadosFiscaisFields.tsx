import { useState } from 'react'
import { empresas as apiEmpresas, type Crm } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { InputCepComBusca } from '../ui/InputCepComBusca'
import { useToast } from '../ui/Toast'
import { maskCnpjCpf } from '../../utils/maskCnpjCpf'
import { digitsOnly, maskTelefoneBr } from '../../utils/masks'

type Props = {
  value: Crm.DadosFiscais
  onChange: (patch: Partial<Crm.DadosFiscais>) => void
  disabled?: boolean
  /** CNPJ da linha/negociação — habilita a consulta na ReceitaWS (#1322). */
  cnpj?: string | null
}

export function CrmDadosFiscaisFields({ value, onChange, disabled, cnpj }: Props) {
  const toast = useToast()
  const [consultandoCnpj, setConsultandoCnpj] = useState(false)

  async function consultarCnpj() {
    const digitos = digitsOnly(cnpj || '')
    if (digitos.length !== 14) {
      toast.showWarning('Informe o CNPJ da linha (14 dígitos) para consultar na Receita.')
      return
    }
    setConsultandoCnpj(true)
    try {
      const data = await apiEmpresas.consultarCnpj(digitos)
      const patch: Partial<Crm.DadosFiscais> = {}
      if (data.endereco) patch.endereco = data.endereco
      if (data.numero) patch.numero = data.numero
      if (data.complemento) patch.complemento = data.complemento
      if (data.bairro) patch.bairro = data.bairro
      if (data.cidade) patch.cidade = data.cidade
      if (data.estado) patch.estado = data.estado
      if (data.cep) patch.cep = data.cep
      if (data.email) patch.email = data.email
      if (data.telefone) patch.telefone = maskTelefoneBr(data.telefone)
      onChange(patch)
      toast.showSuccess('Dados preenchidos pela Receita.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível consultar o CNPJ.'))
    } finally {
      setConsultandoCnpj(false)
    }
  }

  return (
    <fieldset className="space-y-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700" disabled={disabled}>
      <legend className="px-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        Empresa do contrato
      </legend>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="max-w-xl text-xs text-slate-500">
          Este é o cadastro da empresa. O contrato usa estes dados. Uma correção na ficha depois não altera um
          contrato já gerado.
        </p>
        <Button type="button" variant="secondary" onClick={() => void consultarCnpj()} disabled={disabled}>
          {consultandoCnpj ? 'Consultando…' : 'Buscar dados do CNPJ'}
        </Button>
      </div>
      {cnpj ? <p className="text-xs text-slate-500">CNPJ da linha: {maskCnpjCpf(cnpj)}</p> : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="sm:col-span-2">
          <Input
            label="Endereço"
            value={value.endereco || ''}
            onChange={(e) => onChange({ endereco: e.target.value })}
          />
        </div>
        <Input label="Número" value={value.numero || ''} onChange={(e) => onChange({ numero: e.target.value })} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="Complemento"
          value={value.complemento || ''}
          onChange={(e) => onChange({ complemento: e.target.value })}
        />
        <Input label="Bairro" value={value.bairro || ''} onChange={(e) => onChange({ bairro: e.target.value })} />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Input label="Cidade" value={value.cidade || ''} onChange={(e) => onChange({ cidade: e.target.value })} />
        <Input
          label="UF"
          value={value.estado || ''}
          onChange={(e) => onChange({ estado: e.target.value.toUpperCase().slice(0, 2) })}
          maxLength={2}
        />
        <InputCepComBusca
          value={value.cep || ''}
          onChange={(v) => onChange({ cep: v })}
          onEnderecoCompleto={(d) => {
            const patch: Partial<Crm.DadosFiscais> = { cep: d.cep || value.cep || '' }
            if (d.logradouro) patch.endereco = d.logradouro
            if (d.bairro) patch.bairro = d.bairro
            if (d.localidade) patch.cidade = d.localidade
            if (d.uf) patch.estado = d.uf
            onChange(patch)
          }}
          disabled={disabled}
        />
      </div>
      <Input
        label="Inscrição estadual"
        value={value.inscricao_estadual || ''}
        onChange={(e) => onChange({ inscricao_estadual: e.target.value })}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="E-mail da empresa"
          type="email"
          value={value.email || ''}
          onChange={(e) => onChange({ email: e.target.value })}
          hint="Se o lead já tiver e-mail, vem preenchido."
        />
        <Input
          label="Telefone / WhatsApp"
          value={value.telefone || ''}
          onChange={(e) => onChange({ telefone: maskTelefoneBr(e.target.value) })}
          hint="Usado para vincular um contacto na rede ao assinar."
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="Responsável legal"
          value={value.resp_legal_nome || ''}
          onChange={(e) => onChange({ resp_legal_nome: e.target.value })}
        />
        <Input
          label="CPF do responsável"
          value={value.resp_legal_cpf || ''}
          onChange={(e) => onChange({ resp_legal_cpf: maskCnpjCpf(e.target.value) })}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="RG"
          value={value.resp_legal_rg || ''}
          onChange={(e) => onChange({ resp_legal_rg: e.target.value })}
        />
        <Input
          label="Cargo"
          value={value.resp_legal_cargo || ''}
          onChange={(e) => onChange({ resp_legal_cargo: e.target.value })}
        />
      </div>
    </fieldset>
  )
}
