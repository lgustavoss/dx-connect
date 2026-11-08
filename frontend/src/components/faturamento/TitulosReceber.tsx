import { useState } from 'react'
import { Link } from 'react-router-dom'
import { faturamento, type Faturamento } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Input, TEXTAREA_FIELD_CLASS } from '../ui/Input'
import { useToast } from '../ui/Toast'
import { useAuth } from '../../contexts/AuthContext'
import { temPermissao } from '../../lib/permissoes'

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

const MIN_MOTIVO_SEM_BOLETO = 10
const MAX_MOTIVO_SEM_BOLETO = 500
const MSG_SEM_BOLETO = 'Anexe o boleto da fatura antes de dar baixa.'

/** Título com fatura e sem o PDF do boleto anexado. Título sem fatura (implantação/multa) fica fora da regra. */
function semBoleto(t: Faturamento.Titulo): boolean {
  return t.fatura_id != null && t.tem_boleto === false
}

function irParaAnexosDaFatura(
  onVerAnexos: ((faturaId: number) => void) | undefined,
  t: Faturamento.Titulo,
) {
  if (onVerAnexos && t.fatura_id != null) onVerAnexos(t.fatura_id)
}

export function TitulosReceber({
  titulos,
  loading,
  podeBaixar,
  onAtualizado,
  onVerAnexos,
}: {
  titulos: Faturamento.Titulo[]
  loading: boolean
  podeBaixar: boolean
  onAtualizado: (titulo: Faturamento.Titulo) => void
  /** Abre a aba Faturas já na fatura do título, para anexar o boleto (#1387). */
  onVerAnexos?: (faturaId: number) => void
}) {
  const toast = useToast()
  const { user } = useAuth()
  // A exceção de baixa sem boleto exige `faturamento.aprovar` — vínculo ao setor Financeiro não basta.
  const podeExcecaoSemBoleto = temPermissao(user, 'faturamento.aprovar')
  const [baixaId, setBaixaId] = useState<number | null>(null)
  const [observacao, setObservacao] = useState('')
  const [motivoExcecao, setMotivoExcecao] = useState('')
  const [erroMotivoExcecao, setErroMotivoExcecao] = useState('')
  const [pagoEm, setPagoEm] = useState(() => new Date().toISOString().slice(0, 10))
  const [saving, setSaving] = useState(false)
  const [acao, setAcao] = useState<{ tipo: 'cancelar' | 'estornar'; id: number } | null>(null)
  const [motivoAcao, setMotivoAcao] = useState('')
  const [savingAcao, setSavingAcao] = useState(false)

  const tituloBaixa = baixaId == null ? null : (titulos.find((t) => t.id === baixaId) ?? null)
  const exigeExcecaoSemBoleto = tituloBaixa != null && semBoleto(tituloBaixa)
  const faturaIdDaBaixa = tituloBaixa?.fatura_id ?? null

  function abrirBaixa(t: Faturamento.Titulo) {
    setBaixaId(t.id)
    setObservacao('')
    setPagoEm(new Date().toISOString().slice(0, 10))
    setMotivoExcecao('')
    setErroMotivoExcecao('')
  }

  async function confirmarAcao() {
    if (acao == null) return
    setSavingAcao(true)
    try {
      const atual =
        acao.tipo === 'cancelar'
          ? await faturamento.cancelarTitulo(acao.id, motivoAcao)
          : await faturamento.estornarTitulo(acao.id, motivoAcao)
      onAtualizado(atual)
      toast.showSuccess(
        acao.tipo === 'cancelar'
          ? 'Título cancelado. A fatura correspondente também foi cancelada.'
          : 'Baixa estornada: o título voltou para em aberto.',
      )
      setAcao(null)
      setMotivoAcao('')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível concluir a ação.'))
    } finally {
      setSavingAcao(false)
    }
  }

  async function confirmarBaixa() {
    if (baixaId == null) return
    const motivo = motivoExcecao.trim()
    if (exigeExcecaoSemBoleto) {
      if (motivo.length < MIN_MOTIVO_SEM_BOLETO) {
        setErroMotivoExcecao(
          `Descreva o motivo da exceção com pelo menos ${MIN_MOTIVO_SEM_BOLETO} caracteres.`,
        )
        return
      }
      if (motivo.length > MAX_MOTIVO_SEM_BOLETO) {
        setErroMotivoExcecao(
          `O motivo da exceção pode ter no máximo ${MAX_MOTIVO_SEM_BOLETO} caracteres.`,
        )
        return
      }
    }
    setSaving(true)
    try {
      const atual = await faturamento.baixarTitulo(baixaId, {
        pago_em: pagoEm || undefined,
        observacao: observacao.trim() || undefined,
        sem_documento_motivo: exigeExcecaoSemBoleto ? motivo : undefined,
      })
      onAtualizado(atual)
      toast.showSuccess(
        exigeExcecaoSemBoleto
          ? 'Título baixado. A exceção sem boleto foi registrada na auditoria.'
          : 'Título baixado como pago.',
      )
      setBaixaId(null)
      setObservacao('')
      setMotivoExcecao('')
      setErroMotivoExcecao('')
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
          {exigeExcecaoSemBoleto ? (
            <div className="space-y-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 dark:border-amber-900/60 dark:bg-amber-950/30">
              <p className="text-sm font-medium text-amber-950 dark:text-amber-100">
                Fatura sem boleto anexado — exceção auditada
              </p>
              <p className="text-xs leading-snug text-amber-900/80 dark:text-amber-100/80">
                A baixa fica registrada na auditoria com o seu usuário e o motivo abaixo. O ideal é anexar o PDF do
                boleto antes.
              </p>
              {onVerAnexos && faturaIdDaBaixa != null ? (
                <button
                  type="button"
                  className="text-xs font-medium text-amber-900 underline underline-offset-2 hover:text-amber-950 dark:text-amber-200 dark:hover:text-amber-100"
                  onClick={() => {
                    onVerAnexos(faturaIdDaBaixa)
                    setBaixaId(null)
                  }}
                >
                  Abrir anexos da fatura
                </button>
              ) : null}
            </div>
          ) : null}
          <div className="w-44">
            <Input label="Pago em" type="date" value={pagoEm} onChange={(e) => setPagoEm(e.target.value)} />
          </div>
          {exigeExcecaoSemBoleto ? (
            <div>
              <label
                htmlFor="motivo-excecao-sem-boleto"
                className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                Motivo da exceção <span className="text-red-600 dark:text-red-400">*</span>
              </label>
              <textarea
                id="motivo-excecao-sem-boleto"
                className={`${TEXTAREA_FIELD_CLASS} ${
                  erroMotivoExcecao ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''
                }`}
                rows={3}
                maxLength={MAX_MOTIVO_SEM_BOLETO}
                value={motivoExcecao}
                onChange={(e) => {
                  setMotivoExcecao(e.target.value)
                  if (erroMotivoExcecao) setErroMotivoExcecao('')
                }}
                placeholder="Ex.: cliente pagou por PIX e o boleto não foi gerado pelo banco."
                aria-invalid={erroMotivoExcecao ? true : undefined}
                aria-describedby="motivo-excecao-sem-boleto-ajuda"
              />
              <div className="mt-1 flex flex-wrap items-center justify-between gap-2 text-xs">
                <span
                  id="motivo-excecao-sem-boleto-ajuda"
                  className={
                    erroMotivoExcecao ? 'text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400'
                  }
                >
                  {erroMotivoExcecao ||
                    `Entre ${MIN_MOTIVO_SEM_BOLETO} e ${MAX_MOTIVO_SEM_BOLETO} caracteres — fica no histórico.`}
                </span>
                <span className="tabular-nums text-slate-400">
                  {motivoExcecao.length}/{MAX_MOTIVO_SEM_BOLETO}
                </span>
              </div>
            </div>
          ) : null}
          <textarea
            className={TEXTAREA_FIELD_CLASS}
            rows={2}
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            placeholder="Opcional: PIX, extrato, observação."
          />
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void confirmarBaixa()} disabled={saving} loading={saving}>
              {exigeExcecaoSemBoleto ? 'Confirmar baixa com exceção' : 'Confirmar pago'}
            </Button>
            <Button variant="cancel" onClick={() => setBaixaId(null)}>
              Cancelar
            </Button>
          </div>
        </Card>
      ) : null}

      {acao != null ? (
        <Card className="space-y-3 border-red-200 dark:border-red-900/60">
          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
            {acao.tipo === 'cancelar' ? 'Cancelar título' : 'Estornar baixa do título'}
          </p>
          <p className="text-xs text-slate-500">
            {acao.tipo === 'cancelar'
              ? 'Título em aberto/vencido sai do A receber e a fatura correspondente é cancelada. Título pago precisa de estorno antes.'
              : 'O título volta para em aberto e os dados da baixa são limpos. Use quando o pagamento não se confirmou.'}
          </p>
          <textarea
            className={TEXTAREA_FIELD_CLASS}
            rows={2}
            value={motivoAcao}
            onChange={(e) => setMotivoAcao(e.target.value)}
            placeholder="Motivo (opcional)"
          />
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void confirmarAcao()} variant="danger" disabled={savingAcao} loading={savingAcao}>
              Confirmar
            </Button>
            <Button variant="cancel" onClick={() => setAcao(null)}>
              Voltar
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
                      {semBoleto(t) ? (
                        <div className="mt-1">
                          {onVerAnexos ? (
                            <button
                              type="button"
                              onClick={() => irParaAnexosDaFatura(onVerAnexos, t)}
                              title="Fatura sem boleto anexado — abra os documentos da fatura para anexar."
                              className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900 transition hover:bg-amber-100 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200 dark:hover:bg-amber-950/70"
                            >
                              Sem boleto · anexar
                            </button>
                          ) : (
                            <span className="inline-flex rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
                              Sem boleto
                            </span>
                          )}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        {podeBaixar && (t.status === 'aberto' || t.status === 'vencido') ? (
                          semBoleto(t) && !podeExcecaoSemBoleto ? (
                            <>
                              <span title={MSG_SEM_BOLETO} className="inline-flex">
                                <Button variant="secondary" disabled>
                                  Dar baixa
                                </Button>
                              </span>
                              {onVerAnexos ? (
                                <Button variant="ghost" onClick={() => irParaAnexosDaFatura(onVerAnexos, t)}>
                                  Anexar boleto
                                </Button>
                              ) : null}
                            </>
                          ) : (
                            <Button variant="secondary" onClick={() => abrirBaixa(t)}>
                              Dar baixa
                            </Button>
                          )
                        ) : null}
                        {podeBaixar && t.status === 'pago' ? (
                          <Button
                            variant="ghost"
                            onClick={() => {
                              setAcao({ tipo: 'estornar', id: t.id })
                              setMotivoAcao('')
                            }}
                          >
                            Estornar baixa
                          </Button>
                        ) : null}
                        {podeBaixar && (t.status === 'aberto' || t.status === 'vencido') ? (
                          <Button
                            variant="ghost"
                            onClick={() => {
                              setAcao({ tipo: 'cancelar', id: t.id })
                              setMotivoAcao('')
                            }}
                          >
                            Cancelar
                          </Button>
                        ) : null}
                        {!podeBaixar || !['aberto', 'vencido', 'pago'].includes(t.status) ? (
                          <span className="text-xs text-slate-400">—</span>
                        ) : null}
                      </div>
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
