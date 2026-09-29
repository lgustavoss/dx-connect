import { useEffect, useState } from 'react'
import { fetchWhatsAppMidiaBlob, whatsappChats, type WhatsappChats } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { resolveWhatsappMidiaObjectUrl } from '../../lib/whatsappMidiaCache'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import { visualTipoArquivo } from '../../lib/fileTypeIcon'
import { CustomAudioPlayer } from '../CustomAudioPlayer'
import { DocumentoPreviewLightbox } from './DocumentoPreviewLightbox'
import { useToast } from '../ui/Toast'

const ROTULO_SEM_LEGENDA =
  /^(?:\[\s*[^\]]+\s*\]:\s*)?\[(Imagem|Áudio|Vídeo|Documento|Figurinha|Contacto|Localização)(\s+enviad[oa])?\]$/i

type Bloco = {
  chat: WhatsappChats.Anterior
  mensagens: WhatsappChats.Mensagem[]
}

function quando(iso?: string | null) {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function rotuloCorte(chat: WhatsappChats.Anterior) {
  const proto = exibirProtocolo(chat.protocolo)
  const fim = quando(chat.encerramento_at)
  if (fim) return `Atendimento ${proto} encerrado em ${fim}`
  const inicio = quando(chat.atendimento_inicio_at || chat.created_at)
  return inicio ? `Atendimento ${proto} iniciado em ${inicio}` : `Atendimento ${proto}`
}

function legendaVisivel(corpo: string | null | undefined) {
  const texto = (corpo || '').trim()
  if (!texto || ROTULO_SEM_LEGENDA.test(texto)) return null
  return corpo
}

function MiniMidia({ chatId, m }: { chatId: number; m: WhatsappChats.Mensagem }) {
  const tipo = (m.tipo_midia || 'texto').toLowerCase()
  const [url, setUrl] = useState<string | null>(null)
  const [falhou, setFalhou] = useState(false)
  const [docAberto, setDocAberto] = useState(false)

  useEffect(() => {
    let cancel = false
    void resolveWhatsappMidiaObjectUrl(chatId, m.id, () => fetchWhatsAppMidiaBlob(chatId, m.id))
      .then((u) => {
        if (!cancel) setUrl(u)
      })
      .catch(() => {
        if (!cancel) setFalhou(true)
      })
    return () => {
      cancel = true
    }
  }, [chatId, m.id])

  if (falhou) return <p className="text-xs italic opacity-70">Arquivo indisponível</p>
  if (!url) return <p className="text-xs italic opacity-70">Carregando…</p>

  if (tipo === 'imagem' || tipo === 'figurinha') {
    return <img src={url} alt="" className="max-h-40 max-w-full rounded-lg object-contain" />
  }
  if (tipo === 'audio') return <CustomAudioPlayer src={url} />
  if (tipo === 'video') {
    return <video src={url} controls className="max-h-48 max-w-full rounded-lg" />
  }

  const visual = visualTipoArquivo(m.midia_nome_original, m.mimetype)
  const rotulo = (m.midia_nome_original || '').trim() || visual.label
  return (
    <>
      <button
        type="button"
        className="flex items-center gap-2 text-left text-xs font-semibold underline"
        onClick={() => setDocAberto(true)}
        aria-label="Abrir arquivo"
      >
        <span aria-hidden>{visual.emoji}</span>
        <span className="min-w-0 break-all">{rotulo}</span>
      </button>
      {docAberto ? (
        <DocumentoPreviewLightbox
          url={url}
          nome={m.midia_nome_original}
          mime={m.mimetype}
          onClose={() => setDocAberto(false)}
        />
      ) : null}
    </>
  )
}

function Bolha({ chatId, m }: { chatId: number; m: WhatsappChats.Mensagem }) {
  const sistema = Boolean(m.evento_sistema)
  const inbound = m.direcao === 'inbound'
  const hora = quando(m.created_at)
  const tipo = (m.tipo_midia || 'texto').toLowerCase()
  const midiaAberta = tipo !== 'texto' && Boolean(m.midia_disponivel) && !m.apagada
  const legenda = legendaVisivel(m.corpo)
  if (sistema) {
    return (
      <p className="mx-auto max-w-md rounded-full bg-amber-100/90 px-3 py-1 text-center text-[11px] text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
        {m.corpo}
        {hora ? ` · ${hora}` : ''}
      </p>
    )
  }
  return (
    <div className={`flex w-full ${inbound ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-[85%] space-y-1 rounded-2xl px-3 py-2 text-sm shadow-sm sm:max-w-[70%] ${
          inbound
            ? 'bg-white text-slate-800 dark:bg-slate-800 dark:text-slate-100'
            : 'bg-cyan-600 text-white'
        }`}
      >
        {midiaAberta ? <MiniMidia chatId={chatId} m={m} /> : null}
        {m.apagada ? (
          <p className="italic opacity-70">Mensagem apagada</p>
        ) : tipo === 'texto' ? (
          m.corpo ? <p className="whitespace-pre-wrap break-words">{m.corpo}</p> : null
        ) : legenda ? (
          <p className="whitespace-pre-wrap break-words">{legenda}</p>
        ) : null}
        {!midiaAberta && tipo !== 'texto' && !m.apagada ? (
          <p className="text-[11px] opacity-80">
            {tipo === 'audio' ? 'Áudio' : tipo === 'video' ? 'Vídeo' : tipo === 'imagem' || tipo === 'figurinha' ? 'Imagem' : 'Arquivo'}
          </p>
        ) : null}
        {hora ? <p className={`text-[10px] ${inbound ? 'text-slate-400' : 'text-cyan-100'}`}>{hora}</p> : null}
      </div>
    </div>
  )
}

function Divisor({ texto }: { texto: string }) {
  return (
    <div className="flex w-full items-center gap-3 py-2" role="separator">
      <div className="h-px flex-1 bg-slate-400/40" />
      <span className="max-w-[16rem] text-center text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300">
        {texto}
      </span>
      <div className="h-px flex-1 bg-slate-400/40" />
    </div>
  )
}

export function AtendimentosAnterioresFaixa({
  chatId,
  protocoloAtual,
  inicioAtual,
}: {
  chatId: number
  protocoloAtual?: string | null
  inicioAtual?: string | null
}) {
  const toast = useToast()
  const [disponivel, setDisponivel] = useState<WhatsappChats.Anterior | null>(null)
  const [blocos, setBlocos] = useState<Bloco[]>([])
  const [carregando, setCarregando] = useState(false)

  useEffect(() => {
    let cancel = false
    setBlocos([])
    setDisponivel(null)
    void whatsappChats
      .anterior(chatId)
      .then((row) => {
        if (!cancel) setDisponivel(row)
      })
      .catch(() => {
        if (!cancel) setDisponivel(null)
      })
    return () => {
      cancel = true
    }
  }, [chatId])

  async function carregar(alvo: WhatsappChats.Anterior) {
    setCarregando(true)
    try {
      const mensagens = await whatsappChats.mensagens(alvo.id)
      const mais = await whatsappChats.anterior(alvo.id)
      setBlocos((prev) => [{ chat: alvo, mensagens }, ...prev])
      setDisponivel(mais)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível abrir o atendimento anterior.'))
    } finally {
      setCarregando(false)
    }
  }

  function voltarAtual() {
    setBlocos([])
    document.getElementById('wa-atendimento-atual')?.scrollIntoView({ block: 'start' })
    void whatsappChats.anterior(chatId).then(setDisponivel).catch(() => setDisponivel(null))
  }

  if (!disponivel && blocos.length === 0) return null

  const inicio = quando(inicioAtual)
  const atualTxt = inicio
    ? `Atendimento atual ${exibirProtocolo(protocoloAtual)} começou em ${inicio}`
    : `Atendimento atual ${exibirProtocolo(protocoloAtual)}`

  return (
    <div className="space-y-3 pb-2">
      {disponivel ? (
        <div className="sticky top-0 z-10 flex justify-center">
          <button
            type="button"
            className="rounded-full bg-white/95 px-4 py-2 text-xs font-semibold text-slate-700 shadow-sm ring-1 ring-slate-200 hover:bg-cyan-50 hover:text-slate-800 dark:bg-slate-900/95 dark:text-slate-100 dark:ring-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-100"
            disabled={carregando}
            onClick={() => void carregar(disponivel)}
          >
            {carregando ? 'Carregando…' : blocos.length ? 'Ver o anterior a este' : 'Ver atendimento anterior'}
          </button>
        </div>
      ) : null}

      {blocos.map((bloco, index) => (
        <div key={bloco.chat.id} className="space-y-3">
          {bloco.mensagens.map((m) => (
            <Bolha key={m.id} chatId={bloco.chat.id} m={m} />
          ))}
          <Divisor texto={rotuloCorte(bloco.chat)} />
          {index === blocos.length - 1 ? <Divisor texto={atualTxt} /> : null}
        </div>
      ))}

      {blocos.length > 0 ? (
        <div className="flex justify-center">
          <button
            type="button"
            className="rounded-full bg-cyan-700 px-4 py-2 text-xs font-semibold text-white hover:bg-cyan-800"
            onClick={voltarAtual}
          >
            Voltar à conversa atual
          </button>
        </div>
      ) : null}
    </div>
  )
}
