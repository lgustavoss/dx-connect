import { Link } from 'react-router-dom'

export function AcessoNegado({
  title = 'Área exclusiva para administradores',
  detail = 'Você está autenticado, mas esta página só pode ser acessada por usuários com perfil de administrador. Se precisar de acesso, solicite ao gestor da equipe.',
}: {
  title?: string
  detail?: string
} = {}) {
  return (
    <div className="mx-auto max-w-lg rounded-2xl border border-amber-200/80 bg-amber-50/90 p-6 text-amber-950 shadow-sm dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100">
      <p className="text-sm font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-300">403 — Acesso restrito</p>
      <h1 className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h1>
      <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{detail}</p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          to="/"
          className="inline-flex rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
        >
          Ir para o início
        </Link>
        <Link
          to="/tickets"
          className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-800 transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
        >
          Ver tickets
        </Link>
      </div>
    </div>
  )
}
