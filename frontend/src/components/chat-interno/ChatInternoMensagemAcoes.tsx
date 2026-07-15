import { useEffect, useState } from 'react'
import type { ChatInterno } from '../../api/client'
import { ConfirmDialog } from '../ui/ConfirmDialog'

const ROTULO_SEM_LEGENDA = /^(📷 Imagem|🎬 Vídeo|🎵 Áudio|📄 Documento)$/

function legendaEditavel(mensagem: ChatInterno.Mensagem): string {
  const tipo = mensagem.tipo_midia || 'texto'
  const corpo = mensagem.corpo.trim()
  if (tipo !== 'texto' && ROTULO_SEM_LEGENDA.test(corpo)) return ''
  return mensagem.corpo
}

type Props = {
  mensagem: ChatInterno.Mensagem
  onEditar: (novoCorpo: string) => Promise<void>
  onApagar: (escopo: 'todos' | 'para_mim') => Promise<void>
  onResponder?: () => void
  alinhamento?: 'start' | 'end'
}

export function ChatInternoMensagemAcoes({
  mensagem,
  onEditar,
  onApagar,
  onResponder,
  alinhamento = 'end',
}: Props) {
  const [editando, setEditando] = useState(false)
  const [texto, setTexto] = useState(() => legendaEditavel(mensagem))
  const [salvando, setSalvando] = useState(false)
  const [confirmarApagar, setConfirmarApagar] = useState(false)
  const [apagando, setApagando] = useState(false)

  const podeEditar = Boolean(mensagem.pode_editar)
  const podeApagarTodos = Boolean(mensagem.pode_apagar_para_todos)
  const podeApagarMim = Boolean(mensagem.pode_apagar_para_mim)
  const podeResponder = Boolean(onResponder) && !mensagem.apagada
  const temAcoes = podeEditar || podeApagarTodos || podeApagarMim || podeResponder

  const tipoMidia = mensagem.tipo_midia || 'texto'
  const editandoTexto = tipoMidia === 'texto'

  useEffect(() => {
    if (!editando) setTexto(legendaEditavel(mensagem))
  }, [mensagem, editando])

  if (mensagem.apagada || !temAcoes) return null

  if (editando && podeEditar) {
    return (
      <div className="mt-1 w-full min-w-[min(100%,18rem)] space-y-2">
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          rows={editandoTexto ? 3 : 2}
          placeholder={editandoTexto ? undefined : 'Legenda da mídia (opcional)'}
          className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        />
        <div className="flex gap-2">
          <button
            type="button"
            disabled={salvando || (editandoTexto && !texto.trim())}
            onClick={() => {
              setSalvando(true)
              void onEditar(editandoTexto ? texto.trim() : texto)
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
              setTexto(legendaEditavel(mensagem))
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

  return (
    <>
      <div
        className={`pointer-events-none absolute top-1 z-10 flex gap-0.5 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 ${
          alinhamento === 'end' ? 'right-1' : 'left-1'
        }`}
      >
        {podeResponder && (
          <button
            type="button"
            onClick={() => onResponder?.()}
            className="pointer-events-auto rounded-full bg-white/95 px-2 py-0.5 text-[10px] font-medium text-slate-600 shadow-sm ring-1 ring-slate-200 hover:bg-white dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-600"
          >
            Responder
          </button>
        )}
        {podeEditar && (
          <button
            type="button"
            onClick={() => {
              setTexto(legendaEditavel(mensagem))
              setEditando(true)
            }}
            className="pointer-events-auto rounded-full bg-white/95 px-2 py-0.5 text-[10px] font-medium text-slate-600 shadow-sm ring-1 ring-slate-200 hover:bg-white dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-600"
          >
            Editar
          </button>
        )}
        {(podeApagarTodos || podeApagarMim) && (
          <button
            type="button"
            onClick={() => setConfirmarApagar(true)}
            className="pointer-events-auto rounded-full bg-white/95 px-2 py-0.5 text-[10px] font-medium text-slate-600 shadow-sm ring-1 ring-slate-200 hover:bg-white dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-600"
          >
            Apagar
          </button>
        )}
      </div>
      <ConfirmDialog
        open={confirmarApagar}
        title="Apagar mensagem?"
        message={
          podeApagarTodos
            ? 'Nos primeiros 5 minutos você pode apagar para todos ou só para você.'
            : 'A mensagem será removida apenas da sua visualização.'
        }
        confirmLabel={podeApagarTodos ? 'Apagar para todos' : 'Apagar para mim'}
        cancelLabel="Cancelar"
        variant="danger"
        loading={apagando}
        hideActions
        onCancel={() => setConfirmarApagar(false)}
        onConfirm={() => {}}
      >
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => setConfirmarApagar(false)}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-500 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
          >
            Cancelar
          </button>
          {podeApagarMim && (
            <button
              type="button"
              disabled={apagando}
              onClick={() => {
                setApagando(true)
                void onApagar('para_mim')
                  .then(() => setConfirmarApagar(false))
                  .finally(() => setApagando(false))
              }}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-500 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
            >
              Apagar para mim
            </button>
          )}
          {podeApagarTodos && (
            <button
              type="button"
              disabled={apagando}
              onClick={() => {
                setApagando(true)
                void onApagar('todos')
                  .then(() => setConfirmarApagar(false))
                  .finally(() => setApagando(false))
              }}
              className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
            >
              Apagar para todos
            </button>
          )}
        </div>
      </ConfirmDialog>
    </>
  )
}
