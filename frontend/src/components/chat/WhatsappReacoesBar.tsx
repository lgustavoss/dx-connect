import type { WhatsappChats } from '../../api/client'

type Props = {
  reacoes: WhatsappChats.ReacaoMensagem[]
  onReagir?: (emoji: string) => void
  /** false = só chips (cliente reagiu; atendente sem permissão) */
  podeReagir?: boolean
  alinhamento?: 'start' | 'end'
}

/** Chips de reações já aplicadas (#630 lote 2). Picker fica no menu da seta (#947). */
export function WhatsappReacoesBar({
  reacoes,
  onReagir,
  podeReagir = false,
  alinhamento = 'end',
}: Props) {
  if (reacoes.length === 0) return null

  const alignEnd = alinhamento === 'end'

  return (
    <div
      className={`relative z-[1] mt-1 flex flex-wrap gap-1 ${
        alignEnd ? 'justify-end' : 'justify-start'
      }`}
    >
      {reacoes.map((r) => (
        <button
          key={r.emoji}
          type="button"
          disabled={!podeReagir || !onReagir}
          onClick={() => onReagir?.(r.emoji)}
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] shadow-sm transition ${
            r.reagiu_eu
              ? 'border-cyan-400/60 bg-white text-slate-800 dark:bg-slate-800 dark:text-slate-100'
              : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:hover:bg-white dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200'
          } ${!podeReagir ? 'cursor-default' : ''}`}
          title={
            r.reagiu_eu ? 'Remover sua reação' : podeReagir ? 'Reagir' : r.tem_cliente ? 'Cliente' : 'Reação'
          }
        >
          <span>{r.emoji}</span>
          <span className="font-medium tabular-nums">{r.count}</span>
        </button>
      ))}
    </div>
  )
}
