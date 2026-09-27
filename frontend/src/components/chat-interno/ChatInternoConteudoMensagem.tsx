import { useEffect, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { fetchChatInternoMidiaBlob, type ChatInterno } from '../../api/client'
import { segmentarCorpoComMencoes } from '../../lib/chatInternoMencoes'
import { useAuth } from '../../contexts/AuthContext'
import { ImageLightboxViewer } from '../chat/ImageLightboxViewer'
import { DocumentoPreviewLightbox } from '../chat/DocumentoPreviewLightbox'

const ROTULO_SEM_LEGENDA = /^(📷 Imagem|🎬 Vídeo|🎵 Áudio|📄 Documento)$/

type Props = {
  conversaId: number
  mensagem: ChatInterno.Mensagem
  textoClaro?: boolean
  /** Rodapé compacto (hora/status) embutido no canto — estilo WhatsApp Web para texto curto */
  rodape?: ReactNode
  somenteTextoCompacto?: boolean
}

function CorpoComMencoes({
  corpo,
  mencoes,
  textoClaro,
}: {
  corpo: string
  mencoes?: ChatInterno.MencaoMensagem[]
  textoClaro?: boolean
}) {
  const { user } = useAuth()
  const segs = segmentarCorpoComMencoes(corpo, mencoes, user?.id)
  return (
    <>
      {segs.map((s, i) =>
        s.kind === 'mention' ? (
          <span
            key={i}
            className={
              textoClaro
                ? s.self
                  ? 'rounded bg-white/25 px-0.5 font-semibold text-white'
                  : 'font-semibold text-cyan-100'
                : s.self
                  ? 'rounded bg-cyan-100 px-0.5 font-semibold text-cyan-800 dark:bg-cyan-900/60 dark:text-cyan-200'
                  : 'font-semibold text-cyan-700 dark:text-cyan-300'
            }
          >
            {s.value}
          </span>
        ) : (
          <span key={i}>{s.value}</span>
        ),
      )}
    </>
  )
}

export function ChatInternoConteudoMensagem({
  conversaId,
  mensagem,
  textoClaro,
  rodape,
  somenteTextoCompacto = false,
}: Props) {
  const tipo = (mensagem.tipo_midia || 'texto').toLowerCase()
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(false)
  const [zoomAberto, setZoomAberto] = useState(false)
  const [docPreviewAberto, setDocPreviewAberto] = useState(false)

  useEffect(() => {
    if (!mensagem.midia_disponivel || tipo === 'texto') {
      setUrl(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setErr(false)
    void fetchChatInternoMidiaBlob(conversaId, mensagem.id)
      .then((blob) => {
        if (cancelled) return
        setUrl(URL.createObjectURL(blob))
      })
      .catch(() => {
        if (!cancelled) setErr(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [conversaId, mensagem.id, mensagem.midia_disponivel, tipo])

  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [url])

  useEffect(() => {
    if (!zoomAberto) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setZoomAberto(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [zoomAberto])

  const legenda =
    mensagem.corpo && !ROTULO_SEM_LEGENDA.test(mensagem.corpo.trim()) ? mensagem.corpo : null

  if (mensagem.apagada) {
    return (
      <p
        className={`text-sm italic opacity-70 ${
          textoClaro ? 'text-cyan-100' : 'text-slate-500 dark:text-slate-400'
        }`}
      >
        Mensagem apagada
      </p>
    )
  }

  if (tipo === 'texto' || !mensagem.tipo_midia || mensagem.tipo_midia === 'texto') {
    if (somenteTextoCompacto && rodape) {
      return (
        <div className="relative min-w-[3.5rem]">
          <p
            className={`whitespace-pre-wrap break-words text-sm leading-[1.35] [overflow-wrap:anywhere] ${
              textoClaro ? 'text-white' : 'text-slate-900 dark:text-slate-100'
            }`}
          >
            <CorpoComMencoes corpo={mensagem.corpo} mencoes={mensagem.mencoes} textoClaro={textoClaro} />
            <span aria-hidden className="inline-block h-[0.85rem] w-[4.25rem]" />
          </p>
          <div className="absolute bottom-0 right-0 flex items-center gap-0.5 pl-1">{rodape}</div>
        </div>
      )
    }
    return (
      <p
        className={`whitespace-pre-wrap break-words text-sm leading-[1.35] [overflow-wrap:anywhere] ${
          textoClaro ? 'text-white' : 'text-slate-900 dark:text-slate-100'
        }`}
      >
        <CorpoComMencoes corpo={mensagem.corpo} mencoes={mensagem.mencoes} textoClaro={textoClaro} />
      </p>
    )
  }

  if (!mensagem.midia_disponivel) {
    return <p className="text-sm italic opacity-70">{mensagem.corpo || 'Mídia indisponível'}</p>
  }

  if (loading || !url) {
    return <p className="text-xs animate-pulse opacity-50">Carregando mídia…</p>
  }

  if (err) {
    return <p className="text-xs italic opacity-50">Erro ao carregar mídia</p>
  }

  const mediaClass = 'max-h-64 max-w-full rounded-lg border border-black/5 shadow-sm'

  if (tipo === 'imagem') {
    return (
      <>
        <div className="space-y-1">
          <button
            type="button"
            className="block max-w-full cursor-zoom-in rounded-lg border-0 bg-transparent p-0 text-left"
            onClick={(e) => {
              e.stopPropagation()
              setZoomAberto(true)
            }}
            onDoubleClick={(e) => e.stopPropagation()}
            aria-label="Ampliar imagem"
          >
            <img
              src={url}
              alt=""
              className={`${mediaClass} transition-transform duration-200 hover:scale-[1.02]`}
            />
          </button>
          {legenda && (
            <p
              className={`whitespace-pre-wrap break-words text-sm [overflow-wrap:anywhere] ${textoClaro ? 'text-cyan-50' : ''}`}
            >
              {legenda}
            </p>
          )}
        </div>
        {zoomAberto &&
          createPortal(
            <div
              className="fixed inset-0 z-[200] flex flex-col bg-black/90 p-4 backdrop-blur-sm animate-in fade-in duration-200"
              role="dialog"
              aria-modal="true"
              aria-label="Imagem ampliada"
              onClick={() => setZoomAberto(false)}
            >
              <div className="z-30 flex h-12 shrink-0 justify-end" onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  className="flex h-12 w-12 cursor-pointer items-center justify-center rounded-full bg-white/15 text-3xl font-bold text-white transition-colors hover:bg-white/25"
                  onClick={() => setZoomAberto(false)}
                  aria-label="Fechar"
                >
                  &times;
                </button>
              </div>
              <div className="relative z-0 flex min-h-0 w-full flex-1 items-center justify-center overflow-hidden" onClick={(e) => e.stopPropagation()}>
                <ImageLightboxViewer src={url} />
              </div>
              {legenda ? (
                <p
                  className="mt-3 max-w-2xl shrink-0 self-center rounded-xl bg-black/40 px-4 py-2 text-center text-sm text-white backdrop-blur-md"
                  onClick={(e) => e.stopPropagation()}
                >
                  {legenda}
                </p>
              ) : null}
              <a
                href={url}
                download={mensagem.nome_arquivo || 'imagem.jpg'}
                className="z-30 mt-3 shrink-0 self-end rounded-xl bg-sky-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg hover:bg-sky-500"
                onClick={(e) => e.stopPropagation()}
              >
                Baixar
              </a>
            </div>,
            document.body,
          )}
      </>
    )
  }

  if (tipo === 'video') {
    return (
      <div className="space-y-1">
        <video src={url} controls className={mediaClass} />
        {legenda && <p className="whitespace-pre-wrap break-words text-sm [overflow-wrap:anywhere]">{legenda}</p>}
      </div>
    )
  }

  if (tipo === 'audio') {
    return (
      <div className="space-y-1">
        <audio src={url} controls className="max-w-full" />
        {legenda && <p className="whitespace-pre-wrap break-words text-sm [overflow-wrap:anywhere]">{legenda}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={() => setDocPreviewAberto(true)}
        aria-label="Abrir documento"
        className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm underline ${
          textoClaro
            ? 'border-cyan-400/40 text-cyan-50 hover:bg-cyan-500/20'
            : 'border-slate-200 bg-white text-slate-800 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100'
        }`}
      >
        📄 {mensagem.nome_arquivo || 'Documento'}
      </button>
      {legenda && <p className="whitespace-pre-wrap break-words text-sm [overflow-wrap:anywhere]">{legenda}</p>}
      {docPreviewAberto && url ? (
        <DocumentoPreviewLightbox
          url={url}
          nome={mensagem.nome_arquivo}
          mime={mensagem.mimetype}
          onClose={() => setDocPreviewAberto(false)}
        />
      ) : null}
    </div>
  )
}
