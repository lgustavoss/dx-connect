import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, atendentes, ponto, type Atendentes, type Ponto } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PontoAjudaModal } from '../components/PontoAjudaModal'
import { PontoCalendarioMes } from '../components/PontoCalendarioMes'
import { calcularMetricasMes, PontoMetricasMes, type MetricasMesPonto } from '../components/PontoMetricasMes'
import { PontoMesNav } from '../components/PontoMesNav'
import { PontoMetricCard } from '../components/PontoMetricCard'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { FormSection } from '../components/ui/FormSection'
import { Input } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { useEventStream } from '../contexts/EventStreamContext'
import {
  boundsSaldoInicialMes,
  formatarDataRef,
  formatarDuracao,
  formatarHora,
  formatarHoraCurta,
  hojeIso,
  quandoSolicitado,
  rotuloPoliticaGeo,
} from '../lib/pontoFormat'
import { SemPermissao } from './SemPermissao'

type ResumoFechamentoColab = {
  atendenteId: number
  nome: string
  metricas: MetricasMesPonto
  diasAbaixo: number
  atrasos: number
  alerta: boolean
  cienciaConfirmada: boolean
  cienciaEm: string | null
}

function boundsMes(ano: number, mes: number): { desde: string; ate: string } {
  const pad = (n: number) => String(n).padStart(2, '0')
  const ultimo = new Date(ano, mes, 0).getDate()
  return {
    desde: `${ano}-${pad(mes)}-01`,
    ate: `${ano}-${pad(mes)}-${pad(ultimo)}`,
  }
}

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
    case 'abono':
      return 'Folga (banco)'
    case 'ok':
      return 'Ok'
    default:
      return 'Livre'
  }
}

function rotuloTipoSolicitacao(tipo: string): string {
  if (tipo === 'inclusao') return 'Inclusão'
  if (tipo === 'abono') return 'Folga (banco)'
  if (tipo === 'correcao') return 'Correção'
  return tipo
}

function rotuloHorarioSolicitacao(s: Ponto.SolicitacaoAjuste): string | null {
  if (s.tipo === 'abono') return null
  const novo = quandoSolicitado(s.data_ref, s.horario_solicitado)
  if (s.tipo === 'correcao' && s.horario_anterior) {
    return `${formatarDataRef(s.data_ref)} · ${formatarHoraCurta(s.horario_anterior)} → ${formatarHoraCurta(s.horario_solicitado)}`
  }
  if (s.tipo === 'inclusao') return `Novo horário: ${novo}`
  return `Horário: ${novo}`
}

type AbaEquipe = 'hoje' | 'espelho' | 'ajustes' | 'fechamento' | 'config'

