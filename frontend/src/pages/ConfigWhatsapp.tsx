import { useCallback, useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { systemSettings, whatsappSettings } from '../api/client'
import { HorarioSemanaEditor } from '../components/horario/HorarioSemanaEditor'
import { Card } from '../components/ui/Card'
import { PageContainer } from '../components/ui/PageContainer'
import { Button } from '../components/ui/Button'
import { Switch } from '../components/ui/Switch'
import { TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { useToast } from '../components/ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import {
  horarioSemanaFromApi,
  horarioSemanaPadrao,
  validarHorarioSemana,
  type HorarioSemana,
} from '../lib/horarioSemana'

type EstadoEvolution = {
  configurado: boolean
  state: unknown | null
  erro?: string | null
}

type Aba = 'conexao' | 'mensagens' | 'inatividade' | 'avaliacao' | 'horarios'

const ABAS: Array<{ id: Aba; label: string }> = [
  { id: 'conexao', label: 'Conexão' },
  { id: 'mensagens', label: 'Mensagens automáticas' },
  { id: 'inatividade', label: 'Inatividade' },
  { id: 'avaliacao', label: 'Avaliação' },
  { id: 'horarios', label: 'Horários' },
]

function extrairEstadoConexao(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') return null
  const p = payload as Record<string, unknown>
  const st = p.state
  if (!st || typeof st !== 'object') return null
  const inst = (st as Record<string, unknown>).instance
  if (!inst || typeof inst !== 'object') return null
  const state = (inst as Record<string, unknown>).state
  return typeof state === 'string' ? state : null
}

function rotuloEstadoConexao(estadoRaw: string | null): {
  label: string
  tone: 'ok' | 'warn' | 'muted'
} {
  const s = (estadoRaw || '').trim().toLowerCase()
  if (!s) return { label: '—', tone: 'muted' }
  if (s === 'open' || s === 'opened' || s === 'connected') return { label: 'Conectado', tone: 'ok' }
  if (s === 'connecting' || s === 'qr' || s === 'qrcode') return { label: 'Aguardando pareamento', tone: 'warn' }
  if (s === 'close' || s === 'closed' || s === 'disconnected') return { label: 'Desconectado', tone: 'warn' }
  return { label: `Em processamento (${s})`, tone: 'warn' }
}

function nomeEmpresaSistemaPadrao(emp: {
  nome_fantasia?: string | null
  razao_social?: string | null
  nome?: string | null
} | null | undefined): string {
  if (!emp) return ''
  return (
    (emp.nome_fantasia ?? '').trim() ||
    (emp.razao_social ?? '').trim() ||
    (emp.nome ?? '').trim()
  )
}

const DEFAULT_MSG_ESPERA =
  'Olá, {{nome_cliente}}, Seja Bem-Vindo(a) a {{nome_empresa}}.\n\n✅protocolo de atendimento: *{{protocolo}}*\n\nAbertura: *{{data_abertura}}*\n'
const DEFAULT_MSG_ASSUMIDO =
  'Olá, {nome}! Sou o {atendente} atendente responsável pelo seu atendimento. Como posso ajudar?'
const DEFAULT_MSG_ENCERRADO =
  'Atendimento encerrado. Se precisar de algo mais, é só enviar uma nova mensagem por aqui.'
const DEFAULT_MSG_FORA_HORARIO =
  'Olá, {nome}! No momento estamos fora do horário de atendimento. Assim que voltarmos, responderemos por aqui.'
const DEFAULT_MSG_INATIV_AVISO =
  'Olá, {{nome_cliente}}! Você está há um tempo sem responder. Se não houver retorno, encerraremos este atendimento em breve. Responda aqui se ainda precisar de ajuda.'
const DEFAULT_MSG_AVALIACAO =
  'Como você avalia o atendimento?\n\nResponda com uma nota de *1* a *5*:\n1 — Péssimo\n2 — Ruim\n3 — Regular\n4 — Bom\n5 — Excelente'
const DEFAULT_MSG_AVALIACAO_OBRIGADO = 'Obrigado pela sua avaliação! Atendimento encerrado.'

function renderQrPayload(data: Record<string, unknown> | null | undefined) {
  if (!data || typeof data !== 'object') return null
  const code = data.code
  if (typeof code === 'string' && code.length > 0) {
    return (
      <div className="flex justify-center rounded-lg bg-white p-4">
        <QRCodeSVG value={code} size={280} level="M" />
      </div>
    )
  }
  const raw = data.base64 ?? data.qrcode
  if (typeof raw === 'string') {
    if (raw.startsWith('data:image')) {
      return <img src={raw} alt="QR Code WhatsApp" className="mx-auto max-w-[280px] rounded-lg" />
    }
    if (raw.length > 80) {
      return (
        <img
          src={`data:image/png;base64,${raw}`}
          alt="QR Code WhatsApp"
          className="mx-auto max-w-[280px] rounded-lg"
        />
      )
    }
  }
  const pairing = data.pairingCode
  if (typeof pairing === 'string' && pairing.length > 0) {
    return (
      <p className="text-center font-mono text-lg tracking-widest text-slate-800 dark:text-slate-100">
        Código de pareamento: <span className="font-bold">{pairing}</span>
      </p>
    )
  }
  return (
    <pre className="max-h-56 overflow-auto rounded bg-slate-100 p-3 text-xs text-slate-800 dark:bg-slate-900 dark:text-slate-200">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

export function ConfigWhatsapp({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [aba, setAba] = useState<Aba>('conexao')
  const [flags, setFlags] = useState({
    evolution_embutida_disponivel: false,
  })
  const [estado, setEstado] = useState<EstadoEvolution | null>(null)
  const [qrPayload, setQrPayload] = useState<Record<string, unknown> | null>(null)
  const [provisionando, setProvisionando] = useState(false)
  const [salvandoMsgs, setSalvandoMsgs] = useState(false)
  const [salvandoInatividade, setSalvandoInatividade] = useState(false)
  const [salvandoAvaliacao, setSalvandoAvaliacao] = useState(false)

  const [msgEsperaAtiva, setMsgEsperaAtiva] = useState(true)
  const [msgEsperaTexto, setMsgEsperaTexto] = useState(DEFAULT_MSG_ESPERA)
  const [msgAssumidoAtiva, setMsgAssumidoAtiva] = useState(true)
  const [msgAssumidoTexto, setMsgAssumidoTexto] = useState(DEFAULT_MSG_ASSUMIDO)
  const [msgEncerradoAtiva, setMsgEncerradoAtiva] = useState(true)
  const [msgEncerradoTexto, setMsgEncerradoTexto] = useState(DEFAULT_MSG_ENCERRADO)
  const [msgForaHorarioAtiva, setMsgForaHorarioAtiva] = useState(true)
  const [msgForaHorarioTexto, setMsgForaHorarioTexto] = useState(DEFAULT_MSG_FORA_HORARIO)
  const [inativEncerramentoAtiva, setInativEncerramentoAtiva] = useState(false)
  const [inativAvisoMinutos, setInativAvisoMinutos] = useState('15')
  const [inativEncerramentoAposAvisoMinutos, setInativEncerramentoAposAvisoMinutos] = useState('5')
  const [msgInativAvisoAtiva, setMsgInativAvisoAtiva] = useState(true)
  const [msgInativAvisoTexto, setMsgInativAvisoTexto] = useState(DEFAULT_MSG_INATIV_AVISO)
  const [avaliacaoAtiva, setAvaliacaoAtiva] = useState(false)
  const [msgAvaliacaoAtiva, setMsgAvaliacaoAtiva] = useState(true)
  const [msgAvaliacaoTexto, setMsgAvaliacaoTexto] = useState(DEFAULT_MSG_AVALIACAO)
  const [msgAvaliacaoObrigadoTexto, setMsgAvaliacaoObrigadoTexto] = useState(DEFAULT_MSG_AVALIACAO_OBRIGADO)
  const [nomeEmpresaExibicao, setNomeEmpresaExibicao] = useState('')
  const [horarioTimezone, setHorarioTimezone] = useState<string>('America/Sao_Paulo')
  const [usarFeriadosNacionais, setUsarFeriadosNacionais] = useState(false)
  const [horarioSemana, setHorarioSemana] = useState<HorarioSemana>(horarioSemanaPadrao())
  const [salvandoHorarios, setSalvandoHorarios] = useState(false)

  const carregar = useCallback(async () => {
    setLoading(true)
    try {
      const [r, emp] = await Promise.all([whatsappSettings.get(), systemSettings.getEmpresaSistema()])
      setFlags({
        evolution_embutida_disponivel: Boolean(r.evolution_embutida_disponivel),
      })
      setMsgEsperaAtiva(Boolean(r.auto_msg_espera_ativa))
      setMsgEsperaTexto((r.auto_msg_espera_texto ?? DEFAULT_MSG_ESPERA).trim() || DEFAULT_MSG_ESPERA)
      setMsgAssumidoAtiva(Boolean(r.auto_msg_assumido_ativa))
      setMsgAssumidoTexto((r.auto_msg_assumido_texto ?? DEFAULT_MSG_ASSUMIDO).trim() || DEFAULT_MSG_ASSUMIDO)
      setMsgEncerradoAtiva(Boolean(r.auto_msg_encerrado_ativa))
      setMsgEncerradoTexto((r.auto_msg_encerrado_texto ?? DEFAULT_MSG_ENCERRADO).trim() || DEFAULT_MSG_ENCERRADO)
      setMsgForaHorarioAtiva(Boolean(r.auto_msg_fora_horario_ativa))
      setMsgForaHorarioTexto(
        (r.auto_msg_fora_horario_texto ?? DEFAULT_MSG_FORA_HORARIO).trim() || DEFAULT_MSG_FORA_HORARIO,
      )
      setInativEncerramentoAtiva(Boolean(r.inativ_encerramento_ativa))
      setInativAvisoMinutos(String(r.inativ_aviso_minutos ?? 15))
      setInativEncerramentoAposAvisoMinutos(String(r.inativ_encerramento_apos_aviso_minutos ?? 5))
      setMsgInativAvisoAtiva(Boolean(r.auto_msg_inativ_aviso_ativa ?? true))
      setMsgInativAvisoTexto(
        (r.auto_msg_inativ_aviso_texto ?? DEFAULT_MSG_INATIV_AVISO).trim() || DEFAULT_MSG_INATIV_AVISO,
      )
      setAvaliacaoAtiva(Boolean(r.avaliacao_ativa))
      setMsgAvaliacaoAtiva(Boolean(r.auto_msg_avaliacao_ativa ?? true))
      setMsgAvaliacaoTexto((r.auto_msg_avaliacao_texto ?? DEFAULT_MSG_AVALIACAO).trim() || DEFAULT_MSG_AVALIACAO)
      setMsgAvaliacaoObrigadoTexto(
        (r.auto_msg_avaliacao_obrigado_texto ?? DEFAULT_MSG_AVALIACAO_OBRIGADO).trim() ||
          DEFAULT_MSG_AVALIACAO_OBRIGADO,
      )
      setHorarioTimezone((r.horario_timezone ?? 'America/Sao_Paulo').trim() || 'America/Sao_Paulo')
      const identidadeSalva = (r.nome_empresa_exibicao ?? '').trim()
      setNomeEmpresaExibicao(identidadeSalva || nomeEmpresaSistemaPadrao(emp))
      setUsarFeriadosNacionais(Boolean(r.usar_feriados_nacionais))
      setHorarioSemana(horarioSemanaFromApi(r.horario_semana ?? undefined))
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as configurações.'))
    } finally {
      setLoading(false)
    }
  }, [toast])

  const carregarEstado = useCallback(async () => {
    try {
      const r = (await whatsappSettings.estadoEmbutido()) as EstadoEvolution
      setEstado(r)
    } catch (err) {
      setEstado({ configurado: true, state: null, erro: mensagemFalhaParaToast(err) })
    }
  }, [])

  useEffect(() => {
    void carregar()
    void carregarEstado()
  }, [carregar])

  async function prepararEMostrarQr() {
    setProvisionando(true)
    try {
      const out = await whatsappSettings.provisionarEmbutido()
      const q = out.qrcode && typeof out.qrcode === 'object' ? (out.qrcode as Record<string, unknown>) : null
      setQrPayload(q)
      if (out.connect_erro) {
        toast.showWarning(`Provisionado; ao obter QR: ${out.connect_erro}. Use «Atualizar QR».`)
      } else {
        toast.showSuccess('Instância criada. Escaneie o QR Code com o WhatsApp no telemóvel.')
      }
      await carregar()
      await carregarEstado()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao preparar a Evolution.'))
    } finally {
      setProvisionando(false)
    }
  }

  async function atualizarQr() {
    try {
      const q = await whatsappSettings.qrCode()
      setQrPayload(q)
      toast.showSuccess('QR atualizado.')
      await carregarEstado()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err))
    }
  }

  async function reporTudo() {
    if (!confirm('Apagar a instância na Evolution e limpar credenciais no DeskRudder?')) return
    try {
      await whatsappSettings.reporEmbutido()
      setQrPayload(null)
      setEstado(null)
      toast.showSuccess('Pode voltar a preparar a ligação.')
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err))
    }
  }

  useEffect(() => {
    // Enquanto o QR estiver visível, reconsulta o estado de conexão para refletir “open/connecting/close”.
    if (!qrPayload) return
    let cancelled = false
    const t = window.setInterval(() => {
      if (cancelled) return
      void carregarEstado()
    }, 3000)
    return () => {
      cancelled = true
      window.clearInterval(t)
    }
  }, [qrPayload, carregarEstado])

  if (loading) {
    return <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
  }

  const estadoStr = extrairEstadoConexao(estado)
  const estadoUi = rotuloEstadoConexao(estadoStr)
  const conectado = estadoUi.tone === 'ok'

  const conteudo = (
    <Card title={embedded ? undefined : 'WhatsApp (Evolution)'}>
      {!embedded ? (
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          Conecte um número via QR Code e configure mensagens, inatividade, avaliação e horários de atendimento.
        </p>
      ) : null}

      <div className={embedded ? 'border-b border-slate-200 dark:border-slate-800/80' : 'mt-5 border-b border-slate-200 dark:border-slate-800/80'}>
          <nav className="-mb-px flex gap-1 overflow-x-auto sm:gap-2" aria-label="Seções do WhatsApp">
            {ABAS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setAba(id)}
                aria-current={aba === id ? 'page' : undefined}
                className={
                  aba === id
                    ? 'shrink-0 border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                    : 'shrink-0 border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
                }
              >
                {label}
              </button>
            ))}
          </nav>
        </div>

        {aba === 'conexao' ? (
          <div className="mt-6 space-y-5">
            {flags.evolution_embutida_disponivel ? (
              <>
                <div>
                  <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Conectar WhatsApp</h2>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                    No telemóvel: WhatsApp → Aparelhos ligados → Ligar um aparelho → leia o QR.
                  </p>
                </div>

                <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-900/40 dark:text-slate-200">
                  <p className="font-medium">
                    Status da conexão:{' '}
                    <span
                      className={
                        estadoUi.tone === 'ok'
                          ? 'text-emerald-700 dark:text-emerald-300'
                          : estadoUi.tone === 'warn'
                            ? 'text-amber-700 dark:text-amber-300'
                            : 'text-slate-600 dark:text-slate-300'
                      }
                    >
                      {estadoUi.label}
                    </span>
                  </p>
                  {conectado ? (
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                      Conectado. Para validar, envie uma mensagem para o número e verifique em <span className="font-medium">Chat</span>.
                    </p>
                  ) : (
                    qrPayload && (
                      <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                        Depois de ler o QR, pode levar alguns instantes para finalizar a sincronização. O status atualiza automaticamente.
                      </p>
                    )
                  )}
                  {estado?.erro && <p className="mt-1 text-xs text-rose-700 dark:text-rose-300">{estado.erro}</p>}
                  <div className="mt-3">
                    <Button type="button" variant="secondary" onClick={() => void carregarEstado()}>
                      Recarregar status
                    </Button>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 pt-1">
                  <Button type="button" loading={provisionando} onClick={() => void prepararEMostrarQr()}>
                    Gerar QR Code para conectar
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => void atualizarQr()}>
                    Gerar novo QR Code
                  </Button>
                  <Button type="button" variant="danger" onClick={() => void reporTudo()}>
                    Desconectar e reiniciar
                  </Button>
                </div>

                {qrPayload && <div className="pt-1">{renderQrPayload(qrPayload)}</div>}
              </>
            ) : (
              <div className="rounded-lg border border-slate-200 p-4 text-sm text-slate-600 dark:border-slate-800/80 dark:text-slate-400">
                <p className="font-medium text-slate-800 dark:text-slate-200">Pareamento por QR não disponível</p>
                <p className="mt-2 leading-relaxed">
                  Neste servidor a Evolution API embutida não está configurada. Suba o stack via Docker e confirme as variáveis no backend.
                </p>
              </div>
            )}
          </div>
        ) : aba === 'mensagens' ? (
          <div className="mt-6 space-y-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 text-sm text-slate-700 dark:border-slate-800/80 dark:bg-slate-800/20 dark:text-slate-200">
              <p className="font-medium">Como funciona</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                As mensagens abaixo são enviadas automaticamente em eventos do chat. Variáveis:{' '}
                <span className="font-mono">{'{{nome_cliente}}'}</span>,{' '}
                <span className="font-mono">{'{{nome_empresa}}'}</span>,{' '}
                <span className="font-mono">{'{{protocolo}}'}</span>,{' '}
                <span className="font-mono">{'{{data_abertura}}'}</span>,{' '}
                <span className="font-mono">{'{nome}'}</span>,{' '}
                <span className="font-mono">{'{atendente}'}</span>,{' '}
                <span className="font-mono">{'{telefone}'}</span>.
              </p>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800/80 dark:bg-slate-900/30">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Identidade</p>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                Usado em templates como <span className="font-mono">{'{{nome_empresa}}'}</span>. Se vazio ao salvar,
                usa o nome fantasia de Configurações → Sistema → Empresa.
              </p>
              <input
                type="text"
                value={nomeEmpresaExibicao}
                onChange={(e) => setNomeEmpresaExibicao(e.target.value)}
                placeholder="Ex.: nome fantasia da empresa"
                className="mt-3 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              />
            </div>

            <Switch
              checked={msgEsperaAtiva}
              onCheckedChange={setMsgEsperaAtiva}
              label="Mensagem quando o cliente entra na fila"
              description="Enviada na primeira mensagem do cliente, quando o chat é criado e fica em espera."
              showStatusPill
              statusOnText="Enviar"
              statusOffText="Não enviar"
            />
            <textarea
              value={msgEsperaTexto}
              onChange={(e) => setMsgEsperaTexto(e.target.value)}
              rows={4}
              className={TEXTAREA_FIELD_CLASS}
            />

            <Switch
              checked={msgAssumidoAtiva}
              onCheckedChange={setMsgAssumidoAtiva}
              label="Mensagem quando o atendente assume o chat"
              description="Enviada automaticamente quando o chat sai da fila e entra em atendimento."
              showStatusPill
              statusOnText="Enviar"
              statusOffText="Não enviar"
            />
            <textarea
              value={msgAssumidoTexto}
              onChange={(e) => setMsgAssumidoTexto(e.target.value)}
              rows={4}
              className={TEXTAREA_FIELD_CLASS}
            />

            <Switch
              checked={msgEncerradoAtiva}
              onCheckedChange={setMsgEncerradoAtiva}
              label="Mensagem quando o chat é encerrado"
              description="Enviada ao finalizar o atendimento quando a avaliação (aba Avaliação) estiver desativada."
              showStatusPill
              statusOnText="Enviar"
              statusOffText="Não enviar"
            />
            <textarea
              value={msgEncerradoTexto}
              onChange={(e) => setMsgEncerradoTexto(e.target.value)}
              rows={4}
              className={TEXTAREA_FIELD_CLASS}
            />

            <Switch
              checked={msgForaHorarioAtiva}
              onCheckedChange={setMsgForaHorarioAtiva}
              label="Mensagem quando estiver fora do horário"
              description="Enviada quando o cliente manda mensagem fora do horário configurado (uma vez por chat)."
              showStatusPill
              statusOnText="Enviar"
              statusOffText="Não enviar"
            />
            <textarea
              value={msgForaHorarioTexto}
              onChange={(e) => setMsgForaHorarioTexto(e.target.value)}
              rows={4}
              className={TEXTAREA_FIELD_CLASS}
            />

            <div className="flex justify-end pt-2">
              <Button
                type="button"
                loading={salvandoMsgs}
                onClick={() => {
                  setSalvandoMsgs(true)
                  whatsappSettings
                    .patch({
                      nome_empresa_exibicao: nomeEmpresaExibicao,
                      auto_msg_espera_ativa: msgEsperaAtiva,
                      auto_msg_espera_texto: msgEsperaTexto,
                      auto_msg_assumido_ativa: msgAssumidoAtiva,
                      auto_msg_assumido_texto: msgAssumidoTexto,
                      auto_msg_encerrado_ativa: msgEncerradoAtiva,
                      auto_msg_encerrado_texto: msgEncerradoTexto,
                      auto_msg_fora_horario_ativa: msgForaHorarioAtiva,
                      auto_msg_fora_horario_texto: msgForaHorarioTexto,
                    })
                    .then(() => toast.showSuccess('Mensagens automáticas atualizadas.'))
                    .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.')))
                    .finally(() => setSalvandoMsgs(false))
                }}
              >
                Salvar mensagens
              </Button>
            </div>
          </div>
        ) : aba === 'inatividade' ? (
          <div className="mt-6 space-y-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 text-sm text-slate-700 dark:border-slate-800/80 dark:bg-slate-800/20 dark:text-slate-200">
              <p className="font-medium">Encerramento por inatividade</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Encerra chats em atendimento após silêncio. O tempo conta desde a última mensagem (cliente ou
                atendente). No chat, o responsável pode Pausar o timer durante análises longas — ao pausar/retomar o
                prazo volta ao valor configurado. Enviar mensagem (ou o cliente falar) sai automaticamente da pausa.
              </p>
            </div>

            <Switch
              checked={inativEncerramentoAtiva}
              onCheckedChange={setInativEncerramentoAtiva}
              label="Encerramento automático por inatividade do cliente"
              description="Qualquer mensagem (cliente ou atendente) reinicia o timer e sai da pausa. Use Pausar no chat se precisar de mais tempo em silêncio."
              showStatusPill
              statusOnText="Ativo"
              statusOffText="Inativo"
            />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  Minutos sem resposta para enviar o aviso
                </label>
                <input
                  type="number"
                  min={1}
                  max={1440}
                  disabled={!inativEncerramentoAtiva}
                  value={inativAvisoMinutos}
                  onChange={(e) => setInativAvisoMinutos(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  Minutos após o aviso para encerrar o chat
                </label>
                <input
                  type="number"
                  min={1}
                  max={1440}
                  disabled={!inativEncerramentoAtiva}
                  value={inativEncerramentoAposAvisoMinutos}
                  onChange={(e) => setInativEncerramentoAposAvisoMinutos(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
                />
              </div>
            </div>
            <Switch
              checked={msgInativAvisoAtiva}
              onCheckedChange={setMsgInativAvisoAtiva}
              label="Mensagem de aviso antes do encerramento"
              description="Enviada ao cliente quando o tempo de inatividade é atingido."
              showStatusPill
              statusOnText="Enviar"
              statusOffText="Encerrar direto"
            />
            <textarea
              value={msgInativAvisoTexto}
              onChange={(e) => setMsgInativAvisoTexto(e.target.value)}
              rows={4}
              disabled={!inativEncerramentoAtiva || !msgInativAvisoAtiva}
              className={`${TEXTAREA_FIELD_CLASS} disabled:opacity-50`}
            />

            <div className="flex justify-end pt-2">
              <Button
                type="button"
                loading={salvandoInatividade}
                onClick={() => {
                  const avisoMin = Number.parseInt(inativAvisoMinutos, 10)
                  const posMin = Number.parseInt(inativEncerramentoAposAvisoMinutos, 10)
                  if (
                    inativEncerramentoAtiva &&
                    (!Number.isFinite(avisoMin) || avisoMin < 1 || !Number.isFinite(posMin) || posMin < 1)
                  ) {
                    toast.showError('Informe minutos válidos para aviso e encerramento após o aviso.')
                    return
                  }
                  setSalvandoInatividade(true)
                  whatsappSettings
                    .patch({
                      inativ_encerramento_ativa: inativEncerramentoAtiva,
                      inativ_aviso_minutos: inativEncerramentoAtiva ? avisoMin : null,
                      inativ_encerramento_apos_aviso_minutos: inativEncerramentoAtiva ? posMin : null,
                      auto_msg_inativ_aviso_ativa: msgInativAvisoAtiva,
                      auto_msg_inativ_aviso_texto: msgInativAvisoTexto,
                    })
                    .then(() => toast.showSuccess('Configurações de inatividade atualizadas.'))
                    .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.')))
                    .finally(() => setSalvandoInatividade(false))
                }}
              >
                Salvar inatividade
              </Button>
            </div>
          </div>
        ) : aba === 'avaliacao' ? (
          <div className="mt-6 space-y-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 text-sm text-slate-700 dark:border-slate-800/80 dark:bg-slate-800/20 dark:text-slate-200">
              <p className="font-medium">Avaliação do atendimento</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Ao encerrar o chat, o cliente recebe uma solicitação de nota de 1 a 5 antes do atendimento ser
                finalizado. As notas aparecem no histórico de conversas.
              </p>
            </div>

            <Switch
              checked={avaliacaoAtiva}
              onCheckedChange={setAvaliacaoAtiva}
              label="Solicitar avaliação ao encerrar (notas 1 a 5)"
              showStatusPill
              statusOnText="Ativo"
              statusOffText="Inativo"
            />
            <Switch
              checked={msgAvaliacaoAtiva}
              onCheckedChange={setMsgAvaliacaoAtiva}
              label="Enviar mensagens de avaliação"
              description="Solicitação da nota e agradecimento após a resposta."
              showStatusPill
              statusOnText="Enviar"
              statusOffText="Encerrar direto"
            />
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Mensagem solicitando a nota (1 a 5)
            </label>
            <textarea
              value={msgAvaliacaoTexto}
              onChange={(e) => setMsgAvaliacaoTexto(e.target.value)}
              rows={4}
              disabled={!avaliacaoAtiva || !msgAvaliacaoAtiva}
              className={`${TEXTAREA_FIELD_CLASS} disabled:opacity-50`}
            />
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Mensagem de agradecimento após a nota
            </label>
            <textarea
              value={msgAvaliacaoObrigadoTexto}
              onChange={(e) => setMsgAvaliacaoObrigadoTexto(e.target.value)}
              rows={2}
              disabled={!avaliacaoAtiva || !msgAvaliacaoAtiva}
              className={`${TEXTAREA_FIELD_CLASS} disabled:opacity-50`}
            />

            <div className="flex justify-end pt-2">
              <Button
                type="button"
                loading={salvandoAvaliacao}
                onClick={() => {
                  setSalvandoAvaliacao(true)
                  whatsappSettings
                    .patch({
                      avaliacao_ativa: avaliacaoAtiva,
                      auto_msg_avaliacao_ativa: msgAvaliacaoAtiva,
                      auto_msg_avaliacao_texto: msgAvaliacaoTexto,
                      auto_msg_avaliacao_obrigado_texto: msgAvaliacaoObrigadoTexto,
                    })
                    .then(() => toast.showSuccess('Configurações de avaliação atualizadas.'))
                    .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.')))
                    .finally(() => setSalvandoAvaliacao(false))
                }}
              >
                Salvar avaliação
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-6 space-y-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 text-sm text-slate-700 dark:border-slate-800/80 dark:bg-slate-800/20 dark:text-slate-200">
              <p className="font-medium">Horário de funcionamento</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Define quando o atendimento está aberto em cada dia da semana. Fora desse período, a mensagem “fora do horário” pode ser enviada.
              </p>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800/80 dark:bg-slate-900/30">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="sm:col-span-1">
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Fuso horário</label>
                  <input
                    type="text"
                    value={horarioTimezone}
                    onChange={(e) => setHorarioTimezone(e.target.value)}
                    placeholder="America/Sao_Paulo"
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
                  />
                </div>
                <div className="sm:col-span-2">
                  <Switch
                    checked={usarFeriadosNacionais}
                    onCheckedChange={setUsarFeriadosNacionais}
                    label="Considerar feriados nacionais"
                    description="Quando ativado, feriados nacionais são tratados como fechado o dia todo."
                    showStatusPill
                    statusOnText="Ativo"
                    statusOffText="Inativo"
                  />
                </div>
              </div>
            </div>

            <HorarioSemanaEditor value={horarioSemana} onChange={setHorarioSemana} />

            <div className="flex justify-end pt-2">
              <Button
                type="button"
                loading={salvandoHorarios}
                onClick={() => {
                  const erroHorario = validarHorarioSemana(horarioSemana)
                  if (erroHorario) {
                    toast.showError(erroHorario)
                    return
                  }
                  setSalvandoHorarios(true)
                  whatsappSettings
                    .patch({
                      horario_timezone: horarioTimezone,
                      horario_semana: horarioSemana,
                      usar_feriados_nacionais: usarFeriadosNacionais,
                    })
                    .then(() => toast.showSuccess('Horários atualizados.'))
                    .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.')))
                    .finally(() => setSalvandoHorarios(false))
                }}
              >
                Salvar horários
              </Button>
            </div>
          </div>
        )}
      </Card>
  )

  return embedded ? conteudo : <PageContainer>{conteudo}</PageContainer>
}
