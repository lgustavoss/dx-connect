import type { Faturamento } from '../../api/client'
import { Card } from '../ui/Card'

function formatMoney(v: string | number): string {
  const n = typeof v === 'number' ? v : Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

/** Aging 30/60/90 e previsão do mês do A receber (#375). */
export function ResumoAReceberCards({
  resumo,
  loading,
}: {
  resumo: Faturamento.ResumoAReceber | null
  loading: boolean
}) {
  if (loading && !resumo) {
    return (
      <Card>
        <p className="text-sm text-slate-500">Carregando o resumo do A receber…</p>
      </Card>
    )
  }
  if (!resumo) return null
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">A vencer</p>
          <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{formatMoney(resumo.total_aberto)}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Vencido</p>
          <p className="mt-1 text-lg font-semibold text-red-700 dark:text-red-300">{formatMoney(resumo.total_vencido)}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Títulos em aberto</p>
          <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{resumo.quantidade_titulos}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Previsão do mês ({resumo.previsao_mes.competencia})</p>
          <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
            {formatMoney(resumo.previsao_mes.total)}
          </p>
          <p className="text-xs text-slate-500">
            Títulos {formatMoney(resumo.previsao_mes.titulos)} · mensalidades ativas{' '}
            {formatMoney(resumo.previsao_mes.mensalidades_ativas)}
          </p>
        </Card>
      </div>
      <Card className="p-3">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Aging por faixa de atraso</p>
        <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {resumo.faixas.map((faixa) => (
            <div
              key={faixa.chave}
              className={`rounded-lg border px-3 py-2 ${
                faixa.chave === 'a_vencer'
                  ? 'border-slate-200 dark:border-slate-700'
                  : 'border-red-200 bg-red-50/60 dark:border-red-900/60 dark:bg-red-950/30'
              }`}
            >
              <p className="text-xs text-slate-600 dark:text-slate-300">{faixa.label}</p>
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{formatMoney(faixa.valor)}</p>
              <p className="text-xs text-slate-500">{faixa.quantidade} título(s)</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
