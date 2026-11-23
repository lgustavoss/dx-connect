import { useCallback, useEffect, useState } from 'react'
import { ApiError, faturamento, type Faturamento } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { temPermissao } from '../lib/permissoes'
import { SemPermissao } from './SemPermissao'

const GATILHOS: Array<{ value: Faturamento.GatilhoFaturamento; label: string; hint: string }> = [
  {
    value: 'data_inicio',
    label: 'Data de início do contrato',
    hint: 'A mensalidade começa na data de início. É o comportamento padrão da instância.',
  },
  {
    value: 'dias_apos_assinatura',
    label: 'N dias após a assinatura',
    hint: 'Conta a partir do dia em que o contrato foi marcado como assinado.',
  },
  {
    value: 'dias_apos_marco',
    label: 'N dias após a primeira venda no PDV',
    hint: 'Marco informado manualmente no contrato. Sem a data, a mensalidade não nasce («aguardando primeira venda»).',
  },
  {
    value: 'ticket_implantacao_fechado',
    label: 'Ticket de implantação fechado',
    hint: 'Conta a partir do fechamento do ticket de implantação do contrato.',
  },
]

const OPCOES_DIA = Array.from({ length: 28 }, (_, i) => ({ value: i + 1, label: `Dia ${i + 1}` }))

function descreveGatilho(gatilho: Faturamento.GatilhoFaturamento): string {
  return GATILHOS.find((g) => g.value === gatilho)?.hint ?? ''
}

/** Configurações → Financeiro → Faturamento (#1339). Admin da instância. */
export function ConfigFaturamentoPolitica({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const { user } = useAuth()
  const podeEditar = temPermissao(user, 'faturamento.politica')
  const [politica, setPolitica] = useState<Faturamento.Politica | null>(null)
  const [dia, setDia] = useState('10')
  const [gatilho, setGatilho] = useState<Faturamento.GatilhoFaturamento>('data_inicio')
  const [gatilhoDias, setGatilhoDias] = useState('0')
  const [proporcional, setProporcional] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    faturamento.politica
      .get()
      .then((pol) => {
        setPolitica(pol)
        setDia(String(pol.dia_vencimento))
        setGatilho(pol.gatilho)
        setGatilhoDias(String(pol.gatilho_dias ?? 0))
        setProporcional(Boolean(pol.proporcional_primeira_fatura))
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar a política de faturamento.'))
      })
      .finally(() => setLoading(false))
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  async function salvar() {
    const diaNum = Number(dia)
    if (!Number.isInteger(diaNum) || diaNum < 1 || diaNum > 28) {
      toast.showWarning('O dia de vencimento deve ficar entre 1 e 28.')
      return
    }
    const diasNum = Number(gatilhoDias || 0)
    if (!Number.isInteger(diasNum) || diasNum < 0 || diasNum > 365) {
      toast.showWarning('Os dias do gatilho devem ficar entre 0 e 365.')
      return
    }
    setSaving(true)
    try {
      const atual = await faturamento.politica.patch({
        dia_vencimento: diaNum,
        gatilho,
        gatilho_dias: diasNum,
        proporcional_primeira_fatura: proporcional,
      })
      setPolitica(atual)
      toast.showSuccess('Política de faturamento guardada. As próximas faturas já usam esta regra.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível guardar a política.'))
    } finally {
      setSaving(false)
    }
  }

  const usaDias = gatilho !== 'data_inicio' && gatilho !== 'ticket_implantacao_fechado'
  const usaDiasTicket = gatilho === 'ticket_implantacao_fechado'

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={<SemPermissao title="Só administradores alteram a política de faturamento." />}
      title="Faturamento"
      subtitle="Como a mensalidade nasce e vence nesta instância. Vale para o job e para a geração manual."
      actions={
        podeEditar ? (
          <Button onClick={() => void salvar()} disabled={saving || loading} loading={saving}>
            Guardar
          </Button>
        ) : null
      }
    >
      {loading ? (
        <p className="text-sm text-slate-500">A carregar…</p>
      ) : (
        <div className="space-y-4">
          <Card className="space-y-4">
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Vencimento</p>
            <div className="max-w-xs">
              <Select
                label="Dia do vencimento"
                value={Number(dia) || 10}
                onChange={(v) => setDia(String(v))}
                options={OPCOES_DIA}
                disabled={!podeEditar}
              />
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              A fatura da competência YYYY-MM vence neste dia do mês seguinte (até 28 para existir em todos os
              meses). Um contrato pode sobrescrever a data quando for negociação — o override do contrato vence
              esta política.
            </p>
          </Card>

          <Card className="space-y-4">
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
              Início da mensalidade
            </p>
            <div className="max-w-xl">
              <Select
                label="Gatilho"
                value={gatilho}
                onChange={(v) => setGatilho(v as Faturamento.GatilhoFaturamento)}
                options={GATILHOS.map((g) => ({ value: g.value, label: g.label }))}
                disabled={!podeEditar}
              />
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-300">{descreveGatilho(gatilho)}</p>
            {usaDias || usaDiasTicket ? (
              <div className="max-w-xs">
                <Input
                  label={usaDias ? 'Dias após o gatilho' : 'Dias após o fechamento (opcional)'}
                  type="number"
                  min={0}
                  max={365}
                  value={gatilhoDias}
                  onChange={(e) => setGatilhoDias(e.target.value)}
                  disabled={!podeEditar}
                />
              </div>
            ) : null}
          </Card>

          <Card className="space-y-3">
            <Switch
              checked={proporcional}
              onCheckedChange={setProporcional}
              label="Primeira mensalidade proporcional"
              description="Ligado: a primeira fatura cobre do início da mensalidade até o dia anterior ao vencimento, com valor proporcional. As seguintes são cheias no dia D. Desligado: a primeira já vem com valor cheio."
              disabled={!podeEditar}
              showStatusPill
              statusOnText="Proporcional"
              statusOffText="Valor cheio"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Convenção: dias corridos do início até o dia anterior ao vencimento, divididos pelos dias do ciclo
              (do dia D do mês anterior ao vencimento), arredondando em reais com 2 casas. Início no próprio dia D
              = fatura cheia.
            </p>
          </Card>

          <Card className="space-y-2">
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
              Perfis de exemplo
            </p>
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
              <li>
                <strong>Padrão DeskRudder</strong> — vencimento dia 10, mensalidade na data de início do contrato,
                primeira fatura com valor cheio.
              </li>
              <li>
                <strong>Duplex</strong> — vencimento dia 10, mensalidade 30 dias após a primeira venda no PDV,
                primeira fatura proporcional até o próximo dia 10.
              </li>
            </ul>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              O contrato pode sobrescrever a data de início e o dia de vencimento na aba de cobrança do contrato
              (negociação).
            </p>
          </Card>

          {politica ? (
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Política em vigor: dia {politica.dia_vencimento} · gatilho {politica.gatilho}
              {politica.gatilho_dias ? ` (${politica.gatilho_dias} dia(s))` : ''} · primeira fatura{' '}
              {politica.proporcional_primeira_fatura ? 'proporcional' : 'cheia'}.
            </p>
          ) : null}
        </div>
      )}
    </ConfigListPageShell>
  )
}
