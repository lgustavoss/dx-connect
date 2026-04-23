import { useState } from 'react'
import { Input } from './Input'
import { useToast } from './Toast'
import { cadastroAux, type CadastroAux } from '../../api/client'
import { digitsOnly, maskCep } from '../../utils/masks'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

type Props = {
  id?: string
  label?: string
  value: string
  onChange: (v: string) => void
  /** Preenche logradouro, bairro, cidade e UF a partir do ViaCEP (via API). */
  onEnderecoCompleto: (d: CadastroAux.CepEndereco) => void
  disabled?: boolean
}

export function InputCepComBusca({ id, label = 'CEP', value, onChange, onEnderecoCompleto, disabled }: Props) {
  const toast = useToast()
  const [loading, setLoading] = useState(false)

  async function buscar() {
    const d = digitsOnly(value)
    if (d.length !== 8) {
      toast.showWarning('Informe o CEP com 8 dígitos para consultar.')
      return
    }
    setLoading(true)
    try {
      const r = await cadastroAux.consultarCep(d)
      onChange(maskCep(d))
      onEnderecoCompleto(r)
      toast.showSuccess('Endereço preenchido pelo CEP.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível consultar o CEP.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Input
      id={id}
      label={label}
      inputMode="numeric"
      placeholder="00000-000"
      value={value}
      onChange={(e) => onChange(maskCep(e.target.value))}
      disabled={disabled}
      endAdornment={
        <button
          type="button"
          onClick={buscar}
          disabled={disabled || loading}
          className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 disabled:pointer-events-none disabled:opacity-45 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
          aria-label="Buscar endereço pelo CEP"
        >
          {loading ? (
            <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />
          ) : (
            <svg className="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          )}
        </button>
      }
    />
  )
}
