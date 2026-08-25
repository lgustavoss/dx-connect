import { useState } from 'react'
import type { WhatsappChats } from '../../api/client'
import { EMOJIS_REACAO_CHAT_INTERNO } from '../../lib/chatInternoReacoes'

type Props = {
  reacoes: WhatsappChats.ReacaoMensagem[]
  onReagir?: (emoji: string) => void
  /** false = só chips (cliente reagiu; atendente sem permissão) */
  podeReagir?: boolean
  alinhamento?: 'start' | 'end'
  /** Abrir picker a partir do menu da seta (#749). */
  pickerExternoAberto?: boolean
  onPickerExternoClose?: () => void
  /** Menu/edição abertos: não mostrar picker no hover (#S202608-0005 / #947). */
  ocultarPickerHover?: boolean
}

/** Reações no chat WhatsApp com o cliente (#630 lote 2 / #749). */
export function WhatsappReacoesBar({
  reacoes,
  onReagir,
  podeReagir = false,
  alinhamento = 'end',
  pickerExternoAberto = false,
  onPickerExternoClose,
  ocultarPickerHover = false,
}: Props) {
  const temReacoes = reacoes.length > 0
  const alignEnd = alinhamento === 'end'
  const [pickerHoverAberto, setPickerHoverAberto] = useState(false)
  const mostrarPickerMobile = pickerExternoAberto

  return (
    <>
      {podeReagir && onReagir ? (
        <div
          className={`z-20 flex flex-col ${
            alignEnd ? 'items-end' : 'items-start'
          } ${temReacoes || mostrarPickerMobile ? 'relative mt-1' : 'relative'}`}
        >
          {/* Desktop: picker no hover do balão (oculto com menu de ações aberto) */}
          {!ocultarPickerHover ? (
          <div
            className={`pointer-events-none absolute bottom-full z-20 mb-1 hidden flex-col md:flex ${
              alignEnd ? 'right-0 items-end' : 'left-0 items-start'
            }`}
          >
            <div
              className={`opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100 ${
                pickerHoverAberto ? 'pointer-events-auto opacity-100' : ''
              }`}
              onMouseEnter={() => setPickerHoverAberto(true)}
              onMouseLeave={() => setPickerHoverAberto(false)}
            >
              <div className="flex items-center gap-0.5 rounded-full border border-slate-200 bg-white px-1 py-0.5 shadow-md dark:border-slate-600 dark:bg-slate-800">
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
          </div>
          ) : null}
          {mostrarPickerMobile ? (
            <div className="mt-1 flex items-center gap-0.5 rounded-full border border-slate-200 bg-white px-1 py-0.5 shadow-md md:hidden dark:border-slate-600 dark:bg-slate-800">
              {EMOJIS_REACAO_CHAT_INTERNO.map((emoji) => (
                <button
                  key={emoji}
                  type="button"
                  onClick={() => {
                    onReagir(emoji)
                    onPickerExternoClose?.()
                  }}
                  className="min-h-9 min-w-9 rounded-full px-1.5 py-0.5 text-base leading-none hover:bg-slate-100 dark:hover:bg-slate-700"
                  aria-label={`Reagir com ${emoji}`}
                >
                  {emoji}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {temReacoes ? (
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
      ) : null}
    </>
  )
}
