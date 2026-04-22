import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  empresas,
  setores,
  atendentes,
  tickets,
  whatsappChats,
  fetchWhatsAppMidiaBlob,
  type Empresas,
  type Setores,
  type Atendentes,
  type WhatsappChats,
} from '../../api/client'
import { coletarTodasPaginas } from '../../api/collectPages'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useAuth } from '../../contexts/AuthContext'

const ROTULO_SEM_LEGENDA = /^\[(Imagem|Áudio|Vídeo|Documento|Figurinha)\]$/

function ConteudoMensagemWhatsApp({ chatId, m }: { chatId: number; m: WhatsappChats.Mensagem }) {
  const tipo = (m.tipo_midia || 'texto').toLowerCase()
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(false)

  useEffect(() => {
    if (!m.midia_disponivel || tipo === 'texto') {
      setUrl(null)
      return
    }
    let objectUrl: string | null = null
    let cancelled = false
    setUrl(null)
    setLoading(true)
    setErr(false)
    fetchWhatsAppMidiaBlob(chatId, m.id)
      .then((blob) => {
        if (cancelled) return
        const u = URL.createObjectURL(blob)
        if (cancelled) {
          URL.revokeObjectURL(u)
          return
        }
        objectUrl = u
        setUrl(u)
      })
      .catch(() => {
        if (!cancelled) setErr(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [chatId, m.id, m.midia_disponivel, tipo])

  const legenda =
    m.corpo && !ROTULO_SEM_LEGENDA.test(m.corpo.trim()) ? m.corpo : null

  if (tipo === 'texto' || !m.tipo_midia) {
    return <p className="whitespace-pre-wrap">{m.corpo}</p>
  }

  if (!m.midia_disponivel) {
    return (
      <div>
        <p className="whitespace-pre-wrap text-amber-800 dark:text-amber-200/90">{m.corpo}</p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Pré-visualização indisponível (ficheiro não obtido da Evolution ou limite de tamanho).
        </p>
      </div>
    )
  }

  if (err) {
    return <p className="whitespace-pre-wrap text-amber-800 dark:text-amber-200/90">{m.corpo}</p>
  }

  if (loading || !url) {
    return <p className="text-xs text-slate-500 dark:text-slate-400">A carregar mídia…</p>
  }

  if (tipo === 'imagem' || tipo === 'figurinha') {
    return (
      <div className="space-y-1">
        <img
          src={url}
          alt=""
          className="max-h-80 max-w-full rounded-md border border-slate-200 dark:border-slate-600"
        />
        {legenda && <p className="text-xs text-slate-600 dark:text-slate-300">{legenda}</p>}
      </div>
    )
  }

  if (tipo === 'audio') {
    return (
      <div className="space-y-1">
        <audio controls src={url} className="w-full max-w-sm" />
        {legenda && <p className="text-xs text-slate-600 dark:text-slate-300">{legenda}</p>}
      </div>
    )
  }

  if (tipo === 'video') {
    return (
      <div className="space-y-1">
        <video controls src={url} className="max-h-64 max-w-full rounded-md" />
        {legenda && <p className="text-xs text-slate-600 dark:text-slate-300">{legenda}</p>}
      </div>
    )
  }

  if (tipo === 'documento') {
    return (
      <div className="space-y-1">
        <a
          href={url}
          download={`documento-${m.id}`}
          className="inline-flex font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400"
        >
          Descarregar documento
        </a>
        {legenda && <p className="text-xs text-slate-600 dark:text-slate-300">{legenda}</p>}
      </div>
    )
  }

  return <p className="whitespace-pre-wrap">{m.corpo}</p>
}

export function WhatsappConversa() {
  const { chatId } = useParams<{ chatId: string }>()
  const id = Number(chatId)
  const toast = useToast()
  const { user } = useAuth()

  const [chat, setChat] = useState<WhatsappChats.Chat | null>(null)
  const [msgs, setMsgs] = useState<WhatsappChats.Mensagem[]>([])
  const [loading, setLoading] = useState(true)
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [encerrando, setEncerrando] = useState(false)
  const [assumindo, setAssumindo] = useState(false)
  const [modalTransferir, setModalTransferir] = useState(false)
  const [transferSetorId, setTransferSetorId] = useState<number | ''>('')
  const [transferAtendenteId, setTransferAtendenteId] = useState<number | ''>('')
  const [transferindo, setTransferindo] = useState(false)
  const [atendentesDestino, setAtendentesDestino] = useState<Atendentes.Atendente[]>([])
  const [erroAtendentesDestino, setErroAtendentesDestino] = useState<string | null>(null)

  const [modalVinc, setModalVinc] = useState(false)
  const [ticketVincId, setTicketVincId] = useState('')

  const [modalAbrir, setModalAbrir] = useState(false)
  const [empresasList, setEmpresasList] = useState<Empresas.EmpresaListaItem[]>([])
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [setorId, setSetorId] = useState<number | ''>('')
  const [assunto, setAssunto] = useState('')
  const [descTicket, setDescTicket] = useState('')
  const [salvandoTicket, setSalvandoTicket] = useState(false)

  const carregar = useCallback(async () => {
    if (!Number.isFinite(id) || id <= 0) return
    const c = await whatsappChats.get(id)
    const m = await whatsappChats.mensagens(id)
    setChat(c)
    setMsgs(m)
  }, [id])

  useEffect(() => {
    if (!Number.isFinite(id) || id <= 0) return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        await carregar()
        // Ao abrir o chat, marca como visto para limpar pendências de "resposta do cliente".
        // (Falha silenciosa: não deve bloquear a tela.)
        await whatsappChats.marcarVisto(id).catch(() => {})
      } catch (err) {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o chat.'))
          setChat(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, carregar])

  useEffect(() => {
    if (!chat || chat.estado === 'encerrado') return
    const t = window.setInterval(() => {
      void carregar().catch(() => {})
    }, 5000)
    return () => window.clearInterval(t)
  }, [chat, carregar])

  useEffect(() => {
    if (!modalAbrir) return
    void coletarTodasPaginas<Empresas.EmpresaListaItem>((o, l) => empresas.list({ offset: o, limit: l }))
      .then(setEmpresasList)
      .catch(() => setEmpresasList([]))
    void coletarTodasPaginas<Setores.Setor>((o, l) => setores.list({ incluir_inativos: true, offset: o, limit: l }))
      .then(setSetoresList)
      .catch(() => setSetoresList([]))
  }, [modalAbrir])

  useEffect(() => {
    if (!modalTransferir) return
    // Setores para transferência: para atendente, não usar /setores (é filtrado por permissão).
    whatsappChats
      .setoresParaTransferencia()
      .then((rows) =>
        setSetoresList(
          rows.map((s) => ({
            id: s.id,
            nome: s.nome,
            slug: '',
            ativo: true,
          })) as unknown as Setores.Setor[],
        ),
      )
      .catch(() => setSetoresList([]))
    setAtendentesDestino([])
    setErroAtendentesDestino(null)
  }, [modalTransferir])

  useEffect(() => {
    const sid = transferSetorId === '' ? null : Number(transferSetorId)
    if (!modalTransferir || !sid) return
    setAtendentesDestino([])
    setErroAtendentesDestino(null)
    atendentes
      .listPorSetor(sid, { incluir_inativos: true })
      .then((rows) => {
        setAtendentesDestino(rows)
        setErroAtendentesDestino(null)
      })
      .catch((err) => {
        setAtendentesDestino([])
        // Sem permissão para ver atendentes do setor destino: ainda pode transferir para fila.
        setErroAtendentesDestino(mensagemFalhaParaToast(err))
      })
  }, [modalTransferir, transferSetorId])

  async function enviar() {
    if (!chat) return
    const t = texto.trim()
    if (!t) {
      toast.showWarning('Escreva uma mensagem.')
      return
    }
    setEnviando(true)
    try {
      await whatsappChats.enviar(chat.id, t)
      setTexto('')
      await carregar()
      toast.showSuccess('Mensagem enviada.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao enviar.'))
    } finally {
      setEnviando(false)
    }
  }

  async function encerrar() {
    if (!chat) return
    setEncerrando(true)
    try {
      await whatsappChats.encerrar(chat.id)
      await carregar()
      toast.showSuccess('Chat encerrado.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err))
    } finally {
      setEncerrando(false)
    }
  }

  async function assumirChat() {
    if (!chat) return
    setAssumindo(true)
    try {
      await whatsappChats.assumir(chat.id)
      await carregar()
      toast.showSuccess('Chat assumido.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível assumir o chat.'))
    } finally {
      setAssumindo(false)
    }
  }

  async function transferirChat() {
    if (!chat) return
    if (!transferSetorId) {
      toast.showWarning('Selecione o setor de destino.')
      return
    }
    const setor_id = Number(transferSetorId)
    const atendente_id = transferAtendenteId ? Number(transferAtendenteId) : null
    setTransferindo(true)
    try {
      await whatsappChats.transferir(chat.id, { setor_id, atendente_id })
      setModalTransferir(false)
      setTransferSetorId('')
      setTransferAtendenteId('')
      await carregar()
      toast.showSuccess('Chat transferido.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível transferir o chat.'))
    } finally {
      setTransferindo(false)
    }
  }

  async function vincular() {
    if (!chat) return
    const tid = Number(ticketVincId)
    if (!Number.isFinite(tid) || tid <= 0) {
      toast.showWarning('Informe o ID numérico do ticket.')
      return
    }
    try {
      await tickets.get(tid)
    } catch {
      toast.showWarning('Ticket não encontrado ou sem permissão.')
      return
    }
    try {
      await whatsappChats.vincularTicket(chat.id, tid)
      setModalVinc(false)
      setTicketVincId('')
      await carregar()
      toast.showSuccess('Ticket vinculado.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err))
    }
  }

  async function abrirTicket() {
    if (!chat) return
    if (!empresaId || !setorId || !assunto.trim()) {
      toast.showWarning('Preencha empresa, setor e assunto.')
      return
    }
    setSalvandoTicket(true)
    try {
      await whatsappChats.abrirTicket(chat.id, {
        empresa_id: Number(empresaId),
        setor_id: Number(setorId),
        assunto: assunto.trim(),
        descricao: descTicket.trim() || null,
      })
      setModalAbrir(false)
      setAssunto('')
      setDescTicket('')
      await carregar()
      toast.showSuccess('Ticket criado e vinculado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível abrir o ticket.'))
    } finally {
      setSalvandoTicket(false)
    }
  }

  if (!Number.isFinite(id) || id <= 0) {
    return <p className="text-red-600">Identificador de chat inválido.</p>
  }

  if (loading && !chat) {
    return <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
  }

  if (!chat) {
    return <p className="text-slate-600 dark:text-slate-400">Chat não encontrado.</p>
  }

  const encerrado = chat.estado === 'encerrado'
  const isResponsavel =
    user?.role === 'admin' || (Boolean(chat.atendente_id) && Boolean(user?.id) && chat.atendente_id === user?.id)
  const podeEnviarCliente = chat.estado === 'em_atendimento' && !encerrado && isResponsavel
  const podeComentarInterno = !encerrado && Boolean(user)
  const podeAssumir = chat.estado === 'aguardando_atendente' && !encerrado
  const podeTransferir = !encerrado && (chat.estado === 'em_atendimento' || chat.estado === 'aguardando_atendente')

  const podeEscolherResponsavel = Boolean(transferSetorId) && atendentesDestino.length > 0 && !erroAtendentesDestino

  return (
  <div className="mx-auto flex h-full max-w-4xl flex-col space-y-6 pb-10 animate-in fade-in duration-500">
    {/* Header de Navegação */}
    <div className="flex items-center justify-between">
      <Link
        to="/whatsapp/atendendo"
        className="group flex items-center gap-2 text-sm font-semibold text-slate-500 transition-colors hover:text-cyan-600 dark:text-slate-400 dark:hover:text-cyan-400"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 group-hover:bg-cyan-50 dark:bg-slate-800 dark:group-hover:bg-cyan-950/30">
          ←
        </span>
        Voltar aos chats
      </Link>
      
      {!encerrado && (
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
          </span>
          <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 dark:text-emerald-400">Atendimento Ativo</span>
        </div>
      )}
    </div>

    {/* Card Principal de Info e Ações */}
    <Card className="overflow-hidden border-none shadow-xl shadow-slate-200/50 ring-1 ring-slate-200 dark:shadow-none dark:ring-slate-800">
      <div className="bg-gradient-to-r from-white to-slate-50/50 p-6 dark:from-slate-900 dark:to-slate-900/50">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="font-mono text-2xl font-bold tracking-tight text-cyan-700 dark:text-cyan-400">
                {chat.protocolo}
              </h1>
              <span className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                {chat.estado.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
              <span className="font-bold">{chat.cliente_nome || 'Cliente'}</span>
              <span className="text-slate-300 dark:text-slate-600">•</span>
              <span className="font-mono text-sm text-slate-500">{chat.wa_id}</span>
            </p>
            {chat.atendente_nome && (
              <p className="text-xs text-slate-500">
                Responsável: <span className="font-medium text-slate-700 dark:text-slate-300">{chat.atendente_nome}</span>
              </p>
            )}
          </div>

          {!encerrado && (
            <div className="flex flex-wrap gap-2">
              {podeAssumir && (
                <Button type="button" loading={assumindo} onClick={() => void assumirChat()} className="bg-cyan-600 shadow-lg shadow-cyan-600/20 hover:bg-cyan-700">
                  Assumir chat
                </Button>
              )}
              <div className="flex items-center gap-2 rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
                {podeTransferir && (
                  <Button type="button" variant="ghost"  onClick={() => setModalTransferir(true)} className="text-xs">
                    Transferir
                  </Button>
                )}
                <Button type="button" variant="ghost"  onClick={() => setModalVinc(true)} className="text-xs">
                  Vincular ticket
                </Button>
                <Button type="button" variant="ghost"  onClick={() => setModalAbrir(true)} className="text-xs">
                  Abrir ticket
                </Button>
              </div>
              {podeEnviarCliente && (
                <Button type="button" variant="danger"  loading={encerrando} onClick={() => void encerrar()} className="ml-2">
                  Encerrar
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Tickets Vinculados */}
        {chat.ticket_ids.length > 0 && (
          <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Tickets vinculados</span>
            <div className="flex flex-wrap gap-2">
              {chat.ticket_ids.map((tid) => (
                <Link
                  key={tid}
                  to={`/tickets/${tid}`}
                  className="group flex items-center gap-1 rounded-full bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-700 transition-all hover:bg-cyan-100 dark:bg-cyan-950/30 dark:text-cyan-400"
                >
                  Ticket #{tid}
                  <span className="opacity-40 transition-all group-hover:translate-x-0.5 group-hover:opacity-100">↗</span>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>

    {/* Histórico de Mensagens */}
    <Card className="flex flex-col border-none shadow-xl ring-1 ring-slate-200 dark:ring-slate-800">
      <div className="border-b border-slate-50 bg-slate-50/30 px-6 py-3 dark:border-slate-800 dark:bg-slate-900/30">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-500">Mensagens</h2>
      </div>
      
      <ul className="mt-3 max-h-[420px] space-y-4 overflow-y-auto px-6 py-4">
        {msgs.map((m) => {
          const isSystem = m.evento_sistema === 'comentario_interno';
          const isInbound = m.direcao === 'inbound';
          
          return (
            <li key={m.id} className={`flex w-full flex-col ${isInbound ? 'items-start' : 'items-end'}`}>
              {isSystem && (
                <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-amber-700 dark:text-amber-400">
                  🔒 Comentário interno
                </p>
              )}
              <div className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm shadow-sm ${
                isSystem 
                  ? 'border border-amber-100 bg-amber-50 text-amber-900 dark:border-amber-900/30 dark:bg-amber-950/20 dark:text-amber-100'
                  : isInbound
                    ? 'rounded-tl-none bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                    : 'rounded-tr-none bg-cyan-600 text-white dark:bg-cyan-700'
              }`}>
                <ConteudoMensagemWhatsApp chatId={chat.id} m={m} />
              </div>
              <p className="mt-1 text-[10px] font-medium text-slate-500 dark:text-slate-400">
                {m.direcao === 'outbound' ? m.atendente_nome || 'Equipe' : 'Cliente'} ·{' '}
                {m.created_at ? new Date(m.created_at).toLocaleString('pt-BR') : '—'}
              </p>
            </li>
          );
        })}
      </ul>

      {/* Footer com Input Condicional */}
      <div className="border-t border-slate-100 p-4 dark:border-slate-800">
        {podeEnviarCliente && (
          <div className="space-y-3">
            <textarea
              id="wa-msg"
              rows={3}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              className="w-full resize-none rounded-xl border-none bg-slate-50 p-4 text-sm focus:ring-2 focus:ring-cyan-500 dark:bg-slate-900/50 dark:text-slate-100"
              placeholder="Digite a mensagem para o cliente…"
            />
            <div className="flex justify-end">
              <Button type="button" loading={enviando} onClick={() => void enviar()} className="bg-cyan-600 hover:bg-cyan-700">
                Enviar Mensagem
              </Button>
            </div>
          </div>
        )}

        {!podeEnviarCliente && podeComentarInterno && (
          <div className="space-y-3">
            <textarea
              id="wa-interno"
              rows={3}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              className="w-full resize-none rounded-xl border-none bg-amber-50/50 p-4 text-sm italic focus:ring-2 focus:ring-amber-500 dark:bg-amber-950/10 dark:text-amber-100"
              placeholder="Escreva um comentário interno (não será enviado ao cliente)…"
            />
            <div className="flex items-center justify-between gap-3">
              <p className="text-[10px] font-medium text-slate-500 dark:text-slate-400">
                Você não é o responsável por este chat. Este texto ficará visível apenas internamente.
              </p>
              <Button
                type="button"
                loading={enviando}
                onClick={() => {
                  if (!chat) return
                  const t = texto.trim()
                  if (!t) {
                    toast.showWarning('Escreva um comentário.')
                    return
                  }
                  setEnviando(true)
                  whatsappChats
                    .comentarInterno(chat.id, t)
                    .then(async () => {
                      setTexto('')
                      await carregar()
                      toast.showSuccess('Comentário adicionado.')
                    })
                    .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Falha ao comentar.')))
                    .finally(() => setEnviando(false))
                }}
                className="bg-amber-600 hover:bg-amber-700"
              >
                Adicionar comentário
              </Button>
            </div>
          </div>
        )}

        {encerrado && (
          <p className="py-4 text-center text-sm font-medium text-slate-400">Conversa encerrada (somente leitura).</p>
        )}
        
        {chat.estado === 'aguardando_atendente' && !encerrado && (
          <div className="mt-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/20 dark:text-amber-300">
            Este chat ainda está na fila. Clique em <span className="font-bold underline cursor-pointer" onClick={() => void assumirChat()}>Assumir chat</span> acima para responder.
          </div>
        )}
      </div>
    </Card>

    {/* Modais com Estilo Refinado (Backdrop Blur) */}
    {modalVinc && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4" role="dialog">
        <Card className="w-full max-w-md border-none p-6 shadow-2xl ring-1 ring-slate-200 dark:ring-slate-800 animate-in zoom-in-95 duration-200">
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Vincular ticket existente</h3>
          <p className="mt-1 text-sm text-slate-500">Informe o número do ticket para associar a esta conversa.</p>
          <Input
            className="mt-4"
            type="number"
            value={ticketVincId}
            onChange={(e) => setTicketVincId(e.target.value)}
            placeholder="Ex.: 42"
          />
          <div className="mt-6 flex justify-end gap-3">
            <Button type="button" variant="secondary" onClick={() => setModalVinc(false)}>Cancelar</Button>
            <Button type="button" onClick={() => void vincular()} className="bg-cyan-600">Vincular</Button>
          </div>
        </Card>
      </div>
    )}

    {modalAbrir && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4" role="dialog">
        <Card className="max-h-[90vh] w-full max-w-lg overflow-y-auto border-none p-6 shadow-2xl ring-1 ring-slate-200 dark:ring-slate-800 animate-in zoom-in-95">
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Abrir novo ticket</h3>
          <div className="mt-4 space-y-4">
            <div className="grid gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Empresa</label>
              <Select
                value={empresaId === '' ? '' : empresaId}
                onChange={(v) => setEmpresaId(v === '' ? '' : Number(v))}
                includeEmpty
                emptyLabel="Selecione uma empresa…"
                options={empresasList.map((e) => ({ value: e.id, label: e.nome }))}
              />
            </div>
            <div className="grid gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Setor</label>
              <Select
                value={setorId === '' ? '' : setorId}
                onChange={(v) => setSetorId(v === '' ? '' : Number(v))}
                includeEmpty
                emptyLabel="Selecione um setor…"
                options={setoresList.filter((s) => s.ativo).map((s) => ({ value: s.id, label: s.nome }))}
              />
            </div>
            <div className="grid gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Assunto</label>
              <Input value={assunto} onChange={(e) => setAssunto(e.target.value)} placeholder="Título do atendimento" />
            </div>
            <div className="grid gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Descrição (opcional)</label>
              <textarea
                value={descTicket}
                onChange={(e) => setDescTicket(e.target.value)}
                rows={3}
                className="w-full rounded-lg border border-slate-200 bg-white p-3 text-sm focus:ring-2 focus:ring-cyan-500 dark:border-slate-700 dark:bg-slate-900"
              />
            </div>
          </div>
          <div className="mt-8 flex justify-end gap-3 border-t pt-4">
            <Button type="button" variant="secondary" onClick={() => setModalAbrir(false)}>Cancelar</Button>
            <Button type="button" loading={salvandoTicket} onClick={() => void abrirTicket()} className="bg-cyan-600">Criar Ticket</Button>
          </div>
        </Card>
      </div>
    )}

    {modalTransferir && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4" role="dialog">
        <Card className="w-full max-w-lg border-none p-6 shadow-2xl ring-1 ring-slate-200 dark:ring-slate-800 animate-in zoom-in-95">
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Transferir chat</h3>
          <p className="mt-1 text-sm text-slate-500">Mova este atendimento para outro setor ou colega.</p>
          <div className="mt-6 space-y-4">
            <div className="grid gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Setor de Destino</label>
              <Select
                value={transferSetorId === '' ? '' : transferSetorId}
                onChange={(v) => {
                  const n = v === '' ? '' : Number(v)
                  setTransferSetorId(n)
                  setTransferAtendenteId('')
                }}
                includeEmpty
                emptyLabel="Escolha o setor…"
                options={setoresList.filter((s) => s.ativo).map((s) => ({ value: s.id, label: s.nome }))}
              />
            </div>
            <div className="grid gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Atendente (opcional)</label>
              <Select
                value={transferAtendenteId === '' ? '' : transferAtendenteId}
                onChange={(v) => setTransferAtendenteId(v === '' ? '' : Number(v))}
                includeEmpty
                emptyLabel="Deixar na fila do setor"
                disabled={!podeEscolherResponsavel}
                options={atendentesDestino
                  .filter((a) => a.ativo)
                  .map((a) => ({ value: a.id, label: `${a.nome} (${a.role})` }))}
              />
              {erroAtendentesDestino && (
                <p className="text-[11px] text-amber-600 font-medium">
                  Você não tem permissão para escolher um atendente específico neste setor.
                </p>
              )}
            </div>
          </div>
          <div className="mt-8 flex justify-end gap-3 border-t pt-4">
            <Button type="button" variant="secondary" onClick={() => setModalTransferir(false)}>Cancelar</Button>
            <Button type="button" loading={transferindo} onClick={() => void transferirChat()} className="bg-cyan-600">Transferir Agora</Button>
          </div>
        </Card>
      </div>
    )}
  </div>
)
}