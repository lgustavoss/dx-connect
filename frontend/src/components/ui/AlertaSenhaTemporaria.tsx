/** Faixa do primeiro acesso: a senha atual é temporária e o restante do sistema fica bloqueado. */
export function AlertaSenhaTemporaria() {
  return (
    <div
      role="alert"
      className="mb-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-100"
    >
      Esta senha é temporária. Defina uma nova senha para continuar. O restante do sistema fica
      bloqueado até a troca.
    </div>
  )
}
