import type { Crm } from '../../api/client'
import { Input } from '../ui/Input'
import { maskCnpjCpf } from '../../utils/maskCnpjCpf'
import { maskCep, maskTelefoneBr } from '../../utils/masks'

type Props = {
  value: Crm.DadosFiscais
  onChange: (patch: Partial<Crm.DadosFiscais>) => void
  disabled?: boolean
}

export function CrmDadosFiscaisFields({ value, onChange, disabled }: Props) {
  return (
    <fieldset className="space-y-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700" disabled={disabled}>
      <legend className="px-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        Dados fiscais do contratante
      </legend>
      <p className="text-xs text-slate-500">
        Endereço e responsável legal entram no PDF. E-mail e telefone vão para a ficha da Empresa ao assinar, para
        atendimento (chat) depois da conversão.
      </p>
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
        <Input
          label="CEP"
          value={value.cep || ''}
          onChange={(e) => onChange({ cep: maskCep(e.target.value) })}
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
