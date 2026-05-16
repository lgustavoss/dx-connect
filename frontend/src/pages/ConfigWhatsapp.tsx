import { useCallback, useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { whatsappSettings } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'

type EstadoEvolution = {
  configurado: boolean
  state: unknown | null
  erro?: string | null
}

type Aba = 'conexao' | 'mensagens' | 'horarios'

type DiaKey = 'seg' | 'ter' | 'qua' | 'qui' | 'sex' | 'sab' | 'dom'
type HorarioDia = { ativo: boolean; inicio: string; fim: string }
type HorarioSemana = Record<DiaKey, HorarioDia>

const DIAS: Array<{ key: DiaKey; label: string }> = [
  { key: 'seg', label: 'Segunda' },
  { key: 'ter', label: 'Terça' },
  { key: 'qua', label: 'Quarta' },
  { key: 'qui', label: 'Quinta' },
  { key: 'sex', label: 'Sexta' },
  { key: 'sab', label: 'Sábado' },
  { key: 'dom', label: 'Domingo' },
]

function horarioSemanaPadrao(): HorarioSemana {
  return {
    seg: { ativo: true, inicio: '08:00', fim: '18:00' },
    ter: { ativo: true, inicio: '08:00', fim: '18:00' },
    qua: { ativo: true, inicio: '08:00', fim: '18:00' },
    qui: { ativo: true, inicio: '08:00', fim: '18:00' },
    sex: { ativo: true, inicio: '08:00', fim: '18:00' },
    sab: { ativo: false, inicio: '08:00', fim: '12:00' },
    dom: { ativo: false, inicio: '08:00', fim: '12:00' },
  }
}

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

const DEFAULT_MSG_ESPERA =
  'Olá, {{nome_cliente}}, Seja Bem-Vindo(a) a {{nome_empresa}}.\n\n✅protocolo de atendimento: *{{protocolo}}*\n\nAbertura: *{{data_abertura}}*\n'
const DEFAULT_MSG_ASSUMIDO =
  'Olá, {nome}! Sou o {atendente} atendente responsável pelo seu atendimento. Como posso ajudar?'
const DEFAULT_MSG_ENCERRADO =
  'Atendimento encerrado. Se precisar de algo mais, é só enviar uma nova mensagem por aqui.'
const DEFAULT_MSG_FORA_HORARIO =
  'Olá, {nome}! No momento estamos fora do horário de atendimento. Assim que voltarmos, responderemos por aqui.'

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

export function ConfigWhatsapp() {
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

  const [msgEsperaAtiva, setMsgEsperaAtiva] = useState(true)
  const [msgEsperaTexto, setMsgEsperaTexto] = useState(DEFAULT_MSG_ESPERA)
  const [msgAssumidoAtiva, setMsgAssumidoAtiva] = useState(true)
  const [msgAssumidoTexto, setMsgAssumidoTexto] = useState(DEFAULT_MSG_ASSUMIDO)
  const [msgEncerradoAtiva, setMsgEncerradoAtiva] = useState(true)
  const [msgEncerradoTexto, setMsgEncerradoTexto] = useState(DEFAULT_MSG_ENCERRADO)
  const [msgForaHorarioAtiva, setMsgForaHorarioAtiva] = useState(true)
  const [msgForaHorarioTexto, setMsgForaHorarioTexto] = useState(DEFAULT_MSG_FORA_HORARIO)
  const [nomeEmpresaExibicao, setNomeEmpresaExibicao] = useState('DX Connect')
  const [horarioTimezone, setHorarioTimezone] = useState<string>('America/Sao_Paulo')
  const [usarFeriadosNacionais, setUsarFeriadosNacionais] = useState(false)
  const [horarioSemana, setHorarioSemana] = useState<HorarioSemana>(horarioSemanaPadrao())
  const [salvandoHorarios, setSalvandoHorarios] = useState(false)

  const carregar = useCallback(async () => {
    setLoading(true)
    try {
      const r = await whatsappSettings.get()
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
      setHorarioTimezone((r.horario_timezone ?? 'America/Sao_Paulo').trim() || 'America/Sao_Paulo')
      setNomeEmpresaExibicao((String((r as any).nome_empresa_exibicao ?? 'DX Connect')).trim() || 'DX Connect')
      setUsarFeriadosNacionais(Boolean((r as any).usar_feriados_nacionais))
      const hs = (r as any).horario_semana as Record<string, any> | null | undefined
      if (hs && typeof hs === 'object') {
        const base = horarioSemanaPadrao()
        for (const d of DIAS) {
          const c = hs[d.key]
          if (c && typeof c === 'object') {
            base[d.key] = {
              ativo: Boolean(c.ativo ?? base[d.key].ativo),
              inicio: String(c.inicio ?? base[d.key].inicio),
              fim: String(c.fim ?? base[d.key].fim),
            }
          }
        }
        setHorarioSemana(base)
      } else {
        setHorarioSemana(horarioSemanaPadrao())
      }
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
    if (!confirm('Apagar a instância na Evolution e limpar credenciais no DX Connect?')) return
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

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <Card title="WhatsApp (Evolution)">
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          Conecte um número via QR Code e configure mensagens automáticas para padronizar a experiência do cliente.
        </p>

        <div className="mt-5 border-b border-slate-200 dark:border-slate-700/80">
          <nav className="flex gap-1 sm:gap-2" aria-label="Seções do WhatsApp">
            <button
              type="button"
              onClick={() => setAba('conexao')}
              aria-current={aba === 'conexao' ? 'page' : undefined}
              className={
                aba === 'conexao'
                  ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                  : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800/30 dark:hover:text-slate-200'
              }
            >
              Conexão
            </button>
            <button
              type="button"
              onClick={() => setAba('mensagens')}
              aria-current={aba === 'mensagens' ? 'page' : undefined}
              className={
                aba === 'mensagens'
                  ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                  : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800/30 dark:hover:bg-slate-800/30 dark:hover:text-slate-200'
              }
            >
              Mensagens automáticas
            </button>
            <button
              type="button"
              onClick={() => setAba('horarios')}
              aria-current={aba === 'horarios' ? 'page' : undefined}
              className={
                aba === 'horarios'
                  ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                  : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800/30 dark:hover:text-slate-200'
              }
            >
              Horários
            </button>
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

                <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-200">
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
              <div className="rounded-lg border border-slate-200 p-4 text-sm text-slate-600 dark:border-slate-700/80 dark:text-slate-400">
                <p className="font-medium text-slate-800 dark:text-slate-200">Pareamento por QR não disponível</p>
                <p className="mt-2 leading-relaxed">
                  Neste servidor a Evolution API embutida não está configurada. Suba o stack via Docker e confirme as variáveis no backend.
                </p>
              </div>
            )}
          </div>
        ) : aba === 'mensagens' ? (
          <div className="mt-6 space-y-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 text-sm text-slate-700 dark:border-slate-700/80 dark:bg-slate-800/20 dark:text-slate-200">
              <p className="font-medium">Como funciona</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                As mensagens abaixo são enviadas automaticamente em eventos do chat. Variáveis disponíveis: <span className="font-mono">{'{nome}'}</span>,{' '}
                <span className="font-mono">{'{atendente}'}</span>, <span className="font-mono">{'{protocolo}'}</span>,{' '}
                <span className="font-mono">{'{telefone}'}</span>.
              </p>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700/80 dark:bg-slate-900/30">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Identidade</p>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                Usado em templates como <span className="font-mono">{'{{nome_empresa}}'}</span>.
              </p>
              <input
                type="text"
                value={nomeEmpresaExibicao}
                onChange={(e) => setNomeEmpresaExibicao(e.target.value)}
                placeholder="Ex.: DX Connect"
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
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
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
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            />

            <Switch
              checked={msgEncerradoAtiva}
              onCheckedChange={setMsgEncerradoAtiva}
              label="Mensagem quando o chat é encerrado"
              description="Enviada automaticamente quando o atendente encerra o chat."
              showStatusPill
              statusOnText="Enviar"
              statusOffText="Não enviar"
            />
            <textarea
              value={msgEncerradoTexto}
              onChange={(e) => setMsgEncerradoTexto(e.target.value)}
              rows={4}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
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
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
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
        ) : (
          <div className="mt-6 space-y-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 text-sm text-slate-700 dark:border-slate-700/80 dark:bg-slate-800/20 dark:text-slate-200">
              <p className="font-medium">Horário de funcionamento</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Define quando o atendimento está aberto em cada dia da semana. Fora desse período, a mensagem “fora do horário” pode ser enviada.
              </p>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700/80 dark:bg-slate-900/30">
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

            <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700/80">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50/70 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800/30 dark:text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Dia</th>
                    <th className="px-4 py-3">Aberto</th>
                    <th className="px-4 py-3">Início</th>
                    <th className="px-4 py-3">Fim</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {DIAS.map((d) => (
                    <tr key={d.key} className="bg-white/40 dark:bg-slate-900/20">
                      <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-100">{d.label}</td>
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={horarioSemana[d.key].ativo}
                          onChange={(e) =>
                            setHorarioSemana((prev) => ({ ...prev, [d.key]: { ...prev[d.key], ativo: e.target.checked } }))
                          }
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="time"
                          value={horarioSemana[d.key].inicio}
                          disabled={!horarioSemana[d.key].ativo}
                          onChange={(e) =>
                            setHorarioSemana((prev) => ({ ...prev, [d.key]: { ...prev[d.key], inicio: e.target.value } }))
                          }
                          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 disabled:opacity-50"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="time"
                          value={horarioSemana[d.key].fim}
                          disabled={!horarioSemana[d.key].ativo}
                          onChange={(e) =>
                            setHorarioSemana((prev) => ({ ...prev, [d.key]: { ...prev[d.key], fim: e.target.value } }))
                          }
                          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 disabled:opacity-50"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end pt-2">
              <Button
                type="button"
                loading={salvandoHorarios}
                onClick={() => {
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
    </div>
  )
}
