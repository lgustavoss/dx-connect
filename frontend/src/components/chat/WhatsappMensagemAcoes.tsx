import { useEffect, useRef, useState } from 'react'
import type { WhatsappChats } from '../../api/client'
import { EMOJIS_REACAO_CHAT_INTERNO } from '../../lib/chatInternoReacoes'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { TEXTAREA_FIELD_CLASS } from '../ui/Input'

/** Remove prefixo `[ Setor - Nome ]:` gravado no corpo (#628 / #630). */
export function corpoWhatsappSemPrefixo(corpo: string | null | undefined): string {
  const t = (corpo || '').trim()
  return t.replace(/^\[\s*[^\]]+\s*\]:\s*\n?/, '').trim()
}

type Props = {
  mensagem: WhatsappChats.Mensagem
  onEditar?: (novoCorpo: string) => Promise<void>
  onApagar?: () => Promise<void>
  /** Escolher emoji de reação (#947 / #S202608-0005). */
  onReagir?: (emoji: string) => void
  podeReagir?: boolean
  /** Balão claro (inbound) — seta escura. */
  tomClaro?: boolean
}

/** Menu de ações no canto do balão (editar / apagar / reagir) — #630 / #749. */
export function WhatsappMensagemAcoes({
  mensagem,
  onEditar,
  onApagar,
  onReagir,
  podeReagir = false,
  tomClaro = false,
}: Props) {
  const [editando, setEditando] = useState(false)
  const [texto, setTexto] = useState(() => corpoWhatsappSemPrefixo(mensagem.corpo))
  const [salvando, setSalvando] = useState(false)
  const [menuAberto, setMenuAberto] = useState(false)
  const [reagirAberto, setReagirAberto] = useState(false)
  const [confirmarApagar, setConfirmarApagar] = useState(false)
  const [apagando, setApagando] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  const podeEditar = Boolean(mensagem.pode_editar && onEditar)
  const podeApagarTodos = Boolean(mensagem.pode_apagar_para_todos && onApagar)
  const temAcoes = podeEditar || podeApagarTodos || (podeReagir && Boolean(onReagir))

  useEffect(() => {
    if (!editando) setTexto(corpoWhatsappSemPrefixo(mensagem.corpo))
  }, [mensagem, editando])

  useEffect(() => {
    if (!menuAberto) setReagirAberto(false)
  }, [menuAberto])

  useEffect(() => {
    if (!menuAberto) return
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setMenuAberto(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [menuAberto])

  if (mensagem.apagada || !temAcoes) return null

  const itemClass =
    'block w-full px-3 py-1.5 text-left text-xs font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-100 dark:hover:bg-slate-700'

  function escolherEmoji(emoji: string) {
    onReagir?.(emoji)
    setReagirAberto(false)
    setMenuAberto(false)
  }

  return (
    <>
      <div
        ref={rootRef}
        data-msg-acoes
        className="absolute top-1 right-1 z-20"
        onClick={(e) => e.stopPropagation()}
        onDoubleClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          aria-label="Ações da mensagem"
          aria-expanded={menuAberto}
          aria-haspopup="menu"
          title="Ações"
          className={`flex h-8 w-8 items-center justify-center rounded-full transition-opacity md:h-6 md:w-6 ${
            tomClaro
              ? menuAberto
                ? 'bg-slate-200/80 text-slate-700 opacity-100 dark:bg-slate-700 dark:text-slate-100'
                : 'bg-slate-100/80 text-slate-500 opacity-100 hover:bg-slate-200 md:opacity-0 md:group-hover/bubble:opacity-100 md:group-focus-within/bubble:opacity-100 dark:bg-slate-700/80 dark:text-slate-200'
              : menuAberto
                ? 'bg-black/30 text-white opacity-100'
                : 'bg-black/15 text-white opacity-100 hover:bg-black/25 md:opacity-0 md:group-hover/bubble:opacity-100 md:group-focus-within/bubble:opacity-100'
          }`}
          onClick={() => setMenuAberto((o) => !o)}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        {menuAberto && !editando && (
          <div
            role="menu"
            className="absolute right-0 top-full z-30 mt-1 min-w-[8rem] overflow-visible rounded-lg bg-white py-1 shadow-lg ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-600"
          >
            {podeReagir && onReagir && (
              <div
                className="relative"
                onMouseEnter={() => setReagirAberto(true)}
                onMouseLeave={() => setReagirAberto(false)}
              >
                <button
                  type="button"
                  role="menuitem"
                  aria-expanded={reagirAberto}
                  aria-haspopup="true"
                  className={`${itemClass} flex items-center justify-between gap-2`}
                  onClick={() => setReagirAberto((o) => !o)}
                >
                  <span>Reagir</span>
                  <span className="text-[10px] text-slate-400" aria-hidden>
                    ▸
                  </span>
                </button>
                {reagirAberto && (
                  <div
                    role="group"
                    aria-label="Escolher reação"
                    className="absolute right-full top-0 z-40 mr-1 flex items-center gap-0.5 rounded-lg border border-slate-200 bg-white px-1 py-0.5 shadow-lg dark:border-slate-600 dark:bg-slate-800"
                  >
                    {EMOJIS_REACAO_CHAT_INTERNO.map((emoji) => (
                      <button
                        key={emoji}
                        type="button"
                        onClick={() => escolherEmoji(emoji)}
                        className="min-h-9 min-w-9 rounded-full px-1.5 py-0.5 text-base leading-none hover:bg-slate-100 md:min-h-0 md:min-w-0 dark:hover:bg-slate-700"
                        aria-label={`Reagir com ${emoji}`}
                      >
                        {emoji}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {podeEditar && onEditar && (
              <button
                type="button"
                role="menuitem"
                className={itemClass}
                onClick={() => {
                  setMenuAberto(false)
                  setTexto(corpoWhatsappSemPrefixo(mensagem.corpo))
                  setEditando(true)
                }}
              >
                Editar
              </button>
            )}
            {podeApagarTodos && onApagar && (
              <button
                type="button"
                role="menuitem"
                className={`${itemClass} text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40`}
                onClick={() => {
                  setMenuAberto(false)
                  setConfirmarApagar(true)
                }}
              >
                Apagar
              </button>
            )}
          </div>
        )}
      </div>

      {editando && podeEditar && onEditar && (
        <div
          className="relative z-10 mt-2 w-full min-w-[min(100%,18rem)] space-y-2 rounded-lg bg-white/95 p-2 text-slate-900 shadow-md dark:bg-slate-900 dark:text-slate-100"
          onClick={(e) => e.stopPropagation()}
          onDoubleClick={(e) => e.stopPropagation()}
        >
          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            rows={3}
            className={TEXTAREA_FIELD_CLASS}
            autoFocus
          />
          <div className="flex gap-2">
            <button
              type="button"
              disabled={salvando || !texto.trim()}
              onClick={() => {
                setSalvando(true)
                void onEditar(texto.trim())
                  .then(() => setEditando(false))
                  .finally(() => setSalvando(false))
              }}
              className="rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
            >
              Salvar
            </button>
            <button
              type="button"
              onClick={() => {
                setTexto(corpoWhatsappSemPrefixo(mensagem.corpo))
                setEditando(false)
              }}
              className="rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-800 shadow-sm hover:bg-red-100 dark:border-red-800/70 dark:bg-red-950/40 dark:text-red-200 dark:hover:bg-red-950/70"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmarApagar}
        title="Apagar mensagem?"
        message="A mensagem será apagada para todos no WhatsApp do cliente (até 48 h após o envio)."
        confirmLabel="Apagar para todos"
        cancelLabel="Cancelar"
        variant="danger"
        loading={apagando}
        onCancel={() => setConfirmarApagar(false)}
        onConfirm={() => {
          if (!onApagar) return
          setApagando(true)
          void onApagar()
            .then(() => setConfirmarApagar(false))
            .finally(() => setApagando(false))
        }}
      />
    </>
  )
}
