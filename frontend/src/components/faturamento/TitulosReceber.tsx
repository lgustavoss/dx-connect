import { useState } from 'react'
import { Link } from 'react-router-dom'
import { faturamento, type Faturamento } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Input, TEXTAREA_FIELD_CLASS } from '../ui/Input'
import { useToast } from '../ui/Toast'

const STATUS_LABEL: Record<string, string> = {
  aberto: 'Em aberto',
  vencido: 'Vencido',
  pago: 'Pago',
  cancelado: 'Cancelado',
}

const TIPO_LABEL: Record<string, string> = {
  mensalidade: 'Mensalidade',
  implantacao: 'Implantação',
}

function formatMoney(v: string | number): string {
  const n = typeof v === 'number' ? v : Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso.includes('T') ? iso : `${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('pt-BR')
}

function classeStatus(status: string): string {
  if (status === 'pago') return 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
  if (status === 'vencido') return 'bg-red-50 text-red-800 dark:bg-red-950/40 dark:text-red-300'
  if (status === 'aberto') return 'bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200'
  return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
}

export function TitulosReceber({
  titulos,
  loading,
  podeBaixar,
  onAtualizado,
}: {
  titulos: Faturamento.Titulo[]
  loading: boolean
  podeBaixar: boolean
  onAtualizado: (titulo: Faturamento.Titulo) => void
}) {
  const toast = useToast()
  const [baixaId, setBaixaId] = useState<number | null>(null)
  const [observacao, setObservacao] = useState('')
  const [pagoEm, setPagoEm] = useState(() => new Date().toISOString().slice(0, 10))
  const [saving, setSaving] = useState(false)

  async function confirmarBaixa() {
    if (baixaId == null) return
    setSaving(true)
    try {
      const atual = await faturamento.baixarTitulo(baixaId, {
        pago_em: pagoEm || undefined,
        observacao: observacao.trim() || undefined,
      })
      onAtualizado(atual)
      toast.showSuccess('Título baixado como pago.')
      setBaixaId(null)
      setObservacao('')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível dar baixa.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      {baixaId != null ? (
        <Card className="space-y-3">
          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Confirmar baixa</p>
          <p className="text-xs text-slate-500">Marca o título como pago. Não consulta o banco — é o controle interno.</p>
          <div className="w-44">
            <Input label="Pago em" type="date" value={pagoEm} onChange={(e) => setPagoEm(e.target.value)} />
          </div>
          <textarea
            className={TEXTAREA_FIELD_CLASS}
            rows={2}
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            placeholder="Opcional: PIX, extrato, observação."
          />
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void confirmarBaixa()} disabled={saving} loading={saving}>
              Confirmar pago
            </Button>
            <Button variant="cancel" onClick={() => setBaixaId(null)}>
              Cancelar
            </Button>
          </div>
        </Card>
      ) : null}

      <Card>
        {loading ? (
          <p className="text-sm text-slate-500">Carregando títulos…</p>
        ) : titulos.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhum título nesta competência. Aprove a fatura para nascer o a receber.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-700">
                  <th className="px-4 py-3 font-medium">Cliente</th>
                  <th className="px-4 py-3 font-medium">Tipo</th>
                  <th className="px-4 py-3 font-medium">Competência</th>
                  <th className="px-4 py-3 font-medium">Valor</th>
                  <th className="px-4 py-3 font-medium">Vencimento</th>
                  <th className="px-4 py-3 font-medium">Estado</th>
                  <th className="px-4 py-3 font-medium">Ações</th>
                </tr>
              </thead>
              <tbody>
                {titulos.map((t) => (
                  <tr key={t.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800 dark:text-slate-100">
                        {t.razao_social || t.empresa_nome || `Contrato #${t.contrato_id}`}
                      </div>
                      <div className="font-mono text-xs text-slate-500">{t.cnpj || '—'}</div>
                      {t.empresa_id ? (
                        <Link className="text-xs text-sky-700 hover:underline dark:text-sky-300" to={`/empresas/${t.empresa_id}`}>
                          Abrir empresa
                        </Link>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium text-slate-700 dark:text-slate-200">
                        {TIPO_LABEL[t.tipo || 'mensalidade'] || t.tipo}
                      </span>
                    </td>
                    <td className="px-4 py-3 tabular-nums">{t.competencia}</td>
                    <td className="px-4 py-3 tabular-nums">{formatMoney(t.valor)}</td>
                    <td className="px-4 py-3">{formatDate(t.vencimento)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${classeStatus(t.status)}`}>
                        {STATUS_LABEL[t.status] || t.status}
                      </span>
                      {t.status === 'pago' && t.pago_em ? (
                        <p className="mt-1 text-xs text-slate-500">Pago em {formatDate(t.pago_em)}</p>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      {podeBaixar && (t.status === 'aberto' || t.status === 'vencido') ? (
                        <Button
                          variant="secondary"
                          onClick={() => {
                            setBaixaId(t.id)
                            setObservacao('')
                            setPagoEm(new Date().toISOString().slice(0, 10))
                          }}
                        >
                          Dar baixa
                        </Button>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
