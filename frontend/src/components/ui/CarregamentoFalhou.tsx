type Props = {
  titulo: string
  detalhe?: string
  onVoltar: () => void
  voltarLabel?: string
  className?: string
}

export function CarregamentoFalhou({
  titulo,
  detalhe,
  onVoltar,
  voltarLabel = 'Voltar',
  className = 'mx-auto max-w-6xl space-y-4 pb-10',
}: Props) {
  return (
    <div className={className}>
      <p className="text-slate-800 dark:text-slate-100">{titulo}</p>
      {detalhe ? <p className="text-sm text-slate-600 dark:text-slate-400">{detalhe}</p> : null}
      <button
        type="button"
        onClick={onVoltar}
        className="font-medium text-slate-800 underline decoration-slate-400 underline-offset-2 hover:text-slate-950 dark:text-slate-200 dark:hover:text-white"
      >
        {voltarLabel}
      </button>
    </div>
  )
}
