import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/Button'
import {
  TAMANHO_MIN_AUDIO_BYTES,
  criarMediaRecorder,
  ficheiroDeBlobGravacao,
} from '../../lib/gravacaoAudio'

type Props = {
  disabled?: boolean
  onConcluido: (file: File) => void
  onCancelar: () => void
}

/** Gravação compacta integrada na barra de composição (#443). */
export function WhatsappGravadorAudioInline({ disabled, onConcluido, onCancelar }: Props) {
  const [gravando, setGravando] = useState(false)
  const [segundos, setSegundos] = useState(0)
  const [erro, setErro] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)
  const canceladoRef = useRef(false)
  const onConcluidoRef = useRef(onConcluido)
  const onCancelarRef = useRef(onCancelar)

  useEffect(() => {
    onConcluidoRef.current = onConcluido
  }, [onConcluido])

  useEffect(() => {
    onCancelarRef.current = onCancelar
  }, [onCancelar])

  const pararStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (timerRef.current != null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const pararRecorder = useCallback(() => {
    const rec = recorderRef.current
    if (!rec || rec.state === 'inactive') return
    try {
      if (rec.state === 'recording') rec.requestData()
    } catch {
      /* alguns browsers não implementam requestData */
    }
    try {
      rec.stop()
    } catch {
      /* already stopped */
    }
  }, [])

  useEffect(() => {
    if (disabled) return

    let alive = true
    canceladoRef.current = false
    chunksRef.current = []
    setErro(null)
    setSegundos(0)
    setGravando(false)

    void (async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        if (alive) setErro('Microfone não suportado neste browser (use HTTPS).')
        return
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            channelCount: 1,
          },
        })
        if (!alive) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        streamRef.current = stream

        let recorder: MediaRecorder
        try {
          recorder = criarMediaRecorder(stream)
        } catch {
          stream.getTracks().forEach((t) => t.stop())
          streamRef.current = null
          if (alive) setErro('Gravação de áudio não suportada neste browser.')
          return
        }
        recorderRef.current = recorder

        recorder.ondataavailable = (ev) => {
          if (canceladoRef.current || !alive) return
          if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data)
        }

        recorder.onerror = () => {
          if (!alive) return
          setErro('Falha na gravação. Tente novamente.')
          setGravando(false)
          pararStream()
        }

        recorder.onstop = () => {
          pararStream()
          recorderRef.current = null
          if (!alive || canceladoRef.current) {
            chunksRef.current = []
            setGravando(false)
            return
          }
          const mime = recorder.mimeType || chunksRef.current[0]?.type || 'audio/webm'
          const blob = new Blob(chunksRef.current, { type: mime })
          chunksRef.current = []
          if (blob.size < TAMANHO_MIN_AUDIO_BYTES) {
            setErro('Gravação vazia ou demasiado curta. Segure um pouco e tente de novo.')
            setGravando(false)
            return
          }
          setGravando(false)
          onConcluidoRef.current(ficheiroDeBlobGravacao(blob))
        }

        recorder.start(250)
        if (!alive) {
          pararRecorder()
          return
        }
        setGravando(true)
        timerRef.current = window.setInterval(() => setSegundos((s) => s + 1), 1000)
      } catch {
        pararStream()
        if (alive) setErro('Microfone indisponível. Verifique as permissões do browser.')
      }
    })()

    return () => {
      alive = false
      canceladoRef.current = true
      // Parar o MediaRecorder primeiro; as tracks saem no onstop (evita blob truncado).
      const rec = recorderRef.current
      if (rec && rec.state !== 'inactive') {
        pararRecorder()
      } else {
        pararStream()
      }
    }
  }, [disabled, pararRecorder, pararStream])

  const mm = String(Math.floor(segundos / 60)).padStart(2, '0')
  const ss = String(segundos % 60).padStart(2, '0')

  function parar() {
    if (!gravando) return
    canceladoRef.current = false
    pararRecorder()
  }

  function cancelar() {
    canceladoRef.current = true
    chunksRef.current = []
    const rec = recorderRef.current
    if (rec && rec.state !== 'inactive') {
      pararRecorder()
    } else {
      pararStream()
      recorderRef.current = null
    }
    setGravando(false)
    onCancelarRef.current()
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-200 bg-rose-50/90 px-3 py-2 dark:border-rose-900/40 dark:bg-rose-950/20">
      <div className="flex items-center gap-2 text-xs">
        {gravando && <span className="h-2 w-2 animate-pulse rounded-full bg-rose-500" />}
        <span className="font-medium text-rose-800 dark:text-rose-200">
          {gravando ? `A gravar ${mm}:${ss}` : erro ? 'Gravação interrompida' : 'A preparar microfone…'}
        </span>
      </div>
      <div className="flex gap-2">
        <Button variant="ghost" className="h-8 text-xs" onClick={cancelar}>
          Cancelar
        </Button>
        <Button variant="danger" className="h-8 text-xs" disabled={!gravando} onClick={parar}>
          Enviar áudio
        </Button>
      </div>
      {erro && <p className="w-full text-xs text-rose-700 dark:text-rose-300">{erro}</p>}
    </div>
  )
}
