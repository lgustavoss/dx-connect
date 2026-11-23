import { useEffect, useState } from 'react'
import { comercialContratos, type ComercialContrato } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { useToast } from '../ui/Toast'

const MOTIVO_LABEL: Record<string, string> = {
  aguardando_primeira_venda: 'Aguardando primeira venda no PDV — a mensalidade ainda não nasce.',
  aguardando_fechamento_implantacao: 'Aguardando o fechamento do ticket de implantação — a mensalidade ainda não nasce.',
}

const SETUP_MOMENTOS = [
  { value: '', label: 'Não definido (só no PDF)' },
  { value: 'assinatura', label: 'Na assinatura do contrato' },
  { value: 'data_combinada', label: 'Em data combinada' },
  { value: 'primeira_mensalidade', label: 'Junto da 1ª mensalidade' },
  { value: 'isento', label: 'Isento' },
]

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso.includes('T') ? iso : `${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('pt-BR')
}

function diaIso(v: string | null | undefined): string {
  if (!v) return ''
  return v.slice(0, 10)
}

function money(v: string | number | null | undefined): string {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

/**
 * Cobrança do contrato vigente (#1340 / #1339): marco da primeira venda no PDV e
 * overrides de vencimento/início da mensalidade. Só aparece para contrato assinado.
 */
export function CobrancaContrato({
  contrato,
  podeEditar,
  onUpdated,
}: {
  contrato: ComercialContrato.Contrato
  podeEditar: boolean
  onUpdated: (atual: ComercialContrato.Contrato) => void
}) {
  const toast = useToast()
  const [primeiraVenda, setPrimeiraVenda] = useState(diaIso(contrato.primeira_venda_pdv))
  const [diaVencimento, setDiaVencimento] = useState(
    contrato.dia_vencimento_override != null ? String(contrato.dia_vencimento_override) : '',
  )
  const [inicioOverride, setInicioOverride] = useState(diaIso(contrato.inicio_mensalidade_override))
  const [setupMomento, setSetupMomento] = useState(contrato.setup_momento || '')
  const [setupData, setSetupData] = useState(diaIso(contrato.setup_data_combinada))
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setPrimeiraVenda(diaIso(contrato.primeira_venda_pdv))
    setDiaVencimento(contrato.dia_vencimento_override != null ? String(contrato.dia_vencimento_override) : '')
    setInicioOverride(diaIso(contrato.inicio_mensalidade_override))
    setSetupMomento(contrato.setup_momento || '')
    setSetupData(diaIso(contrato.setup_data_combinada))
  }, [
    contrato.id,
    contrato.primeira_venda_pdv,
    contrato.dia_vencimento_override,
    contrato.inicio_mensalidade_override,
    contrato.setup_momento,
    contrato.setup_data_combinada,
  ])

  async function salvar() {
    if (diaVencimento.trim()) {
      const n = Number(diaVencimento)
      if (!Number.isInteger(n) || n < 1 || n > 28) {
        toast.showWarning('O dia de vencimento deve ficar entre 1 e 28.')
        return
      }
    }
    if (setupMomento === 'data_combinada' && !setupData.trim()) {
      toast.showWarning('Informe a data combinada da taxa de implantação.')
      return
    }
    setSaving(true)
    try {
      const atual = await comercialContratos.atualizarCobranca(contrato.id, {
        primeira_venda_pdv: primeiraVenda.trim() || null,
        dia_vencimento_override: diaVencimento.trim() ? Number(diaVencimento) : null,
        inicio_mensalidade_override: inicioOverride.trim() || null,
        setup_momento: setupMomento ? (setupMomento as ComercialContrato.CobrancaUpdate['setup_momento']) : null,
        setup_data_combinada: setupData.trim() || null,
      })
      toast.showSuccess('Cobrança do contrato atualizada.')
      onUpdated(atual)
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível guardar a cobrança do contrato.'))
    } finally {
      setSaving(false)
    }
  }

  const motivo = contrato.aguardando_motivo

  return (
    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Cobrança da mensalidade</p>
      <div className="mt-1 grid gap-1 text-xs text-slate-500 sm:grid-cols-2">
        <span>
          Início efetivo: <strong className="text-slate-700 dark:text-slate-200">{formatDate(contrato.inicio_mensalidade_efetivo)}</strong>
        </span>
        <span>
          Vencimento: <strong className="text-slate-700 dark:text-slate-200">dia {contrato.dia_vencimento_efetivo ?? '—'}</strong>
        </span>
      </div>
      {motivo ? (
        <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
          {MOTIVO_LABEL[motivo] || motivo}
        </p>
      ) : null}
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <Input
          label="Primeira venda no PDV"
          type="date"
          value={primeiraVenda}
          onChange={(e) => setPrimeiraVenda(e.target.value)}
          disabled={!podeEditar}
          hint="Data manual — sem integração de PDV ainda."
        />
        <Input
          label="Dia de vencimento (override)"
          type="number"
          min={1}
          max={28}
          placeholder="Política da instância"
          value={diaVencimento}
          onChange={(e) => setDiaVencimento(e.target.value)}
          disabled={!podeEditar}
        />
        <Input
          label="Início da mensalidade (override)"
          type="date"
          value={inicioOverride}
          onChange={(e) => setInicioOverride(e.target.value)}
          disabled={!podeEditar}
        />
      </div>
      <div className="mt-3 rounded-lg border border-slate-200/70 p-3 dark:border-slate-700">
        <p className="text-xs font-medium text-slate-700 dark:text-slate-200">Taxa de implantação (setup)</p>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          Valor: {contrato.setup_isento ? 'isento' : money(contrato.setup_valor)} — vira título próprio em A receber
          quando o momento configurado chega (uma vez só, sem duplicar). Isento não gera título.
        </p>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          <Select
            label="Quando vira título"
            value={setupMomento}
            onChange={(v) => setSetupMomento(String(v))}
            options={SETUP_MOMENTOS}
            disabled={!podeEditar}
          />
          {setupMomento === 'data_combinada' ? (
            <Input
              label="Data combinada"
              type="date"
              value={setupData}
              onChange={(e) => setSetupData(e.target.value)}
              disabled={!podeEditar}
            />
          ) : null}
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Overrides valem só para este contrato (negociação). Em branco = segue a política da instância.
        {contrato.primeira_venda_pdv_por_nome ? (
          <>
            {' '}
            Última primeira venda informada por {contrato.primeira_venda_pdv_por_nome}
            {contrato.primeira_venda_pdv_em ? ` em ${new Date(contrato.primeira_venda_pdv_em).toLocaleString('pt-BR')}` : ''}.
          </>
        ) : null}
      </p>
      {podeEditar ? (
        <div className="mt-2">
          <Button variant="secondary" onClick={() => void salvar()} disabled={saving} loading={saving}>
            Guardar cobrança
          </Button>
        </div>
      ) : null}
    </div>
  )
}
