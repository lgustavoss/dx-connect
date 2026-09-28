import { MensagemRodapeMeta } from '../../components/chat/MensagemRodapeMeta'

export type EnvioTextoPendente = {
  tempId: string
  texto: string
  quotedWaMessageId: string | null
  quotedPreview: string | null
  criadoEm: string
  /** Maior id de mensagem conhecido ao enviar — a mensagem gravada terá id maior. */
  maiorIdAntes: number
  estado: 'enviando' | 'falhou'
}

type Props = {
  envio: EnvioTextoPendente
  onTentarDeNovo: () => void
  onDescartar: () => void
}

export function WhatsappMensagemPendente({ envio, onTentarDeNovo, onDescartar }: Props) {
  const falhou = envio.estado === 'falhou'
  return (
    <div className="flex w-full justify-end" data-envio-pendente={envio.tempId}>
      <div className="relative max-w-[85%] space-y-1 sm:max-w-[70%]">
        <div
          className={`rounded-2xl rounded-tr-none px-4 py-2 pr-8 text-sm text-white shadow-sm ${
            falhou ? 'bg-cyan-600/60 ring-1 ring-red-400' : 'bg-cyan-600/80'
          }`}
        >
          {envio.quotedWaMessageId && (
            <div className="mb-2 rounded border-l-4 border-white bg-black/10 p-2 text-xs text-slate-100">
              <p className="text-[10px] font-bold text-white">Mensagem Citada</p>
              <p className="max-w-xs truncate">{envio.quotedPreview || 'Mídia'}</p>
            </div>
          )}
          <p className="whitespace-pre-wrap break-words">{envio.texto}</p>
          <MensagemRodapeMeta
            hora={envio.criadoEm}
            status={falhou ? 'erro' : 'pendente'}
            direcao="outbound"
            variant="claro"
          />
        </div>
        {falhou && (
          <div className="flex items-center justify-end gap-2 text-[11px]">
            <span className="text-red-600 dark:text-red-400">Não enviada</span>
            <button
              type="button"
              onClick={onTentarDeNovo}
              className="cursor-pointer font-semibold text-cyan-700 hover:underline dark:text-cyan-400"
            >
              Tentar de novo
            </button>
            <button
              type="button"
              onClick={onDescartar}
              className="cursor-pointer text-slate-500 hover:underline dark:text-slate-400"
            >
              Descartar
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
