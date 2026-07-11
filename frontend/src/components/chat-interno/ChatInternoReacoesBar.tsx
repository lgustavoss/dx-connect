import type { ChatInterno } from '../../api/client'
import { EMOJIS_REACAO_CHAT_INTERNO } from '../../lib/chatInternoReacoes'

type Props = {
  reacoes: ChatInterno.ReacaoMensagem[]
  onReagir: (emoji: string) => void
  alinhamento?: 'start' | 'end'
}

export function ChatInternoReacoesBar({ reacoes, onReagir, alinhamento = 'end' }: Props) {
  const temReacoes = reacoes.length > 0

  return (
    <>
      <div
        className={`pointer-events-none absolute bottom-[calc(100%-4px)] z-10 flex opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 md:opacity-0 md:group-hover:opacity-100 ${
          alinhamento === 'end' ? 'right-0 justify-end' : 'left-0 justify-start'
        }`}
      >
        <div className="pointer-events-auto flex items-center gap-0.5 rounded-full border border-slate-200 bg-white px-1 py-0.5 shadow-md dark:border-slate-600 dark:bg-slate-800">
          {EMOJIS_REACAO_CHAT_INTERNO.map((emoji) => (
            <button
              key={emoji}
              type="button"
              onClick={() => onReagir(emoji)}
              className="rounded-full px-1.5 py-0.5 text-base leading-none hover:bg-slate-100 dark:hover:bg-slate-700"
              aria-label={`Reagir com ${emoji}`}
            >
              {emoji}
            </button>
          ))}
        </div>
      </div>

      {temReacoes ? (
        <div
          className={`relative z-[1] -mt-2.5 flex flex-wrap gap-1 ${
            alinhamento === 'end' ? 'justify-end' : 'justify-start'
          }`}
        >
          {reacoes.map((r) => (
            <button
              key={r.emoji}
              type="button"
              onClick={() => onReagir(r.emoji)}
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] shadow-sm transition ${
                r.reagiu_eu
                  ? 'border-cyan-400/60 bg-white text-slate-800 dark:bg-slate-800 dark:text-slate-100'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200'
              }`}
              title={r.reagiu_eu ? 'Remover sua reação' : 'Reagir'}
            >
              <span>{r.emoji}</span>
              <span className="font-medium tabular-nums">{r.count}</span>
            </button>
          ))}
        </div>
      ) : null}
    </>
  )
}
