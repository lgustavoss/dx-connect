type Props = {
  ativo: boolean
  labelAtivo?: string
  labelInativo?: string
}

export function BadgeAtivo({ ativo, labelAtivo = 'Ativo', labelInativo = 'Inativo' }: Props) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
        ativo
          ? 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-600/15 dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-600/30'
          : 'bg-slate-100 text-slate-600 ring-1 ring-slate-300/60 dark:bg-slate-800 dark:text-slate-400 dark:ring-slate-600/40'
      }`}
    >
      {ativo ? labelAtivo : labelInativo}
    </span>
  )
}
