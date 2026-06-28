export type TipoAnexoPicker = 'imagem' | 'video' | 'audio' | 'documento'

const ACOES: { tipo: TipoAnexoPicker | 'gravar'; rotulo: string; icone: string }[] = [
  { tipo: 'imagem', rotulo: 'Imagem', icone: '🖼️' },
  { tipo: 'video', rotulo: 'Vídeo', icone: '🎬' },
  { tipo: 'audio', rotulo: 'Áudio', icone: '🎵' },
  { tipo: 'documento', rotulo: 'Documento', icone: '📄' },
  { tipo: 'gravar', rotulo: 'Gravar', icone: '🎙️' },
]

type Props = {
  disabled: boolean
  motivoDesabilitado?: string
  onEscolher: (tipo: TipoAnexoPicker) => void
  onGravarAudio: () => void
}

export function WhatsappBarraAnexos({ disabled, motivoDesabilitado, onEscolher, onGravarAudio }: Props) {
  return (
    <div className="mb-2">
      {disabled && motivoDesabilitado && (
        <p className="mb-1.5 text-[11px] text-amber-800 dark:text-amber-200">{motivoDesabilitado}</p>
      )}
      <div className="flex flex-wrap gap-1 sm:gap-1.5">
        {ACOES.map((a) => (
          <button
            key={a.tipo}
            type="button"
            disabled={disabled}
            title={disabled ? motivoDesabilitado : a.rotulo}
            onClick={() => (a.tipo === 'gravar' ? onGravarAudio() : onEscolher(a.tipo))}
            className="flex min-w-[3.5rem] flex-col items-center gap-0.5 rounded-xl border border-slate-200 bg-white px-2 py-1.5 text-[10px] font-semibold text-slate-700 shadow-sm transition hover:border-cyan-300 hover:bg-cyan-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-cyan-700 dark:hover:bg-cyan-950/30"
          >
            <span className="text-base leading-none" aria-hidden>
              {a.icone}
            </span>
            <span>{a.rotulo}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export const ACCEPT_ANEXO: Record<TipoAnexoPicker, string> = {
  imagem: 'image/*',
  video: 'video/*',
  audio: 'audio/*',
  documento:
    '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip,.rar,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
