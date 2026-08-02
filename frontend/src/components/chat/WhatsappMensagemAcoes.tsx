import { useEffect, useState } from 'react'
import type { WhatsappChats } from '../../api/client'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { TEXTAREA_FIELD_CLASS } from '../ui/Input'

/** Remove prefixo `[ Setor - Nome ]:` gravado no corpo (#628 / #630). */
export function corpoWhatsappSemPrefixo(corpo: string | null | undefined): string {
  const t = (corpo || '').trim()
  return t.replace(/^\[\s*[^\]]+\s*\]:\s*\n?/, '').trim()
}

type Props = {
  mensagem: WhatsappChats.Mensagem
  onEditar: (novoCorpo: string) => Promise<void>
  onApagar: () => Promise<void>
  alinhamento?: 'start' | 'end'
}

/** Editar / apagar para todos no chat WhatsApp (#630 lote 3). */
export function WhatsappMensagemAcoes({
  mensagem,
  onEditar,
  onApagar,
  alinhamento = 'end',
}: Props) {
  const [editando, setEditando] = useState(false)
  const [texto, setTexto] = useState(() => corpoWhatsappSemPrefixo(mensagem.corpo))
  const [salvando, setSalvando] = useState(false)
  const [confirmarApagar, setConfirmarApagar] = useState(false)
  const [apagando, setApagando] = useState(false)

  const podeEditar = Boolean(mensagem.pode_editar)
  const podeApagarTodos = Boolean(mensagem.pode_apagar_para_todos)
  const temAcoes = podeEditar || podeApagarTodos

  useEffect(() => {
    if (!editando) setTexto(corpoWhatsappSemPrefixo(mensagem.corpo))
  }, [mensagem, editando])

  if (mensagem.apagada || !temAcoes) return null

  if (editando && podeEditar) {
    return (
      <div className="mt-1 w-full min-w-[min(100%,18rem)] space-y-2">
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          rows={3}
          className={TEXTAREA_FIELD_CLASS}
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
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-500 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
          >
            Cancelar
          </button>
        </div>
      </div>
    )
  }

  const btnAcaoClass =
    'rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-600 dark:hover:bg-slate-700'

  return (
    <>
      <div
        className={`pointer-events-none absolute bottom-full z-20 flex flex-col ${
          alinhamento === 'end' ? 'right-0 items-end' : 'left-0 items-start'
        }`}
      >
        <div
          className={`flex gap-1 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100 ${
            alinhamento === 'end' ? 'justify-end' : 'justify-start'
          }`}
        >
          {podeEditar && (
            <button
              type="button"
              onClick={() => {
                setTexto(corpoWhatsappSemPrefixo(mensagem.corpo))
                setEditando(true)
              }}
              className={btnAcaoClass}
            >
              Editar
            </button>
          )}
          {podeApagarTodos && (
            <button type="button" onClick={() => setConfirmarApagar(true)} className={btnAcaoClass}>
              Apagar
            </button>
          )}
        </div>
        <div
          className="h-2 w-full min-w-[8rem] group-hover:pointer-events-auto group-focus-within:pointer-events-auto"
          aria-hidden
        />
      </div>
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
          setApagando(true)
          void onApagar()
            .then(() => setConfirmarApagar(false))
            .finally(() => setApagando(false))
        }}
      />
    </>
  )
}