export function PontoEquipe() {
  const toast = useToast()
  const { user } = useAuth()
  const { subscribe } = useEventStream()
  const [hoje, setHoje] = useState<Ponto.HojeLista | null>(null)
  const [equipe, setEquipe] = useState<Atendentes.Atendente[]>([])
  const [atendenteId, setAtendenteId] = useState('')
  const [loading, setLoading] = useState(true)
  const [semPermissao, setSemPermissao] = useState(false)
  const [solAjusteHistorico, setSolAjusteHistorico] = useState<Ponto.SolicitacaoAjuste[]>([])
  const [carregandoSolHist, setCarregandoSolHist] = useState(false)
  const [setup, setSetup] = useState<Ponto.SetupStatus | null>(null)
  const [compAno, setCompAno] = useState(() => new Date().getFullYear())
  const [compMes, setCompMes] = useState(() => new Date().getMonth() + 1)
  const [competencia, setCompetencia] = useState<Ponto.Competencia | null>(null)
  const [ciencias, setCiencias] = useState<Ponto.CienciaItem[]>([])
  const [ajudaAberta, setAjudaAberta] = useState(false)
  const [digest, setDigest] = useState<Ponto.Digest | null>(null)
  const [banco, setBanco] = useState<Ponto.BancoHoras | null>(null)
  const [bancoMesAnterior, setBancoMesAnterior] = useState<Ponto.BancoHoras | null>(null)
  const [settings, setSettings] = useState<Ponto.Settings | null>(null)
  const [feriados, setFeriados] = useState<Ponto.Feriado[]>([])
  const [feriadoData, setFeriadoData] = useState('')
  const [feriadoNome, setFeriadoNome] = useState('')
  const [feriadoRecorrente, setFeriadoRecorrente] = useState(true)
  const [salvandoSettings, setSalvandoSettings] = useState(false)
  const agoraCal = new Date()
  const [calAno, setCalAno] = useState(agoraCal.getFullYear())
  const [calMes, setCalMes] = useState(agoraCal.getMonth() + 1)
  const [calendario, setCalendario] = useState<Ponto.Calendario | null>(null)
  const [diaCal, setDiaCal] = useState<string | null>(null)
  const [loadingCal, setLoadingCal] = useState(false)
  const [aba, setAba] = useState<AbaEquipe>('hoje')
  const [exportMenuAberto, setExportMenuAberto] = useState(false)
  const exportMenuRef = useRef<HTMLDivElement>(null)
  const [ajusteAno, setAjusteAno] = useState(agoraCal.getFullYear())
  const [ajusteMes, setAjusteMes] = useState(agoraCal.getMonth() + 1)
  const [ajusteAtendenteId, setAjusteAtendenteId] = useState('')

  // Solicitações de ajuste (nova fila)
  const [solAjustePendentes, setSolAjustePendentes] = useState<Ponto.SolicitacaoAjuste[]>([])
  const [decisaoSol, setDecisaoSol] = useState<{
    id: number
    estado: 'aprovada' | 'rejeitada'
  } | null>(null)
  const [decisaoMotivo, setDecisaoMotivo] = useState('')
  const [decidindoSol, setDecidindoSol] = useState(false)
  const [reabrirAberto, setReabrirAberto] = useState(false)
  const [reabrirMotivo, setReabrirMotivo] = useState('')
  const [reabrindo, setReabrindo] = useState(false)
  const [resumoFechamento, setResumoFechamento] = useState<ResumoFechamentoColab[]>([])
  const [loadingResumoFechamento, setLoadingResumoFechamento] = useState(false)
  const [exportandoRelatorioId, setExportandoRelatorioId] = useState<number | null>(null)

  const carregar = useCallback(
    async (silencioso = false) => {
      try {
        const [dia, dig, st, fer, setupSt, comp, cins, solAdj] = await Promise.all([
          ponto.hoje(),
          ponto.digest(),
          ponto.settings(),
          ponto.feriados(new Date().getFullYear()),
          ponto.setupStatus(),
          ponto.competencia(compAno, compMes),
          ponto.cienciasAdmin(compAno, compMes),
          ponto.solicitacoesAjusteAdmin('pendente'),
        ])
        setHoje(dia)
        setDigest(dig)
        setSettings(st)
        setFeriados(fer)
        setSetup(setupSt)
        setCompetencia(comp)
        setCiencias(cins)
        setSolAjustePendentes(solAdj)
        setSemPermissao(false)
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
    [compAno, compMes, toast],
  )

  useEffect(() => {
    void coletarTodasPaginas<Atendentes.Atendente>((o, l) =>
      atendentes.list({ incluir_inativos: false, offset: o, limit: l }),
    ).then((lista) => {
      setEquipe(lista)
      setAtendenteId((cur) => (cur || (lista[0] ? String(lista[0].id) : '')))
    })
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  useEffect(() => {
    const unsub = subscribe('ponto.solicitacao_ajuste', () => {
      void carregar(true)
    })
    return unsub
  }, [subscribe, carregar])

  const carregarSolHistorico = useCallback(async () => {
    setCarregandoSolHist(true)
    try {
      const [aprovadas, rejeitadas] = await Promise.all([
        ponto.solicitacoesAjusteAdmin('aprovada'),
        ponto.solicitacoesAjusteAdmin('rejeitada'),
      ])
      const merged = [...aprovadas, ...rejeitadas].sort((a, b) => {
        const ta = a.decidido_em || a.created_at || ''
        const tb = b.decidido_em || b.created_at || ''
        return tb.localeCompare(ta)
      })
      setSolAjusteHistorico(merged)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o histórico de solicitações.'))
    } finally {
      setCarregandoSolHist(false)
    }
  }, [toast])

  useEffect(() => {
    if (aba === 'ajustes') {
      void carregarSolHistorico()
    }
  }, [aba, carregarSolHistorico])

  useEffect(() => {
    if (aba !== 'fechamento') {
      setResumoFechamento([])
      return
    }
    let cancel = false
    setLoadingResumoFechamento(true)

    void ponto
      .resumoFechamentoEquipe(compAno, compMes)
      .then((data) => {
        if (cancel) return
        const rows: ResumoFechamentoColab[] = (data.itens ?? []).map((item) => ({
          atendenteId: item.atendente_id,
          nome: item.atendente_nome,
          metricas: {
            diasNoMes: item.dias_no_mes,
            diasTrabalhados: item.dias_trabalhados,
            diasATrabalhar: item.dias_a_trabalhar,
            faltas: item.faltas,
            segundosNecessarios: item.segundos_necessarios,
            segundosTrabalhados: item.segundos_trabalhados,
            segundosATrabalhar: item.segundos_a_trabalhar,
            saldoMesAnteriorSeg: item.saldo_mes_anterior_segundos,
            saldoMesSeg: item.saldo_mes_segundos,
            saldoAtualSeg: item.saldo_atual_segundos,
            segundosHePagos: item.segundos_he_pagos ?? 0,
            segundosCreditoBanco: item.segundos_credito_banco ?? 0,
            segundosDebitoBanco: item.segundos_debito_banco ?? 0,
          },
          diasAbaixo: item.dias_abaixo ?? 0,
          atrasos: item.atrasos ?? 0,
          alerta: !!item.alerta,
          cienciaConfirmada: !!item.ciencia_confirmada,
          cienciaEm: item.ciencia_em ?? null,
        }))
        rows.sort((a, b) => {
          if (a.alerta !== b.alerta) return a.alerta ? -1 : 1
          return a.nome.localeCompare(b.nome, 'pt-BR')
        })
        setResumoFechamento(rows)
      })
      .catch((err) => {
        if (!cancel) {
          toast.showError(
            mensagemFalhaParaToast(err, 'Não foi possível carregar o resumo do fechamento.'),
          )
        }
      })
      .finally(() => {
        if (!cancel) setLoadingResumoFechamento(false)
      })

    return () => {
      cancel = true
    }
  }, [aba, compAno, compMes, toast])

  const totaisFechamento = useMemo(() => {
    const comAlerta = resumoFechamento.filter((r) => r.alerta).length
    const ok = resumoFechamento.length - comAlerta
    const cienciaPend = resumoFechamento.filter((r) => !r.cienciaConfirmada).length
    const faltas = resumoFechamento.reduce((acc, r) => acc + r.metricas.faltas, 0)
    const credito = resumoFechamento.reduce((acc, r) => acc + r.metricas.segundosCreditoBanco, 0)
    const debito = resumoFechamento.reduce((acc, r) => acc + r.metricas.segundosDebitoBanco, 0)
    return { ok, comAlerta, cienciaPend, faltas, credito, debito }
  }, [resumoFechamento])

  const solPendentesFiltradas = useMemo(() => {
    if (!ajusteAtendenteId) return solAjustePendentes
    const id = Number(ajusteAtendenteId)
    return solAjustePendentes.filter((s) => s.atendente_id === id)
  }, [solAjustePendentes, ajusteAtendenteId])

  const solHistoricoFiltrado = useMemo(() => {
    const { desde, ate } = boundsMes(ajusteAno, ajusteMes)
    return solAjusteHistorico.filter((s) => {
      if (s.data_ref < desde || s.data_ref > ate) return false
      if (ajusteAtendenteId && s.atendente_id !== Number(ajusteAtendenteId)) return false
      return true
    })
  }, [solAjusteHistorico, ajusteAno, ajusteMes, ajusteAtendenteId])

  const rotuloMesAjuste = useMemo(
    () =>
      new Date(ajusteAno, ajusteMes - 1, 1).toLocaleDateString('pt-BR', {
        month: 'long',
        year: 'numeric',
      }),
    [ajusteAno, ajusteMes],
  )

  useEffect(() => {
    if (!atendenteId) {
      setCalendario(null)
      setBanco(null)
      setBancoMesAnterior(null)
      return
    }
    let cancel = false
    setLoadingCal(true)
    const { desde, ate } = boundsMes(calAno, calMes)
    const saldoIni = boundsSaldoInicialMes(calAno, calMes)
    void Promise.all([
      ponto.calendarioAdmin(Number(atendenteId), calAno, calMes),
      ponto.bancoHorasAdmin(Number(atendenteId), desde, ate),
      ponto.bancoHorasAdmin(Number(atendenteId), saldoIni.desde, saldoIni.ate),
    ])
      .then(([cal, bh, bhPrev]) => {
        if (cancel) return
        setCalendario(cal)
        setBanco(bh)
        setBancoMesAnterior(bhPrev)
      })
      .catch((err) => {
        if (!cancel) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o espelho do colaborador.'))
        }
      })
      .finally(() => {
        if (!cancel) setLoadingCal(false)
      })
    return () => {
      cancel = true
    }
  }, [atendenteId, calAno, calMes, toast])

  useEffect(() => {
    if (!exportMenuAberto) return
    const onDoc = (e: MouseEvent) => {
      if (!exportMenuRef.current?.contains(e.target as Node)) setExportMenuAberto(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [exportMenuAberto])

  const metricasEspelho = useMemo(
    () => calcularMetricasMes(calendario, banco, bancoMesAnterior, hojeIso()),
    [calendario, banco, bancoMesAnterior],
  )

  function periodoExportacao() {
    return boundsMes(calAno, calMes)
  }

  function exigirAtendenteSelecionado(): number | null {
    if (!atendenteId) {
      toast.showWarning('Selecione um colaborador para exportar.')
      return null
    }
    return Number(atendenteId)
  }

  async function exportarCsv() {
    const id = exigirAtendenteSelecionado()
    if (id == null) return
    const { desde, ate } = periodoExportacao()
    try {
      const blob = await ponto.exportCsv({ atendente_id: id, desde, ate })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ponto_batidas_${desde}_${ate}.csv`
      a.click()
      URL.revokeObjectURL(url)
      setExportMenuAberto(false)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível exportar o CSV.'))
    }
  }

  async function exportarRelatorio(ext: 'pdf' | 'xlsx') {
    const id = exigirAtendenteSelecionado()
    if (id == null) return
    const { desde, ate } = periodoExportacao()
    try {
      const params = { atendente_id: id, desde, ate }
      const blob =
        ext === 'pdf' ? await ponto.exportPdf(params) : await ponto.exportXlsx(params)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = ext === 'pdf' ? `ponto_relatorio_${desde}.pdf` : `ponto_relatorio_${desde}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      setExportMenuAberto(false)
    } catch (err) {
      toast.showError(
        mensagemFalhaParaToast(err, `Não foi possível exportar o ${ext.toUpperCase()}.`),
      )
    }
  }

  async function exportarFolha(ext: 'csv' | 'xlsx') {
    const id = exigirAtendenteSelecionado()
    if (id == null) return
    const { desde, ate } = periodoExportacao()
    try {
      const blob = await ponto.exportFolha(ext, { atendente_id: id, desde, ate })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = ext === 'csv' ? `ponto_folha_${desde}.csv` : `ponto_folha_${desde}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      setExportMenuAberto(false)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível exportar a folha RH.'))
    }
  }

  async function decidirSolAjuste(id: number, estado: 'aprovada' | 'rejeitada') {
    if (estado === 'aprovada') {
      try {
        await ponto.decidirSolicitacaoAjuste(id, { estado: 'aprovada' })
        toast.showSuccess('Solicitação aprovada.')
        await Promise.all([carregar(true), carregarSolHistorico()])
      } catch (err) {
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível aprovar a solicitação.'))
      }
      return
    }
    setDecisaoMotivo('')
    setDecisaoSol({ id, estado: 'rejeitada' })
  }

  async function confirmarRejeicaoSol() {
    if (!decisaoSol) return
    if (!decisaoMotivo.trim() || decisaoMotivo.trim().length < 3) {
      toast.showWarning('Informe o motivo da rejeição (mínimo 3 caracteres).')
      return
    }
    setDecidindoSol(true)
    try {
      await ponto.decidirSolicitacaoAjuste(decisaoSol.id, {
        estado: 'rejeitada',
        decisao_motivo: decisaoMotivo.trim(),
      })
      toast.showSuccess('Solicitação rejeitada.')
      setDecisaoSol(null)
      setDecisaoMotivo('')
      await Promise.all([carregar(true), carregarSolHistorico()])
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível rejeitar a solicitação.'))
    } finally {
      setDecidindoSol(false)
    }
  }

  async function confirmarReabrirCompetencia() {
    if (!reabrirMotivo.trim() || reabrirMotivo.trim().length < 3) {
      toast.showWarning('Informe o motivo da reabertura (mínimo 3 caracteres).')
      return
    }
    setReabrindo(true)
    try {
      await ponto.reabrirCompetencia(compAno, compMes, { motivo: reabrirMotivo.trim() })
      toast.showSuccess('Competência reaberta.')
      setReabrirAberto(false)
      setReabrirMotivo('')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível reabrir.'))
    } finally {
      setReabrindo(false)
    }
  }

  function abrirEspelhoColab(atendenteId: number) {
    setAtendenteId(String(atendenteId))
    setCalAno(compAno)
    setCalMes(compMes)
    setDiaCal(null)
    setAba('espelho')
  }

  async function exportarPdfColab(atendenteId: number, nome: string) {
    const { desde, ate } = boundsMes(compAno, compMes)
    setExportandoRelatorioId(atendenteId)
    try {
      const blob = await ponto.exportPdf({ atendente_id: atendenteId, desde, ate })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ponto_${nome.replace(/\s+/g, '_').toLowerCase()}_${desde}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível gerar o relatório PDF.'))
    } finally {
      setExportandoRelatorioId(null)
    }
  }

  function rotuloSaldoFechamento(seg: number): string {
    if (seg === 0) return '0'
    const sinal = seg > 0 ? '+' : '−'
    return `${sinal}${formatarDuracao(Math.abs(seg))}`
  }

  async function baixarAnexoSol(s: Ponto.SolicitacaoAjuste) {
    try {
      const blob = await ponto.fetchSolicitacaoAjusteAnexoBlob(s.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = s.anexo_nome || `anexo-solicitacao-${s.id}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível baixar o anexo.'))
    }
  }

  async function salvarSettings() {
    if (!settings) return
    setSalvandoSettings(true)
    try {
      const st = await ponto.updateSettings({
        usar_feriados_nacionais: settings.usar_feriados_nacionais,
        // Fecho automático descontinuado: saída esquecida → solicitação de ajuste pelo colaborador.
        fecho_automatico_ativo: false,
        fecho_apos_horas: settings.fecho_apos_horas,
        fecho_margem_pos_saida_minutos: settings.fecho_margem_pos_saida_minutos ?? 30,
        jornada_diaria_minutos: settings.jornada_diaria_minutos,
        pausa_minima_minutos: settings.pausa_minima_minutos ?? 0,
        he_teto_mensal_minutos: null,
        politica_geolocalizacao: settings.politica_geolocalizacao,
        banco_horas_ativo: settings.banco_horas_ativo ?? true,
        he_destino_excedente: settings.he_destino_excedente ?? 'banco',
        he_banco_primeiros_minutos: settings.he_banco_primeiros_minutos ?? 120,
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
      await ponto.criarFeriado({
        data: feriadoData,
        nome: feriadoNome.trim(),
        recorrente_anual: feriadoRecorrente,
      })
      toast.showSuccess(
        feriadoRecorrente
          ? 'Feriado cadastrado (repete nos anos seguintes).'
          : 'Feriado cadastrado.',
      )
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

  const solicitacoesPendentes = digest?.solicitacoes_ajuste_pendentes ?? digest?.justificativas_pendentes ?? 0
  const setupPendentes = setup?.pendentes ?? 0
  const cienciasPendentes = ciencias.filter((c) => !c.confirmada).length

  const abas: { id: AbaEquipe; label: string; badge?: number }[] = [
    { id: 'hoje', label: 'Hoje' },
    { id: 'espelho', label: 'Espelho' },
    {
      id: 'ajustes',
      label: 'Ajustes',
      badge: solicitacoesPendentes > 0 ? solicitacoesPendentes : undefined,
    },
    {
      id: 'fechamento',
      label: 'Fechamento',
      badge: cienciasPendentes > 0 ? cienciasPendentes : undefined,
    },
    {
      id: 'config',
      label: 'Configurações',
      badge: setupPendentes > 0 ? setupPendentes : undefined,
    },
  ]

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
        subtitle="O colaborador pede o ajuste; você decide. Batidas, fechamento e configurações ficam nas outras abas."
        actions={
          <Button
            type="button"
            variant="ghost"
            onClick={() => setAjudaAberta(true)}
            title="Abrir ajuda do ponto"
          >
            Ajuda
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800">
        {abas.map((t) => (
          <button
            key={t.id}
            type="button"
            aria-current={aba === t.id ? 'page' : undefined}
            onClick={() => setAba(t.id)}
            className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition ${
              aba === t.id
                ? 'border-b-2 border-cyan-600 text-cyan-800 dark:border-cyan-400 dark:text-cyan-200'
                : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            {t.label}
            {t.badge != null ? (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900 dark:bg-amber-950/60 dark:text-amber-100">
                {t.badge}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      {setupPendentes > 0 && aba !== 'config' ? (
        <Card className="mb-4 border-amber-200 bg-amber-50/80 dark:border-amber-900/50 dark:bg-amber-950/30">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <p className="text-amber-950 dark:text-amber-100">
              Há <strong>{setupPendentes}</strong> item(ns) pendente(s) na configuração do ponto.
            </p>
            <Button type="button" variant="secondary" onClick={() => setAba('config')}>
              Abrir configurações
            </Button>
          </div>
        </Card>
      ) : null}

      {aba === 'hoje' ? (
      <div className="space-y-4">
      <Card className="overflow-hidden border-cyan-200/60 bg-gradient-to-br from-slate-50 via-white to-cyan-50/40 dark:border-cyan-900/40 dark:from-slate-950 dark:via-slate-900 dark:to-cyan-950/20">
        {loading && !digest ? (
          <div className="h-28 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
        ) : (
          <div className="space-y-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Digest de hoje
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
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
                label="Solicitações de ajuste"
                value={String(solicitacoesPendentes)}
                hint="pendentes"
                tone={solicitacoesPendentes > 0 ? 'warn' : 'neutral'}
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

        <Card title="Equipe hoje">
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

        {solicitacoesPendentes > 0 ? (
          <Card className="border-amber-200/80 dark:border-amber-900/40">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium text-slate-900 dark:text-slate-50">
                  {solicitacoesPendentes} solicitação{solicitacoesPendentes === 1 ? '' : 'ões'} aguardando decisão
                </p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                  O colaborador pede inclusão, correção ou folga; você só aprova ou rejeita.
                </p>
              </div>
              <Button type="button" onClick={() => setAba('ajustes')}>
                Ir para Ajustes
              </Button>
            </div>
          </Card>
        ) : null}
      </div>
      ) : null}

      {aba === 'ajustes' ? (
      <div className="space-y-4">
        <Card
          title="Ajustes"
          description="Filtre por colaborador e mês. A fila mostra o que ainda falta decidir; o histórico só o mês escolhido."
          titleActions={
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-[14rem] w-64">
                <Select
                  label="Colaborador"
                  value={ajusteAtendenteId}
                  onChange={(v) => setAjusteAtendenteId(String(v))}
                  options={[
                    { value: '', label: 'Todos' },
                    ...equipe.map((a) => ({ value: String(a.id), label: a.nome })),
                  ]}
                />
              </div>
              <div className="pt-[1.625rem]">
                <PontoMesNav
                  ano={ajusteAno}
                  mes={ajusteMes}
                  onChange={(ano, mes) => {
                    setAjusteAno(ano)
                    setAjusteMes(mes)
                  }}
                />
              </div>
            </div>
          }
        >
          <div className="space-y-6">
            <section>
              <h3 className="mb-3 text-sm font-semibold text-slate-900 dark:text-slate-50">
                Fila para decidir
                {solPendentesFiltradas.length > 0 ? (
                  <span className="ml-2 font-normal text-slate-500">
                    ({solPendentesFiltradas.length})
                  </span>
                ) : null}
              </h3>
              {solPendentesFiltradas.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center dark:border-slate-700">
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    Nenhuma solicitação pendente
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {ajusteAtendenteId
                      ? 'Este colaborador não tem pedidos aguardando decisão.'
                      : 'Quando alguém pedir ajuste em Meu ponto, o pedido aparece aqui.'}
                  </p>
                </div>
              ) : (
                <ul className="space-y-3">
                  {solPendentesFiltradas.map((s) => (
                    <li
                      key={s.id}
                      className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-800 dark:bg-slate-950/40"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-base font-semibold text-slate-900 dark:text-slate-50">
                              {s.atendente_nome ?? `Atendente #${s.atendente_id}`}
                            </span>
                            <span className="rounded-full bg-cyan-100 px-2.5 py-0.5 text-xs font-semibold text-cyan-900 dark:bg-cyan-950/50 dark:text-cyan-100">
                              {rotuloTipoSolicitacao(s.tipo)}
                            </span>
                            {s.tipo !== 'abono' ? (
                              <span className="text-xs text-slate-500">
                                {s.tipo_batida === 'entrada' ? 'Entrada' : 'Saída'}
                              </span>
                            ) : null}
                          </div>
                          <p className="text-sm text-slate-600 dark:text-slate-300">
                            Ref. {s.data_ref}
                            {rotuloHorarioSolicitacao(s) ? ` · ${rotuloHorarioSolicitacao(s)}` : ''}
                          </p>
                          <p className="text-sm text-slate-800 dark:text-slate-100">{s.motivo}</p>
                          {s.tem_anexo ? (
                            <button
                              type="button"
                              className="text-sm font-medium text-cyan-700 underline dark:text-cyan-300"
                              onClick={() => void baixarAnexoSol(s)}
                            >
                              Ver anexo{s.anexo_nome ? ` (${s.anexo_nome})` : ''}
                            </button>
                          ) : null}
                        </div>
                        <div className="flex shrink-0 flex-wrap gap-2">
                          <Button type="button" onClick={() => void decidirSolAjuste(s.id, 'aprovada')}>
                            Aprovar
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => void decidirSolAjuste(s.id, 'rejeitada')}
                          >
                            Rejeitar
                          </Button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold capitalize text-slate-900 dark:text-slate-50">
                  Histórico · {rotuloMesAjuste}
                  {solHistoricoFiltrado.length > 0 ? (
                    <span className="ml-2 font-normal normal-case text-slate-500">
                      ({solHistoricoFiltrado.length})
                    </span>
                  ) : null}
                </h3>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={carregandoSolHist}
                  onClick={() => void carregarSolHistorico()}
                >
                  Atualizar
                </Button>
              </div>
              {carregandoSolHist && solAjusteHistorico.length === 0 ? (
                <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
              ) : solHistoricoFiltrado.length === 0 ? (
                <p className="text-sm text-slate-500">
                  Nenhum pedido decidido neste mês
                  {ajusteAtendenteId ? ' para este colaborador' : ''}.
                </p>
              ) : (
                <ul className="space-y-3">
                  {solHistoricoFiltrado.map((s) => {
                    const aprovada = s.estado === 'aprovada'
                    return (
                      <li
                        key={s.id}
                        className="rounded-xl border border-slate-200 px-4 py-3 dark:border-slate-800"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="min-w-0 space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-semibold text-slate-900 dark:text-slate-50">
                                {s.atendente_nome ?? `#${s.atendente_id}`}
                              </span>
                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                                {rotuloTipoSolicitacao(s.tipo)}
                              </span>
                              <span
                                className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                                  aprovada
                                    ? 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100'
                                    : 'bg-rose-100 text-rose-900 dark:bg-rose-950/50 dark:text-rose-100'
                                }`}
                              >
                                {aprovada ? 'Aprovada' : 'Rejeitada'}
                              </span>
                            </div>
                            <p className="text-sm text-slate-600 dark:text-slate-300">
                              {s.data_ref}
                              {rotuloHorarioSolicitacao(s) ? ` · ${rotuloHorarioSolicitacao(s)}` : ''}
                              {' · '}
                              {s.motivo}
                            </p>
                            {s.decisao_motivo ? (
                              <p className="text-xs text-slate-500">
                                Decisão: {s.decisao_motivo}
                                {s.decidido_em
                                  ? ` · ${new Date(s.decidido_em).toLocaleString('pt-BR')}`
                                  : ''}
                              </p>
                            ) : s.decidido_em ? (
                              <p className="text-xs text-slate-500">
                                {new Date(s.decidido_em).toLocaleString('pt-BR')}
                              </p>
                            ) : null}
                            {s.tem_anexo ? (
                              <button
                                type="button"
                                className="text-xs font-medium text-cyan-700 underline dark:text-cyan-300"
                                onClick={() => void baixarAnexoSol(s)}
                              >
                                Anexo{s.anexo_nome ? `: ${s.anexo_nome}` : ''}
                              </button>
                            ) : null}
                          </div>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </section>
          </div>
        </Card>
      </div>
      ) : null}

      {aba === 'espelho' ? (
      <div className="space-y-4">
        <Card
          title="Espelho do colaborador"
          description="Selecione uma pessoa para ver o mês no calendário e exportar só os dados dela."
          titleActions={
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-[14rem] w-64">
                <Select
                  label="Colaborador"
                  value={atendenteId}
                  onChange={(v) => setAtendenteId(String(v))}
                  options={equipe.map((a) => ({ value: String(a.id), label: a.nome }))}
                />
              </div>
              <div className="relative pt-[1.625rem]" ref={exportMenuRef}>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={!atendenteId}
                  onClick={() => setExportMenuAberto((o) => !o)}
                >
                  Exportar
                </Button>
                {exportMenuAberto ? (
                  <div className="absolute right-0 z-20 mt-1 w-56 rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                    <button
                      type="button"
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                      onClick={() => void exportarCsv()}
                    >
                      Batidas (CSV)
                    </button>
                    <button
                      type="button"
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                      onClick={() => void exportarRelatorio('pdf')}
                    >
                      Relatório mensal (PDF)
                    </button>
                    <button
                      type="button"
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                      onClick={() => void exportarRelatorio('xlsx')}
                    >
                      Relatório mensal (Excel)
                    </button>
                    <button
                      type="button"
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                      onClick={() => void exportarFolha('csv')}
                    >
                      Folha RH (CSV)
                    </button>
                    <button
                      type="button"
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                      onClick={() => void exportarFolha('xlsx')}
                    >
                      Folha RH (Excel)
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          }
        >
          {!atendenteId ? (
            <p className="text-sm text-slate-500">Nenhum colaborador disponível.</p>
          ) : (
            <div className="space-y-4">
              <PontoMetricasMes metricas={metricasEspelho} loading={loadingCal} />
              <PontoCalendarioMes
                calendario={calendario}
                loading={loadingCal}
                diaSelecionado={diaCal}
                onSelecionarDia={(iso) => setDiaCal(iso)}
                ano={calAno}
                mes={calMes}
                onMudarMes={(ano, mes) => {
                  setCalAno(ano)
                  setCalMes(mes)
                }}
              />
            </div>
          )}
        </Card>
      </div>
      ) : null}

      {aba === 'fechamento' ? (
      <div className="space-y-4">
        <Card
          title="Competência mensal"
          description="Fecha o espelho do mês para a equipe confirmar ciência. Depois do fechamento, novos ajustes ficam marcados como pós-fechamento (auditoria)."
        >
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <PontoMesNav
              ano={compAno}
              mes={compMes}
              onChange={(ano, mes) => {
                setCompAno(ano)
                setCompMes(mes)
              }}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                disabled={!!competencia?.fechada}
                title={
                  competencia?.fechada
                    ? 'Este mês já está fechado'
                    : 'Travar o mês e liberar a ciência para a equipe'
                }
                onClick={() => {
                  void (async () => {
                    try {
                      await ponto.fecharCompetencia(compAno, compMes)
                      toast.showSuccess('Mês fechado. A equipe pode confirmar ciência do espelho.')
                      await carregar(true)
                    } catch (err) {
                      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível fechar.'))
                    }
                  })()
                }}
              >
                Fechar mês
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={!competencia?.fechada}
                title={
                  competencia?.fechada
                    ? 'Reabrir para permitir ajustes normais neste mês'
                    : 'Só disponível depois de fechar o mês'
                }
                onClick={() => {
                  setReabrirMotivo('')
                  setReabrirAberto(true)
                }}
              >
                Reabrir
              </Button>
            </div>
          </div>
          <div
            className={`rounded-lg border px-3 py-2 text-sm ${
              competencia?.fechada
                ? 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100'
                : 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300'
            }`}
          >
            {competencia?.fechada ? (
              <>
                <p className="font-medium">Mês fechado</p>
                <p className="mt-0.5">
                  {competencia.fechado_por_nome ? `Por ${competencia.fechado_por_nome}` : 'Fechado'}
                  {competencia.fechado_em
                    ? ` em ${new Date(competencia.fechado_em).toLocaleString('pt-BR')}`
                    : ''}
                  . A equipe pode confirmar ciência; ajustes novos neste mês entram como pós-fechamento.
                </p>
                {competencia.reabrir_motivo ? (
                  <p className="mt-1 text-xs opacity-80">
                    Última reabertura: {competencia.reabrir_motivo}
                  </p>
                ) : null}
              </>
            ) : (
              <>
                <p className="font-medium">Mês aberto</p>
                <p className="mt-0.5">
                  Ajustes e solicitações seguem normais. Use <strong>Fechar mês</strong> quando o
                  espelho estiver conferido e for hora da equipe dar ciência.
                </p>
              </>
            )}
          </div>
          <div className="mt-4 space-y-3">
            <div>
              <p className="mb-2 text-sm font-medium text-slate-800 dark:text-slate-100">
                Resumo da equipe no mês
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                <PontoMetricCard
                  tone="good"
                  label="Em dia"
                  value={loadingResumoFechamento ? '…' : String(totaisFechamento.ok)}
                  hint="Sem faltas/atrasos relevantes"
                />
                <PontoMetricCard
                  tone={totaisFechamento.comAlerta > 0 ? 'warn' : 'info'}
                  label="Com alerta"
                  value={loadingResumoFechamento ? '…' : String(totaisFechamento.comAlerta)}
                  hint="Falta, atraso ou abaixo da meta"
                />
                <PontoMetricCard
                  tone={totaisFechamento.faltas > 0 ? 'warn' : 'info'}
                  label="Faltas (p/ desconto)"
                  value={loadingResumoFechamento ? '…' : String(totaisFechamento.faltas)}
                  hint="Não abonadas — folha"
                />
                <PontoMetricCard
                  tone="good"
                  label="Crédito banco"
                  value={
                    loadingResumoFechamento
                      ? '…'
                      : totaisFechamento.credito > 0
                        ? `+${formatarDuracao(totaisFechamento.credito)}`
                        : '0'
                  }
                  hint="Horas geradas no mês"
                />
                <PontoMetricCard
                  tone={totaisFechamento.debito > 0 ? 'warn' : 'info'}
                  label="Débito banco"
                  value={
                    loadingResumoFechamento
                      ? '…'
                      : totaisFechamento.debito > 0
                        ? `−${formatarDuracao(totaisFechamento.debito)}`
                        : '0'
                  }
                  hint="Parcial + folga (banco)"
                />
                <PontoMetricCard
                  tone={
                    competencia?.fechada && totaisFechamento.cienciaPend > 0 ? 'warn' : 'info'
                  }
                  label="Ciência pendente"
                  value={loadingResumoFechamento ? '…' : String(totaisFechamento.cienciaPend)}
                  hint={
                    competencia?.fechada
                      ? 'Aguardando confirmação'
                      : 'Após fechar o mês'
                  }
                />
              </div>
              {!competencia?.fechada && totaisFechamento.comAlerta > 0 && !loadingResumoFechamento ? (
                <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
                  Há {totaisFechamento.comAlerta} colaborador
                  {totaisFechamento.comAlerta === 1 ? '' : 'es'} com alerta — confira antes de
                  fechar.
                </p>
              ) : null}
            </div>

            {loadingResumoFechamento && resumoFechamento.length === 0 ? (
              <div className="h-40 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
            ) : resumoFechamento.length === 0 ? (
              <p className="text-sm text-slate-500">Sem colaboradores ativos.</p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900/60 dark:text-slate-400">
                    <tr>
                      <th className="px-3 py-2 font-medium">Colaborador</th>
                      <th className="px-3 py-2 font-medium">Dias</th>
                      <th className="px-3 py-2 font-medium">Faltas</th>
                      <th className="px-3 py-2 font-medium">Saldo inicial</th>
                      <th className="px-3 py-2 font-medium">Crédito</th>
                      <th className="px-3 py-2 font-medium">Débito</th>
                      <th className="px-3 py-2 font-medium">Saldo mês</th>
                      <th className="px-3 py-2 font-medium">Ciência</th>
                      <th className="px-3 py-2 font-medium">Situação</th>
                      <th className="px-3 py-2 font-medium">Relatório</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resumoFechamento.map((r) => (
                      <tr
                        key={r.atendenteId}
                        className="border-t border-slate-100 dark:border-slate-800"
                      >
                        <td className="px-3 py-2.5 font-medium text-slate-900 dark:text-slate-50">
                          {r.nome}
                        </td>
                        <td className="px-3 py-2.5 tabular-nums text-slate-600 dark:text-slate-300">
                          {r.metricas.diasTrabalhados}/{r.metricas.diasNoMes}
                        </td>
                        <td
                          className={`px-3 py-2.5 tabular-nums ${
                            r.metricas.faltas > 0
                              ? 'font-semibold text-amber-700 dark:text-amber-300'
                              : 'text-slate-600 dark:text-slate-300'
                          }`}
                        >
                          {r.metricas.faltas}
                        </td>
                        <td className="px-3 py-2.5 tabular-nums text-slate-600 dark:text-slate-300">
                          {rotuloSaldoFechamento(r.metricas.saldoMesAnteriorSeg)}
                        </td>
                        <td className="px-3 py-2.5 tabular-nums text-emerald-700 dark:text-emerald-300">
                          {r.metricas.segundosCreditoBanco > 0
                            ? `+${formatarDuracao(r.metricas.segundosCreditoBanco)}`
                            : '0'}
                        </td>
                        <td className="px-3 py-2.5 tabular-nums text-amber-700 dark:text-amber-300">
                          {r.metricas.segundosDebitoBanco > 0
                            ? `−${formatarDuracao(r.metricas.segundosDebitoBanco)}`
                            : '0'}
                        </td>
                        <td className="px-3 py-2.5 tabular-nums text-slate-600 dark:text-slate-300">
                          {rotuloSaldoFechamento(r.metricas.saldoMesSeg)}
                        </td>
                        <td className="px-3 py-2.5">
                          {r.cienciaConfirmada ? (
                            <span className="text-emerald-700 dark:text-emerald-300">
                              Confirmou
                              {r.cienciaEm
                                ? ` · ${new Date(r.cienciaEm).toLocaleDateString('pt-BR')}`
                                : ''}
                            </span>
                          ) : (
                            <span className="text-amber-700 dark:text-amber-300">
                              {competencia?.fechada ? 'Pendente' : '—'}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2.5">
                          {r.alerta ? (
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900 dark:bg-amber-950/50 dark:text-amber-100">
                              Atenção
                              {r.metricas.faltas > 0 ? ` · ${r.metricas.faltas} falta(s)` : ''}
                              {r.atrasos > 0 ? ` · ${r.atrasos} atraso(s)` : ''}
                              {r.diasAbaixo > 0 ? ` · ${r.diasAbaixo} abaixo` : ''}
                            </span>
                          ) : (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100">
                              OK
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex flex-wrap gap-1.5">
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={() => abrirEspelhoColab(r.atendenteId)}
                            >
                              Ver espelho
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              disabled={exportandoRelatorioId === r.atendenteId}
                              onClick={() => void exportarPdfColab(r.atendenteId, r.nome)}
                            >
                              {exportandoRelatorioId === r.atendenteId ? 'Gerando…' : 'PDF'}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </Card>
      </div>
      ) : null}

      {aba === 'config' ? (
      <div className="space-y-4">
        {setup && setup.pendentes > 0 ? (
          <Card
            className="border-amber-200 bg-amber-50/80 dark:border-amber-900/50 dark:bg-amber-950/30"
            title="Checklist de configuração"
          >
            <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
              Confira jornada dos colaboradores e geolocalização. Saída esquecida é tratada via
              solicitação de ajuste (sem fechamento automático).
            </p>
            <ul className="space-y-2 text-sm">
              {setup.itens
                .filter((i) => !i.ok)
                .map((i) => (
                  <li key={i.codigo} className="flex flex-wrap items-center justify-between gap-2">
                    <span>
                      <strong>{i.titulo}</strong> — {i.detalhe}
                    </span>
                    {i.destino === 'cadastro_atendentes' ? (
                      <Link to="/atendentes" className="text-cyan-700 underline dark:text-cyan-300">
                        Abrir cadastro
                      </Link>
                    ) : (
                      <a href="#ponto-settings" className="text-cyan-700 underline dark:text-cyan-300">
                        Ir às configurações abaixo
                      </a>
                    )}
                  </li>
                ))}
            </ul>
          </Card>
        ) : null}

        <div id="ponto-settings">
        <Card title="Configurações do ponto">
          {settings ? (
            <div className="space-y-5">
              <FormSection
                compact
                title="Conformidade"
                className="rounded-xl border border-slate-200/90 p-4 dark:border-slate-800/60"
              >
                <div className="grid gap-3 sm:grid-cols-2">
                  <Switch
                    tight
                    checked={settings.usar_feriados_nacionais}
                    onCheckedChange={(v) =>
                      setSettings({ ...settings, usar_feriados_nacionais: v })
                    }
                    label="Feriados nacionais (BR)"
                    description="Contam na conformidade do calendário"
                    className="h-full w-full"
                  />
                  <Switch
                    tight
                    checked={settings.banco_horas_ativo ?? true}
                    onCheckedChange={(v) =>
                      setSettings({ ...settings, banco_horas_ativo: v })
                    }
                    label="Banco de horas"
                    description="Credita excesso além da jornada"
                    className="h-full w-full"
                  />
                </div>
                {(settings.banco_horas_ativo ?? true) ? (
                  <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                    O saldo acumula entre meses no período de compensação (CLT: até 6 meses em acordo
                    individual escrito, ou até 12 com norma coletiva). Débito em folha só com
                    previsão em acordo/convenção.
                  </p>
                ) : null}
              </FormSection>

              <FormSection
                compact
                title="Jornada e hora extra"
                className="rounded-xl border border-slate-200/90 p-4 dark:border-slate-800/60"
              >
                <div className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-6">
                  <div
                    className={
                      (settings.he_destino_excedente ?? 'banco') === 'misto'
                        ? 'sm:col-span-4'
                        : 'sm:col-span-6 max-w-xl'
                    }
                  >
                    <Select
                      label="Destino do excesso"
                      value={settings.he_destino_excedente ?? 'banco'}
                      onChange={(v) =>
                        setSettings({
                          ...settings,
                          he_destino_excedente: String(v) as Ponto.HeDestinoExcedente,
                        })
                      }
                      options={[
                        { value: 'banco', label: 'Todo o excesso no banco' },
                        { value: 'pagamento', label: 'Todo o excesso a pagar' },
                        {
                          value: 'misto',
                          label: 'Misto — banco primeiro, resto pago',
                        },
                      ]}
                    />
                  </div>
                  {(settings.he_destino_excedente ?? 'banco') === 'misto' ? (
                    <div className="sm:col-span-2">
                      <Input
                        label="Minutos no banco / dia"
                        type="number"
                        min={0}
                        max={1440}
                        value={String(settings.he_banco_primeiros_minutos ?? 120)}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            he_banco_primeiros_minutos: Math.max(0, Number(e.target.value) || 0),
                          })
                        }
                      />
                      <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                        Ex.: 120 = 2h no banco; o resto a pagar
                      </p>
                    </div>
                  ) : null}

                  <div className="sm:col-span-2">
                    <Input
                      label="Jornada diária (horas)"
                      type="number"
                      min={1}
                      max={24}
                      step={1}
                      value={String(Math.round((settings.jornada_diaria_minutos ?? 480) / 60) || 8)}
                      onChange={(e) => {
                        const horas = Math.min(24, Math.max(1, Number(e.target.value) || 8))
                        setSettings({
                          ...settings,
                          jornada_diaria_minutos: horas * 60,
                        })
                      }}
                    />
                    <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                      Meta sem escala no dia
                    </p>
                  </div>
                  <div className="sm:col-span-2">
                    <Input
                      label="Pausa mínima (min)"
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
                    <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                      0 = desligado; só alerta
                    </p>
                  </div>
                  <div className="sm:col-span-2">
                    <Select
                      label="Geolocalização"
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
                    <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                      Locais no cadastro de cada pessoa
                    </p>
                  </div>
                </div>
                <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  Opcional registra GPS; recomendada avisa fora da área; obrigatória bloqueia sem GPS
                  ou fora do raio. Pin da empresa em Configurações → Empresa.
                </p>
                <p className="rounded-lg border border-slate-200/80 bg-slate-50/80 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
                  Saída esquecida: o colaborador pede inclusão/correção em Meu ponto — sem fechamento
                  automático.
                </p>
              </FormSection>

              <div className="flex justify-end">
                <Button type="button" disabled={salvandoSettings} onClick={() => void salvarSettings()}>
                  {salvandoSettings ? 'Salvando…' : 'Salvar configurações'}
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Carregando…</p>
          )}
        </Card>
        </div>

        <Card title="Feriados da instância">
          <p className="mb-4 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            Além dos feriados nacionais (se ligados acima), cadastre datas da empresa. Com
            «repetir todos os anos», o mesmo dia/mês vale automaticamente nos anos seguintes.
          </p>
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <div className="w-[10.75rem] shrink-0">
              <Input
                label="Data"
                type="date"
                value={feriadoData}
                onChange={(e) => setFeriadoData(e.target.value)}
              />
            </div>
            <div className="min-w-[12rem] max-w-md flex-1">
              <Input
                label="Nome"
                value={feriadoNome}
                onChange={(e) => setFeriadoNome(e.target.value)}
                placeholder="Ex.: Aniversário da rede"
              />
            </div>
            <Switch
              tight
              bare
              checked={feriadoRecorrente}
              onCheckedChange={setFeriadoRecorrente}
              label="Repetir todos os anos"
              className="pb-2"
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
                  key={`${f.id}-${f.data}`}
                  className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                >
                  <span className="min-w-0">
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      {f.data.slice(8, 10)}/{f.data.slice(5, 7)}/{f.data.slice(0, 4)}
                    </span>
                    {' · '}
                    {f.nome}
                    {f.recorrente_anual ? (
                      <span className="ml-2 inline-flex rounded-full bg-sky-100 px-2 py-0.5 text-[11px] font-semibold text-sky-900 dark:bg-sky-950/50 dark:text-sky-100">
                        Todo ano
                      </span>
                    ) : null}
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
      ) : null}

      <ConfirmDialog
        open={!!decisaoSol}
        title="Rejeitar solicitação"
        message="Informe o motivo da rejeição para o colaborador."
        confirmLabel="Rejeitar"
        variant="danger"
        loading={decidindoSol}
        onConfirm={() => void confirmarRejeicaoSol()}
        onCancel={() => {
          if (decidindoSol) return
          setDecisaoSol(null)
          setDecisaoMotivo('')
        }}
      >
        <Input
          label="Motivo da rejeição"
          value={decisaoMotivo}
          onChange={(e) => setDecisaoMotivo(e.target.value)}
          placeholder="Ex.: horário divergente do combinado"
        />
      </ConfirmDialog>
      <ConfirmDialog
        open={reabrirAberto}
        title="Reabrir competência"
        message="O mês volta a aceitar ajustes normais. Informe o motivo para auditoria."
        confirmLabel="Reabrir"
        loading={reabrindo}
        onConfirm={() => void confirmarReabrirCompetencia()}
        onCancel={() => {
          if (reabrindo) return
          setReabrirAberto(false)
          setReabrirMotivo('')
        }}
      >
        <Input
          label="Motivo da reabertura"
          value={reabrirMotivo}
          onChange={(e) => setReabrirMotivo(e.target.value)}
          placeholder="Ex.: faltou incluir batida aprovada"
        />
      </ConfirmDialog>
      <PontoAjudaModal
        open={ajudaAberta}
        onClose={() => setAjudaAberta(false)}
        audiencia="admin"
      />
    </PageContainer>
  )
}
