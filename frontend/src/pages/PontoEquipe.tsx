import { useCallback, useEffect, useState } from 'react'
import { ApiError, atendentes, audit, ponto, type Atendentes, type Audit, type Ponto } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PontoCalendarioMes } from '../components/PontoCalendarioMes'
import { PontoBatidaMapaModal } from '../components/PontoBatidaMapaModal'
import { PontoMetricCard } from '../components/PontoMetricCard'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import {
  formatarDuracao,
  formatarHora,
  hojeIso,
  inicioMesIso,
  rotuloPoliticaGeo,
} from '../lib/pontoFormat'
import { SemPermissao } from './SemPermissao'

function rotuloStatus(s: Ponto.HojeItem['status']): string {
  switch (s) {
    case 'falta':
      return 'Falta'
    case 'parcial':
      return 'Parcial'
    case 'folga':
      return 'Folga'
    case 'folga_com_ponto':
      return 'Folga c/ ponto'
    case 'atraso':
      return 'Atraso'
    case 'feriado':
      return 'Feriado'
    case 'ferias':
      return 'Férias'
    case 'folga_programada':
      return 'Folga programada'
    case 'ok':
      return 'Ok'
    default:
      return 'Livre'
  }
}

function toDatetimeLocalValue(d = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function PontoEquipe() {
  const toast = useToast()
  const { user } = useAuth()
  const [items, setItems] = useState<Ponto.BatidaAdmin[]>([])
  const [total, setTotal] = useState(0)
  const [hoje, setHoje] = useState<Ponto.HojeLista | null>(null)
  const [equipe, setEquipe] = useState<Atendentes.Atendente[]>([])
  const [atendenteId, setAtendenteId] = useState('')
  const [desde, setDesde] = useState(inicioMesIso)
  const [ate, setAte] = useState(hojeIso)
  const [loading, setLoading] = useState(true)
  const [semPermissao, setSemPermissao] = useState(false)
  const [ajusteAtendente, setAjusteAtendente] = useState('')
  const [ajusteTipo, setAjusteTipo] = useState<Ponto.Tipo>('entrada')
  const [ajusteQuando, setAjusteQuando] = useState(toDatetimeLocalValue())
  const [ajusteMotivo, setAjusteMotivo] = useState('')
  const [salvandoAjuste, setSalvandoAjuste] = useState(false)
  const [ajustesAudit, setAjustesAudit] = useState<Audit.AuditLogEntry[]>([])
  const [ajusteAutorId, setAjusteAutorId] = useState('')
  const [ajusteAuditDesde, setAjusteAuditDesde] = useState(inicioMesIso)
  const [ajusteAuditAte, setAjusteAuditAte] = useState(hojeIso)
  const [carregandoAjustes, setCarregandoAjustes] = useState(false)
  const [justifs, setJustifs] = useState<Ponto.Justificativa[]>([])
  const [hesPendentes, setHesPendentes] = useState<Ponto.HoraExtra[]>([])
  const [ausPendentes, setAusPendentes] = useState<Ponto.Ausencia[]>([])
  const [ausTipo, setAusTipo] = useState<'ferias' | 'folga_programada'>('folga_programada')
  const [ausAtendente, setAusAtendente] = useState('')
  const [ausDesde, setAusDesde] = useState(hojeIso)
  const [ausAte, setAusAte] = useState(hojeIso)
  const [ausMotivo, setAusMotivo] = useState('')
  const [concedendoAus, setConcedendoAus] = useState(false)
  const [heModo, setHeModo] = useState<'resto_do_dia' | 'ate_horario' | 'duracao'>('resto_do_dia')
  const [heAteHorario, setHeAteHorario] = useState('20:00')
  const [heDuracaoMin, setHeDuracaoMin] = useState('60')
  const [heConcederAtendente, setHeConcederAtendente] = useState('')
  const [heConcederMotivo, setHeConcederMotivo] = useState('')
  const [concedendoHe, setConcedendoHe] = useState(false)
  const [decidindoHeId, setDecidindoHeId] = useState<number | null>(null)
  const [digest, setDigest] = useState<Ponto.Digest | null>(null)
  const [banco, setBanco] = useState<Ponto.BancoHoras | null>(null)
  const [settings, setSettings] = useState<Ponto.Settings | null>(null)
  const [feriados, setFeriados] = useState<Ponto.Feriado[]>([])
  const [feriadoData, setFeriadoData] = useState('')
  const [feriadoNome, setFeriadoNome] = useState('')
  const [salvandoSettings, setSalvandoSettings] = useState(false)
  const [mapaBatida, setMapaBatida] = useState<Ponto.BatidaAdmin | null>(null)
  const agoraCal = new Date()
  const [calAno, setCalAno] = useState(agoraCal.getFullYear())
  const [calMes, setCalMes] = useState(agoraCal.getMonth() + 1)
  const [calendario, setCalendario] = useState<Ponto.Calendario | null>(null)
  const [diaCal, setDiaCal] = useState<string | null>(null)
  const [loadingCal, setLoadingCal] = useState(false)

  const carregar = useCallback(
    async (silencioso = false) => {
      try {
        const [hist, dia, js, dig, st, fer, hes, aus] = await Promise.all([
          ponto.batidasAdmin({
            atendente_id: atendenteId ? Number(atendenteId) : undefined,
            desde,
            ate,
            limit: 100,
          }),
          ponto.hoje(),
          ponto.justificativasAdmin('pendente'),
          ponto.digest(),
          ponto.settings(),
          ponto.feriados(new Date().getFullYear()),
          ponto.horaExtraAdmin('pendente'),
          ponto.ausenciasAdmin('pendente'),
        ])
        setItems(hist.items)
        setTotal(hist.total)
        setHoje(dia)
        setJustifs(js)
        setDigest(dig)
        setSettings(st)
        setFeriados(fer)
        setHesPendentes(hes)
        setAusPendentes(aus)
        setSemPermissao(false)
        if (atendenteId) {
          const bh = await ponto.bancoHorasAdmin(Number(atendenteId), desde, ate)
          setBanco(bh)
        } else {
          setBanco(null)
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setSemPermissao(true)
          return
        }
        if (!silencioso) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o ponto da equipe.'))
        }
      } finally {
        setLoading(false)
      }
    },
    [ate, atendenteId, desde, toast],
  )

  useEffect(() => {
    void coletarTodasPaginas<Atendentes.Atendente>((o, l) =>
      atendentes.list({ incluir_inativos: false, offset: o, limit: l }),
    ).then(setEquipe)
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  const carregarAjustesAudit = useCallback(async () => {
    setCarregandoAjustes(true)
    try {
      const page = await audit.list({
        entity_type: 'ponto_batida',
        atendente_id: ajusteAutorId ? Number(ajusteAutorId) : undefined,
        de: ajusteAuditDesde,
        ate: ajusteAuditAte,
        ordenar_por: 'created_at',
        ordem: 'desc',
        limit: 50,
      })
      setAjustesAudit(
        page.items.filter((x) =>
          ['create_ajuste', 'update_ajuste', 'anular'].includes(x.action),
        ),
      )
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o histórico de ajustes.'))
    } finally {
      setCarregandoAjustes(false)
    }
  }, [ajusteAuditAte, ajusteAuditDesde, ajusteAutorId, toast])

  useEffect(() => {
    void carregarAjustesAudit()
  }, [carregarAjustesAudit])

  useEffect(() => {
    if (!atendenteId) {
      setCalendario(null)
      return
    }
    let cancel = false
    setLoadingCal(true)
    void ponto
      .calendarioAdmin(Number(atendenteId), calAno, calMes)
      .then((cal) => {
        if (!cancel) setCalendario(cal)
      })
      .catch((err) => {
        if (!cancel) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o calendário.'))
        }
      })
      .finally(() => {
        if (!cancel) setLoadingCal(false)
      })
    return () => {
      cancel = true
    }
  }, [atendenteId, calAno, calMes, toast])

  async function exportarCsv() {
    try {
      const blob = await ponto.exportCsv({
        atendente_id: atendenteId ? Number(atendenteId) : undefined,
        desde,
        ate,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'ponto_batidas.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível exportar o CSV.'))
    }
  }

  async function exportarRelatorio(ext: 'pdf' | 'xlsx') {
    try {
      const params = {
        atendente_id: atendenteId ? Number(atendenteId) : undefined,
        desde,
        ate,
      }
      const blob =
        ext === 'pdf' ? await ponto.exportPdf(params) : await ponto.exportXlsx(params)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = ext === 'pdf' ? 'ponto_relatorio.pdf' : 'ponto_relatorio.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.showError(
        mensagemFalhaParaToast(err, `Não foi possível exportar o ${ext.toUpperCase()}.`),
      )
    }
  }

  async function salvarAjuste() {
    if (!ajusteAtendente) {
      toast.showWarning('Selecione o atendente.')
      return
    }
    if (ajusteMotivo.trim().length < 3) {
      toast.showWarning('Informe o motivo do ajuste (mínimo 3 caracteres).')
      return
    }
    setSalvandoAjuste(true)
    try {
      const iso = new Date(ajusteQuando).toISOString()
      await ponto.criarAjuste({
        atendente_id: Number(ajusteAtendente),
        tipo: ajusteTipo,
        registrado_em: iso,
        motivo: ajusteMotivo.trim(),
      })
      toast.showSuccess('Ajuste registrado.')
      setAjusteMotivo('')
      await Promise.all([carregar(true), carregarAjustesAudit()])
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o ajuste.'))
    } finally {
      setSalvandoAjuste(false)
    }
  }

  async function anularBatida(id: number) {
    const motivo = window.prompt('Motivo da anulação (obrigatório, mín. 3 caracteres):')
    if (!motivo || motivo.trim().length < 3) {
      toast.showWarning('Anulação cancelada — motivo obrigatório.')
      return
    }
    try {
      await ponto.anular(id, motivo.trim())
      toast.showSuccess('Batida anulada.')
      await Promise.all([carregar(true), carregarAjustesAudit()])
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível anular.'))
    }
  }

  async function exportarAjustesCsv() {
    try {
      const blob = await audit.exportCsv({
        entity_type: 'ponto_batida',
        atendente_id: ajusteAutorId ? Number(ajusteAutorId) : undefined,
        de: ajusteAuditDesde,
        ate: ajusteAuditAte,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ajustes-ponto-${ajusteAuditDesde}-${ajusteAuditAte}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível exportar os ajustes.'))
    }
  }

  async function decidirJust(id: number, estado: 'aprovada' | 'rejeitada') {
    const motivo = window.prompt(estado === 'aprovada' ? 'Motivo da aprovação:' : 'Motivo da rejeição:')
    if (!motivo || motivo.trim().length < 3) return
    try {
      await ponto.decidirJustificativa(id, { estado, decisao_motivo: motivo.trim() })
      toast.showSuccess(estado === 'aprovada' ? 'Justificativa aprovada.' : 'Justificativa rejeitada.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível decidir.'))
    }
  }

  async function decidirAus(id: number, aprovar: boolean) {
    try {
      await ponto.decidirAusencia(id, {
        aprovar,
        decisao_motivo: aprovar ? null : 'Negado pelo administrador',
      })
      toast.showSuccess(aprovar ? 'Ausência aprovada.' : 'Ausência negada.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível decidir a ausência.'))
    }
  }

  async function concederAus() {
    if (!ausAtendente) {
      toast.showWarning('Selecione o atendente.')
      return
    }
    if (ausAte < ausDesde) {
      toast.showWarning('A data final deve ser igual ou posterior à inicial.')
      return
    }
    setConcedendoAus(true)
    try {
      await ponto.concederAusencia({
        atendente_id: Number(ausAtendente),
        tipo: ausTipo,
        desde: ausDesde,
        ate: ausAte,
        motivo: ausMotivo.trim() || null,
      })
      toast.showSuccess('Ausência agendada.')
      setAusMotivo('')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível agendar a ausência.'))
    } finally {
      setConcedendoAus(false)
    }
  }

  async function decidirHe(id: number, aprovar: boolean) {
    setDecidindoHeId(id)
    try {
      await ponto.decidirHoraExtra(id, {
        aprovar,
        modo: aprovar ? heModo : null,
        ate_horario: aprovar && heModo === 'ate_horario' ? heAteHorario : null,
        duracao_minutos:
          aprovar && heModo === 'duracao' ? Math.max(15, Number(heDuracaoMin) || 60) : null,
        decisao_motivo: aprovar ? null : 'Negado pelo administrador',
      })
      toast.showSuccess(aprovar ? 'Hora extra liberada.' : 'Pedido de hora extra negado.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível decidir a hora extra.'))
    } finally {
      setDecidindoHeId(null)
    }
  }

  async function concederHe() {
    if (!heConcederAtendente) {
      toast.showWarning('Selecione o atendente.')
      return
    }
    setConcedendoHe(true)
    try {
      await ponto.concederHoraExtra({
        atendente_id: Number(heConcederAtendente),
        modo: heModo,
        ate_horario: heModo === 'ate_horario' ? heAteHorario : null,
        duracao_minutos: heModo === 'duracao' ? Math.max(15, Number(heDuracaoMin) || 60) : null,
        motivo: heConcederMotivo.trim() || null,
      })
      toast.showSuccess('Hora extra concedida.')
      setHeConcederMotivo('')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível conceder a hora extra.'))
    } finally {
      setConcedendoHe(false)
    }
  }

  async function salvarSettings() {
    if (!settings) return
    setSalvandoSettings(true)
    try {
      const st = await ponto.updateSettings({
        usar_feriados_nacionais: settings.usar_feriados_nacionais,
        fecho_automatico_ativo: settings.fecho_automatico_ativo,
        fecho_apos_horas: settings.fecho_apos_horas,
        fecho_margem_pos_saida_minutos: settings.fecho_margem_pos_saida_minutos ?? 30,
        jornada_diaria_minutos: settings.jornada_diaria_minutos,
        pausa_minima_minutos: settings.pausa_minima_minutos ?? 0,
        politica_geolocalizacao: settings.politica_geolocalizacao,
      })
      setSettings(st)
      toast.showSuccess('Configurações de ponto salvas.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar as configurações.'))
    } finally {
      setSalvandoSettings(false)
    }
  }

  async function adicionarFeriado() {
    if (!feriadoData || !feriadoNome.trim()) {
      toast.showWarning('Informe data e nome do feriado.')
      return
    }
    try {
      await ponto.criarFeriado({ data: feriadoData, nome: feriadoNome.trim() })
      toast.showSuccess('Feriado cadastrado.')
      setFeriadoNome('')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível criar o feriado.'))
    }
  }

  async function apagarFeriado(id: number) {
    try {
      await ponto.removerFeriado(id)
      toast.showSuccess('Feriado removido.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível remover o feriado.'))
    }
  }

  if (user?.role !== 'admin' || semPermissao) {
    return (
      <SemPermissao
        title="Acesso restrito a administradores."
        voltarPara="/ponto"
        voltarLabel="Ir para Meu ponto"
      />
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Ponto da equipe"
        subtitle="Visão do dia, batidas, ajustes auditados e relatórios mensais."
      />

      <Card className="overflow-hidden border-cyan-200/60 bg-gradient-to-br from-slate-50 via-white to-cyan-50/40 dark:border-cyan-900/40 dark:from-slate-950 dark:via-slate-900 dark:to-cyan-950/20">
        {loading && !digest ? (
          <div className="h-28 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
        ) : (
          <div className="space-y-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Digest de hoje
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <PontoMetricCard label="Faltas" value={String(digest?.faltas ?? 0)} tone="warn" />
              <PontoMetricCard label="Atrasos" value={String(digest?.atrasos ?? 0)} tone="warn" />
              <PontoMetricCard
                label="Jornadas abertas"
                value={String(digest?.jornadas_abertas ?? 0)}
                tone="info"
              />
              <PontoMetricCard
                label="Online sem ponto"
                value={String(digest?.online_sem_ponto ?? 0)}
                tone="warn"
              />
              <PontoMetricCard
                label="Justificativas"
                value={String(digest?.justificativas_pendentes ?? 0)}
                hint="pendentes"
              />
            </div>
            {(digest?.itens ?? []).some((i) => i.status === 'falta' || i.atrasado) ? (
              <ul className="space-y-1 text-sm text-amber-900 dark:text-amber-100">
                {(digest?.itens ?? [])
                  .filter((i) => i.status === 'falta' || i.atrasado)
                  .map((i) => (
                    <li key={`alerta-${i.atendente_id}`}>
                      <span className="font-medium">{i.nome}</span>
                      {i.status === 'falta' ? ' — falta' : null}
                      {i.atrasado ? ' — atraso' : null}
                    </li>
                  ))}
              </ul>
            ) : null}
          </div>
        )}
      </Card>

      <div className="space-y-4">
        <Card title="Hoje">
          {loading && !hoje ? (
            <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                  <tr>
                    <th className="py-2 pr-3 font-medium">Nome</th>
                    <th className="py-2 pr-3 font-medium">Online</th>
                    <th className="py-2 pr-3 font-medium">Esperado</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 font-medium">Entrada</th>
                  </tr>
                </thead>
                <tbody>
                  {(hoje?.itens ?? []).map((item) => (
                    <tr key={item.atendente_id} className="border-b border-slate-100 dark:border-slate-800/80">
                      <td className="py-2 pr-3">
                        {item.nome}
                        {item.em_pausa ? (
                          <span className="ml-2 text-xs text-amber-700 dark:text-amber-300">pausa</span>
                        ) : null}
                        {item.atrasado ? (
                          <span className="ml-2 text-xs text-amber-700 dark:text-amber-300">atraso</span>
                        ) : null}
                        {item.feriado ? (
                          <span className="ml-2 text-xs text-slate-500">feriado</span>
                        ) : null}
                      </td>
                      <td className="py-2 pr-3">
                        {item.online_sem_ponto ? (
                          <span className="text-amber-700 dark:text-amber-300">Online sem ponto</span>
                        ) : item.online ? (
                          'Online'
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="py-2 pr-3">{item.esperado ? 'Trabalho' : '—'}</td>
                      <td className="py-2 pr-3">{rotuloStatus(item.status)}</td>
                      <td className="py-2">{formatarHora(item.entrada_em)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Justificativas pendentes">
          {justifs.length === 0 ? (
            <p className="text-sm text-slate-500">Nenhuma pendente.</p>
          ) : (
            <ul className="space-y-3">
              {justifs.map((j) => (
                <li
                  key={j.id}
                  className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                >
                  <div className="text-sm">
                    <p className="font-medium">
                      {j.atendente_nome ?? j.atendente_id} · {j.data_ref} · {j.tipo}
                    </p>
                    <p className="text-slate-600 dark:text-slate-300">{j.motivo}</p>
                    {j.tem_anexo ? (
                      <button
                        type="button"
                        className="mt-1 text-xs text-cyan-700 underline dark:text-cyan-300"
                        onClick={() =>
                          void ponto
                            .baixarJustificativaAnexo(j.id, j.anexo_nome)
                            .catch((err) =>
                              toast.showError(
                                mensagemFalhaParaToast(err, 'Não foi possível baixar o anexo.'),
                              ),
                            )
                        }
                      >
                        Baixar anexo{j.anexo_nome ? ` (${j.anexo_nome})` : ''}
                      </button>
                    ) : null}
                  </div>
                  <div className="flex gap-2">
                    <Button type="button" variant="secondary" onClick={() => void decidirJust(j.id, 'aprovada')}>
                      Aprovar
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => void decidirJust(j.id, 'rejeitada')}>
                      Rejeitar
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Férias / folga programada">
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
            Agende direto ou aprove pedidos dos colaboradores. Dias aprovados não geram falta automática.
          </p>
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Select
              label="Colaborador"
              value={ausAtendente}
              onChange={(v) => setAusAtendente(String(v))}
              options={[
                { value: '', label: 'Selecione' },
                ...equipe.map((a) => ({ value: String(a.id), label: a.nome })),
              ]}
            />
            <Select
              label="Tipo"
              value={ausTipo}
              onChange={(v) => setAusTipo(String(v) as 'ferias' | 'folga_programada')}
              options={[
                { value: 'folga_programada', label: 'Folga programada' },
                { value: 'ferias', label: 'Férias' },
              ]}
            />
            <Input label="De" type="date" value={ausDesde} onChange={(e) => setAusDesde(e.target.value)} />
            <Input label="Até" type="date" value={ausAte} onChange={(e) => setAusAte(e.target.value)} />
            <Input
              label="Motivo (opcional)"
              value={ausMotivo}
              onChange={(e) => setAusMotivo(e.target.value)}
            />
            <Button type="button" disabled={concedendoAus} onClick={() => void concederAus()}>
              Agendar
            </Button>
          </div>
          <p className="mb-2 text-sm font-medium text-slate-800 dark:text-slate-100">Pedidos pendentes</p>
          {ausPendentes.length === 0 ? (
            <p className="text-sm text-slate-500">Nenhum pedido pendente.</p>
          ) : (
            <ul className="space-y-3">
              {ausPendentes.map((a) => (
                <li
                  key={a.id}
                  className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                >
                  <div className="text-sm">
                    <p className="font-medium">{a.atendente_nome ?? a.atendente_id}</p>
                    <p className="text-slate-600 dark:text-slate-300">
                      {a.tipo === 'ferias' ? 'Férias' : 'Folga programada'} · {a.desde} → {a.ate}
                    </p>
                    {a.motivo ? <p className="text-slate-500">{a.motivo}</p> : null}
                  </div>
                  <div className="flex gap-2">
                    <Button type="button" variant="secondary" onClick={() => void decidirAus(a.id, true)}>
                      Aprovar
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => void decidirAus(a.id, false)}>
                      Negar
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Hora extra (WhatsApp após jornada)">
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
            Conceda HE com antecedência ou libere pedidos após o fim da jornada. Modos: resto do dia, até um horário ou
            duração em minutos (respeita o teto do colaborador, se houver).
          </p>
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Select
              label="Conceder a"
              value={heConcederAtendente}
              onChange={(v) => setHeConcederAtendente(String(v))}
              options={[
                { value: '', label: 'Selecione' },
                ...equipe.map((a) => ({ value: String(a.id), label: a.nome })),
              ]}
            />
            <Select
              label="Modo"
              value={heModo}
              onChange={(v) => setHeModo(String(v) as 'resto_do_dia' | 'ate_horario' | 'duracao')}
              options={[
                { value: 'resto_do_dia', label: 'Resto do dia' },
                { value: 'ate_horario', label: 'Até horário' },
                { value: 'duracao', label: 'Duração (minutos)' },
              ]}
            />
            {heModo === 'ate_horario' ? (
              <Input
                label="Até (HH:MM)"
                type="time"
                value={heAteHorario}
                onChange={(e) => setHeAteHorario(e.target.value)}
              />
            ) : null}
            {heModo === 'duracao' ? (
              <Input
                label="Minutos"
                type="number"
                min={15}
                max={1440}
                value={heDuracaoMin}
                onChange={(e) => setHeDuracaoMin(e.target.value)}
              />
            ) : null}
            <Input
              label="Motivo (opcional)"
              value={heConcederMotivo}
              onChange={(e) => setHeConcederMotivo(e.target.value)}
            />
            <Button type="button" disabled={concedendoHe} onClick={() => void concederHe()}>
              Conceder HE
            </Button>
          </div>
          <p className="mb-2 text-sm font-medium text-slate-800 dark:text-slate-100">Pedidos pendentes</p>
          {hesPendentes.length === 0 ? (
            <p className="text-sm text-slate-500">Nenhum pedido pendente.</p>
          ) : (
            <ul className="space-y-3">
              {hesPendentes.map((h) => (
                <li
                  key={h.id}
                  className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                >
                  <div className="text-sm">
                    <p className="font-medium">{h.atendente_nome ?? h.atendente_id}</p>
                    <p className="text-slate-600 dark:text-slate-300">{h.motivo || 'Sem motivo informado'}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={decidindoHeId === h.id}
                      onClick={() => void decidirHe(h.id, true)}
                    >
                      Liberar
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={decidindoHeId === h.id}
                      onClick={() => void decidirHe(h.id, false)}
                    >
                      Negar
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Ajuste manual">
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
            Toda alteração de batida exige <strong>motivo</strong> (mínimo 3 caracteres) e fica no histórico
            auditado abaixo e no relatório mensal (PDF/Excel).
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <Select
              label="Atendente"
              value={ajusteAtendente}
              onChange={(v) => setAjusteAtendente(String(v))}
              options={[
                { value: '', label: 'Selecione' },
                ...equipe.map((a) => ({ value: String(a.id), label: a.nome })),
              ]}
            />
            <Select
              label="Tipo"
              value={ajusteTipo}
              onChange={(v) => setAjusteTipo(String(v) as Ponto.Tipo)}
              options={[
                { value: 'entrada', label: 'Entrada' },
                { value: 'saida', label: 'Saída' },
                { value: 'pausa_inicio', label: 'Início de pausa' },
                { value: 'pausa_fim', label: 'Fim de pausa' },
              ]}
            />
            <Input
              label="Data/hora"
              type="datetime-local"
              value={ajusteQuando}
              onChange={(e) => setAjusteQuando(e.target.value)}
            />
            <Input
              label="Motivo do ajuste (obrigatório)"
              value={ajusteMotivo}
              onChange={(e) => setAjusteMotivo(e.target.value)}
              placeholder="Ex.: esquecimento — mínimo 3 caracteres"
            />
            <Button
              type="button"
              disabled={salvandoAjuste || ajusteMotivo.trim().length < 3 || !ajusteAtendente}
              onClick={() => void salvarAjuste()}
            >
              Registrar ajuste
            </Button>
          </div>
        </Card>

        <Card title="Histórico de ajustes">
          <div className="mb-3 flex flex-wrap items-end gap-3">
            <Select
              label="Autor"
              value={ajusteAutorId}
              onChange={(v) => setAjusteAutorId(String(v))}
              options={[
                { value: '', label: 'Todos' },
                ...equipe.map((a) => ({ value: String(a.id), label: a.nome })),
              ]}
            />
            <Input
              label="De"
              type="date"
              value={ajusteAuditDesde}
              onChange={(e) => setAjusteAuditDesde(e.target.value)}
            />
            <Input
              label="Até"
              type="date"
              value={ajusteAuditAte}
              onChange={(e) => setAjusteAuditAte(e.target.value)}
            />
            <Button type="button" variant="secondary" disabled={carregandoAjustes} onClick={() => void carregarAjustesAudit()}>
              Filtrar
            </Button>
            <Button type="button" variant="secondary" onClick={() => void exportarAjustesCsv()}>
              Exportar CSV
            </Button>
          </div>
          {ajustesAudit.length === 0 ? (
            <p className="text-sm text-slate-500">Nenhum ajuste no período.</p>
          ) : (
            <ul className="max-h-64 space-y-2 overflow-y-auto text-sm">
              {ajustesAudit.map((log) => {
                const payload = (log.payload_json ?? {}) as Record<string, unknown>
                const motivo = typeof payload.motivo === 'string' ? payload.motivo : '—'
                const acao =
                  log.action === 'create_ajuste'
                    ? 'Criação'
                    : log.action === 'update_ajuste'
                      ? 'Alteração'
                      : log.action === 'anular'
                        ? 'Anulação'
                        : log.action
                return (
                  <li
                    key={log.id}
                    className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                  >
                    <p className="font-medium text-slate-800 dark:text-slate-100">
                      {acao} · batida #{log.entity_id} · {log.atendente_nome ?? log.atendente_id}
                    </p>
                    <p className="text-slate-600 dark:text-slate-300">{motivo}</p>
                    <p className="text-xs text-slate-500">
                      {log.created_at ? new Date(log.created_at).toLocaleString('pt-BR') : '—'}
                    </p>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>

        <Card title="Histórico">
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Select
              label="Atendente"
              value={atendenteId}
              onChange={(v) => setAtendenteId(String(v))}
              options={[
                { value: '', label: 'Todos' },
                ...equipe.map((a) => ({ value: String(a.id), label: a.nome })),
              ]}
            />
            <Input label="De" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
            <Input label="Até" type="date" value={ate} onChange={(e) => setAte(e.target.value)} />
            <Button type="button" variant="secondary" onClick={() => void carregar()}>
              Filtrar
            </Button>
            <Button type="button" variant="secondary" onClick={() => void exportarCsv()}>
              Exportar CSV
            </Button>
            <Button type="button" variant="secondary" onClick={() => void exportarRelatorio('pdf')}>
              PDF mensal
            </Button>
            <Button type="button" variant="secondary" onClick={() => void exportarRelatorio('xlsx')}>
              Excel mensal
            </Button>
          </div>
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
            {total} batida{total === 1 ? '' : 's'} no filtro
            {banco ? (
              <>
                {' '}
                · Banco de {banco.atendente_nome ?? 'selecionado'}:{' '}
                <strong>
                  {banco.saldo_segundos >= 0 ? '+' : '−'}
                  {formatarDuracao(Math.abs(banco.saldo_segundos))}
                </strong>
              </>
            ) : null}
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                <tr>
                  <th className="py-2 pr-3 font-medium">Atendente</th>
                  <th className="py-2 pr-3 font-medium">Tipo</th>
                  <th className="py-2 pr-3 font-medium">Horário</th>
                  <th className="py-2 pr-3 font-medium">Origem</th>
                  <th className="py-2 font-medium">Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-slate-500">
                      Nenhuma batida neste filtro.
                    </td>
                  </tr>
                ) : (
                  items.map((b) => (
                    <tr key={b.id} className="border-b border-slate-100 dark:border-slate-800/80">
                      <td className="py-2 pr-3">{b.atendente_nome}</td>
                      <td className="py-2 pr-3">{b.tipo.replace('_', ' ')}</td>
                      <td className="py-2 pr-3">{formatarHora(b.registrado_em)}</td>
                      <td className="py-2 pr-3">
                        {b.origem ?? '—'}
                        {b.latitude != null && b.longitude != null ? (
                          <>
                            <span
                              className="ml-1 text-xs text-cyan-700 dark:text-cyan-300"
                              title={`${b.latitude.toFixed(5)}, ${b.longitude.toFixed(5)}${
                                b.accuracy_metros != null ? ` (±${Math.round(b.accuracy_metros)} m)` : ''
                              }`}
                            >
                              · GPS
                            </span>
                            {b.fora_area ? (
                              <span className="ml-1 text-xs text-amber-700 dark:text-amber-300">· fora</span>
                            ) : null}
                            <Button
                              type="button"
                              variant="ghost"
                              className="ml-1 h-auto px-1 py-0 text-xs text-cyan-700 dark:text-cyan-300"
                              onClick={() => setMapaBatida(b)}
                            >
                              mapa
                            </Button>
                          </>
                        ) : null}
                      </td>
                      <td className="py-2">
                        <Button type="button" variant="ghost" onClick={() => void anularBatida(b.id)}>
                          Anular
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {atendenteId ? (
          <Card title="Calendário do atendente">
            <PontoCalendarioMes
              calendario={calendario}
              loading={loadingCal}
              diaSelecionado={diaCal}
              onSelecionarDia={(iso) => {
                setDiaCal(iso)
                setDesde(iso)
                setAte(iso)
              }}
              onMesAnterior={() => {
                if (calMes <= 1) {
                  setCalMes(12)
                  setCalAno((y) => y - 1)
                } else setCalMes((m) => m - 1)
              }}
              onMesSeguinte={() => {
                if (calMes >= 12) {
                  setCalMes(1)
                  setCalAno((y) => y + 1)
                } else setCalMes((m) => m + 1)
              }}
            />
          </Card>
        ) : null}

        <Card title="Configurações do ponto">
          {settings ? (
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={settings.usar_feriados_nacionais}
                  onChange={(e) =>
                    setSettings({ ...settings, usar_feriados_nacionais: e.target.checked })
                  }
                />
                Usar feriados nacionais (BR) na conformidade
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={settings.fecho_automatico_ativo}
                  onChange={(e) =>
                    setSettings({ ...settings, fecho_automatico_ativo: e.target.checked })
                  }
                />
                Fechar jornada esquecida automaticamente (desligado por padrão)
              </label>
              <Input
                label="Horas abertas para fecho (critério 1)"
                type="number"
                min={4}
                max={48}
                value={String(settings.fecho_apos_horas)}
                onChange={(e) =>
                  setSettings({ ...settings, fecho_apos_horas: Number(e.target.value) || 14 })
                }
              />
              <Input
                label="Margem após saída prevista, minutos (critério 2)"
                type="number"
                min={0}
                max={240}
                value={String(settings.fecho_margem_pos_saida_minutos ?? 30)}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    fecho_margem_pos_saida_minutos: Number(e.target.value) || 0,
                  })
                }
              />
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Fecha pelo critério que ocorrer primeiro (N horas abertas ou saída prevista + margem),
                com motivo esquecimento.
              </p>
              <Input
                label="Jornada diária (minutos) — meta do calendário"
                type="number"
                min={60}
                max={1440}
                value={String(settings.jornada_diaria_minutos ?? 480)}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    jornada_diaria_minutos: Number(e.target.value) || 480,
                  })
                }
              />
              <Input
                label="Pausa mínima (minutos)"
                type="number"
                min={0}
                max={240}
                value={String(settings.pausa_minima_minutos ?? 0)}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    pausa_minima_minutos: Math.max(0, Number(e.target.value) || 0),
                  })
                }
              />
              <p className="text-xs text-slate-500 dark:text-slate-400">
                0 = desligado. Se a soma das pausas do dia ficar abaixo do mínimo (com jornada iniciada), o
                calendário e os alertas sinalizam — sem bloquear batidas.
              </p>
              <Select
                label="Política de geolocalização"
                value={settings.politica_geolocalizacao ?? 'opcional'}
                onChange={(v) =>
                  setSettings({
                    ...settings,
                    politica_geolocalizacao: String(v) as Ponto.PoliticaGeolocalizacao,
                  })
                }
                options={[
                  { value: 'opcional', label: rotuloPoliticaGeo('opcional') },
                  { value: 'recomendada', label: rotuloPoliticaGeo('recomendada') },
                  { value: 'obrigatoria', label: rotuloPoliticaGeo('obrigatoria') },
                ]}
              />
              <p className="text-xs text-slate-500">
                Locais ficam no cadastro de cada pessoa (e pin da empresa em Configurações → Empresa). Opcional
                registra geo; recomendada avisa fora da área; obrigatória bloqueia sem GPS ou fora do raio.
              </p>
              <Button type="button" disabled={salvandoSettings} onClick={() => void salvarSettings()}>
                Salvar configurações
              </Button>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Carregando…</p>
          )}
        </Card>

        <Card title="Feriados da instância">
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Input
              label="Data"
              type="date"
              value={feriadoData}
              onChange={(e) => setFeriadoData(e.target.value)}
            />
            <Input
              label="Nome"
              value={feriadoNome}
              onChange={(e) => setFeriadoNome(e.target.value)}
              placeholder="Ex.: Aniversário da rede"
            />
            <Button type="button" onClick={() => void adicionarFeriado()}>
              Adicionar
            </Button>
          </div>
          <ul className="space-y-2 text-sm">
            {feriados.length === 0 ? (
              <li className="text-slate-500">Nenhum feriado custom cadastrado este ano.</li>
            ) : (
              feriados.map((f) => (
                <li
                  key={f.id}
                  className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                >
                  <span>
                    {f.data} · {f.nome}
                  </span>
                  <Button type="button" variant="ghost" onClick={() => void apagarFeriado(f.id)}>
                    Remover
                  </Button>
                </li>
              ))
            )}
          </ul>
        </Card>
      </div>

      <PontoBatidaMapaModal
        open={mapaBatida != null && mapaBatida.latitude != null && mapaBatida.longitude != null}
        onClose={() => setMapaBatida(null)}
        latitude={mapaBatida?.latitude ?? 0}
        longitude={mapaBatida?.longitude ?? 0}
        titulo={
          mapaBatida
            ? `${mapaBatida.atendente_nome} · ${mapaBatida.tipo.replace('_', ' ')}`
            : 'Localização'
        }
        subtitulo={mapaBatida ? formatarHora(mapaBatida.registrado_em) : undefined}
        raioMetros={null}
      />
    </PageContainer>
  )
}
