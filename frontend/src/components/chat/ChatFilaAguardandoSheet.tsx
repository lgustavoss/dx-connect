import { useEffect, useId, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChatListaEspera } from '../../pages/chat/ChatListaEspera'
import { ChatFilaSomToggle } from './ChatFilaSomToggle'

type Props = {
  open: boolean
  onClose: () => void
}

export function ChatFilaAguardandoSheet({ open, onClose }: Props) {
  const navigate = useNavigate()
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    panelRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[100] md:hidden"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-[2px]" aria-hidden />
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="absolute inset-x-0 bottom-0 flex max-h-[min(85vh,32rem)] flex-col rounded-t-2xl bg-white shadow-2xl outline-none dark:bg-slate-950"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
          <div className="flex items-center gap-1">
            <h2 id={titleId} className="text-base font-bold text-slate-900 dark:text-white">
              Aguardando
            </h2>
            <ChatFilaSomToggle size="md" />
          </div>
          <button
            type="button"
            className="rounded-lg px-2 py-1 text-2xl leading-none text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800 dark:hover:text-slate-100"
            onClick={onClose}
            aria-label="Fechar"
          >
            &times;
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ChatListaEspera
            ignorarBusca
            onChatAssumido={(canal, chatId) => {
              navigate(canal === 'portal' ? `/chat/portal/${chatId}` : `/chat/c/${chatId}`)
              onClose()
            }}
            onVerChat={onClose}
          />
        </div>
      </div>
    </div>
  )
}
