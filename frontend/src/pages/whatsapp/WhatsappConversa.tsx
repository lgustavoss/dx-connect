import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  empresas,
  setores,
  atendentes,
  tickets,
  whatsappChats,
  fetchWhatsAppMidiaBlob,
  uploadWhatsAppMidia,
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

function textoCitacaoResumido(m: WhatsappChats.Mensagem, todas: WhatsappChats.Mensagem[]): string {
  const prev = (m.quoted_corpo_preview || '').trim()
  if (prev) return prev.length > 240 ? `${prev.slice(0, 240)}…` : prev
  const ref = todas.find(
    (x) => Boolean(x.wa_message_id && m.quoted_wa_message_id && x.wa_message_id === m.quoted_wa_message_id),
  )
  if (ref) {
    const t = ref.corpo.trim()
    return t.length > 240 ? `${t.slice(0, 240)}…` : t
  }
  return 'Mensagem'
}

function mediatipoDoFicheiro(f: File): string {
  if (f.type.startsWith('image/')) return 'imagem'
  if (f.type.startsWith('video/')) return 'video'
  if (f.type.startsWith('audio/')) return 'audio'
  return 'documento'
}

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
  const [citando, setCitando] = useState<WhatsappChats.Mensagem | null>(null)
  const [enviando, setEnviando] = useState(false)
  const fileMidiaRef = useRef<HTMLInputElement>(null)
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
      await whatsappChats.enviar(chat.id, {
        texto: t,
        quoted_wa_message_id: citando?.wa_message_id ?? undefined,
      })
      setTexto('')
      setCitando(null)
      await carregar()
      toast.showSuccess('Mensagem enviada.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao enviar.'))
    } finally {
      setEnviando(false)
    }
  }

  async function onEscolherFicheiroMidia(ev: React.ChangeEvent<HTMLInputElement>) {
    const f = ev.target.files?.[0]
    ev.target.value = ''
    if (!f || !chat) return
    const responsavel =
      user?.role === 'admin' ||
      (Boolean(chat.atendente_id) && Boolean(user?.id) && chat.atendente_id === user?.id)
    if (chat.estado !== 'em_atendimento' || !responsavel) {
      toast.showWarning('Só é possível enviar ficheiros enquanto atende o chat ativo.')
      return
    }
    const fd = new FormData()
    fd.append('file', f)
    fd.append('mediatipo', mediatipoDoFicheiro(f))
    fd.append('caption', '')
    if (citando?.wa_message_id) fd.append('quoted_wa_message_id', citando.wa_message_id)
    setEnviando(true)
    try {
      await uploadWhatsAppMidia(chat.id, fd)
      setCitando(null)
      await carregar()
      toast.showSuccess('Mídia enviada.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao enviar ficheiro.'))
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
    <div className="mx-auto max-w-3xl space-y-4 pb-10">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          to="/whatsapp/atendendo"
          className="text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
        >
          ← Voltar aos chats
        </Link>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-lg font-semibold text-cyan-700 dark:text-cyan-400">{chat.protocolo}</p>
            <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">
              {chat.cliente_nome || 'Cliente'} · <span className="font-mono text-xs">{chat.wa_id}</span>
            </p>
            <p className="mt-2 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Estado: <span className="font-semibold">{chat.estado.replace(/_/g, ' ')}</span>
              {chat.atendente_nome && <> · Atendente: {chat.atendente_nome}</>}
            </p>
          </div>
          {!encerrado && (
            <div className="flex flex-wrap gap-2">
              {podeAssumir && (
                <Button type="button" loading={assumindo} onClick={() => void assumirChat()}>
                  Assumir chat
                </Button>
              )}
              {podeTransferir && (
                <Button type="button" variant="secondary" onClick={() => setModalTransferir(true)}>
                  Transferir
                </Button>
              )}
              <Button type="button" variant="secondary" onClick={() => setModalVinc(true)}>
                Vincular ticket
              </Button>
              <Button type="button" variant="secondary" onClick={() => setModalAbrir(true)}>
                Abrir ticket
              </Button>
              {podeEnviarCliente && (
                <Button type="button" variant="danger" loading={encerrando} onClick={() => void encerrar()}>
                  Encerrar chat
                </Button>
              )}
            </div>
          )}
        </div>
        {chat.ticket_ids.length > 0 && (
          <div className="mt-3 border-t border-slate-200 pt-3 dark:border-slate-700">
            <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">Tickets vinculados</p>
            <ul className="mt-1 flex flex-wrap gap-2">
              {chat.ticket_ids.map((tid) => (
                <li key={tid}>
                  <Link
                    to={`/tickets/${tid}`}
                    className="text-sm font-medium text-cyan-700 underline hover:text-cyan-800 dark:text-cyan-400"
                  >
                    Ticket #{tid}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      <Card className="p-4">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Mensagens</h2>
        <ul className="mt-3 max-h-[420px] space-y-3 overflow-y-auto pr-1">
          {msgs.map((m) => (
            <li
              key={m.id}
              className={`rounded-lg px-3 py-2 text-sm ${
                m.direcao === 'inbound'
                  ? 'ml-0 mr-8 bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                  : 'ml-8 mr-0 bg-cyan-50 text-slate-900 dark:bg-cyan-950/40 dark:text-slate-100'
              }`}
            >
              {m.evento_sistema === 'comentario_interno' && (
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
                  Comentário interno
                </p>
              )}
              {(m.quoted_wa_message_id || m.quoted_corpo_preview) && (
                <div className="mb-2 border-l-2 border-cyan-600/50 pl-2 text-xs text-slate-600 dark:border-cyan-400/50 dark:text-slate-400">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Em resposta a</span>
                  <p className="mt-0.5 line-clamp-4 whitespace-pre-wrap">{textoCitacaoResumido(m, msgs)}</p>
                </div>
              )}
              <ConteudoMensagemWhatsApp chatId={chat.id} m={m} />
              {podeEnviarCliente && m.wa_message_id && (
                <div className="mt-1 flex justify-end">
                  <button
                    type="button"
                    className="text-[11px] font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                    onClick={() => setCitando(m)}
                  >
                    Citar esta mensagem
                  </button>
                </div>
              )}
              <p className="mt-1 text-[10px] text-slate-500 dark:text-slate-400">
                {m.direcao === 'outbound' ? m.atendente_nome || 'Equipe' : 'Cliente'} ·{' '}
                {m.created_at ? new Date(m.created_at).toLocaleString('pt-BR') : '—'}
              </p>
            </li>
          ))}
        </ul>

        {podeEnviarCliente && (
          <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-700">
            <input
              ref={fileMidiaRef}
              type="file"
              className="hidden"
              accept="image/*,video/*,audio/*,.pdf,.doc,.docx"
              onChange={(e) => void onEscolherFicheiroMidia(e)}
            />
            {citando && (
              <div className="mb-3 flex items-start justify-between gap-2 rounded-lg border border-cyan-200 bg-cyan-50/80 px-3 py-2 text-xs text-slate-800 dark:border-cyan-900/50 dark:bg-cyan-950/30 dark:text-slate-200">
                <p>
                  A responder citando uma mensagem do WhatsApp. O envio (texto ou ficheiro) incluirá esta citação.
                </p>
                <button
                  type="button"
                  className="shrink-0 font-medium text-cyan-800 underline dark:text-cyan-300"
                  onClick={() => setCitando(null)}
                >
                  Cancelar
                </button>
              </div>
            )}
            <label className="sr-only" htmlFor="wa-msg">
              Nova mensagem
            </label>
            <textarea
              id="wa-msg"
              rows={3}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              placeholder="Digite a mensagem para o cliente…"
            />
            <div className="mt-2 flex flex-wrap items-center justify-end gap-2">
              <Button type="button" variant="secondary" disabled={enviando} onClick={() => fileMidiaRef.current?.click()}>
                Enviar ficheiro
              </Button>
              <Button type="button" loading={enviando} onClick={() => void enviar()}>
                Enviar
              </Button>
            </div>
          </div>
        )}
        {!podeEnviarCliente && podeComentarInterno && (
          <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-700">
            <label className="sr-only" htmlFor="wa-interno">
              Comentário interno
            </label>
            <textarea
              id="wa-interno"
              rows={3}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              placeholder="Escreva um comentário interno (não será enviado ao cliente)…"
            />
            <div className="mt-2 flex items-center justify-between gap-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Você não é o responsável por este chat. Este texto ficará visível apenas no DX Connect.
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
              >
                Adicionar comentário
              </Button>
            </div>
          </div>
        )}
        {encerrado && (
          <p className="mt-4 text-center text-sm text-slate-500 dark:text-slate-400">Conversa encerrada (somente leitura).</p>
        )}
        {chat.estado === 'aguardando_atendente' && !encerrado && (
          <p className="mt-4 text-sm text-amber-800 dark:text-amber-200">
            Este chat ainda está na fila. Clique em <span className="font-semibold">Assumir chat</span> acima para poder responder (ou use{' '}
            <Link to="/whatsapp/atendendo" className="underline">
              Atendendo
            </Link>
            ).
          </p>
        )}
      </Card>

      {modalVinc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog">
          <Card className="w-full max-w-md p-4 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Vincular a ticket existente</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Informe o ID interno do ticket (número da URL).</p>
            <Input
              className="mt-3"
              type="number"
              value={ticketVincId}
              onChange={(e) => setTicketVincId(e.target.value)}
              placeholder="Ex.: 42"
            />
            <div className="mt-4 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setModalVinc(false)}>
                Cancelar
              </Button>
              <Button type="button" onClick={() => void vincular()}>
                Vincular
              </Button>
            </div>
          </Card>
        </div>
      )}

      {modalAbrir && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog">
          <Card className="max-h-[90vh] w-full max-w-lg overflow-y-auto p-4 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Abrir ticket a partir do chat</h3>
            <div className="mt-4 space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Empresa</label>
                <Select
                  value={empresaId === '' ? '' : empresaId}
                  onChange={(v) => setEmpresaId(v === '' ? '' : Number(v))}
                  includeEmpty
                  emptyLabel="Selecione…"
                  options={empresasList.map((e) => ({ value: e.id, label: e.nome }))}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Setor</label>
                <Select
                  value={setorId === '' ? '' : setorId}
                  onChange={(v) => setSetorId(v === '' ? '' : Number(v))}
                  includeEmpty
                  emptyLabel="Selecione…"
                  options={setoresList.filter((s) => s.ativo).map((s) => ({ value: s.id, label: s.nome }))}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Assunto</label>
                <Input value={assunto} onChange={(e) => setAssunto(e.target.value)} placeholder="Resumo do problema" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Descrição (opcional)</label>
                <textarea
                  value={descTicket}
                  onChange={(e) => setDescTicket(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setModalAbrir(false)}>
                Cancelar
              </Button>
              <Button type="button" loading={salvandoTicket} onClick={() => void abrirTicket()}>
                Criar ticket
              </Button>
            </div>
          </Card>
        </div>
      )}

      {modalTransferir && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog">
          <Card className="w-full max-w-lg p-4 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Transferir chat</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Escolha o setor de destino. Opcionalmente, selecione um atendente desse setor para já atribuir o chat.
            </p>
            <div className="mt-4 space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Setor</label>
                <Select
                  value={transferSetorId === '' ? '' : transferSetorId}
                  onChange={(v) => {
                    const n = v === '' ? '' : Number(v)
                    setTransferSetorId(n)
                    setTransferAtendenteId('')
                  }}
                  includeEmpty
                  emptyLabel="Selecione…"
                  options={setoresList.filter((s) => s.ativo).map((s) => ({ value: s.id, label: s.nome }))}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Atendente (opcional)</label>
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
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Você pode transferir para a fila do setor, mas não tem permissão para selecionar um atendente específico deste setor.
                  </p>
                )}
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setModalTransferir(false)}>
                Cancelar
              </Button>
              <Button type="button" loading={transferindo} onClick={() => void transferirChat()}>
                Transferir
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
