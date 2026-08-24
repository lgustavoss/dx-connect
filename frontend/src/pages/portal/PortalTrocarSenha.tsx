import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { portalCliente } from '../../api/client'
import { usePortalAuth } from '../../contexts/PortalAuthContext'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

const fieldClass =
  'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-[0.9375rem] text-slate-900 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/25'

export function PortalTrocarSenha() {
  const { user, applyTokens, refreshUser } = usePortalAuth()
  const [atual, setAtual] = useState('')
  const [nova, setNova] = useState('')
  const [confirma, setConfirma] = useState('')
  const [saving, setSaving] = useState(false)
  const toast = useToast()
  const navigate = useNavigate()

  if (!user) {
    return <Navigate to="/portal/login" replace />
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (nova.length < 8) {
      toast.showError('A nova senha deve ter ao menos 8 caracteres.')
      return
    }
    if (nova !== confirma) {
      toast.showError('A confirmação não confere com a nova senha.')
      return
    }
    setSaving(true)
    try {
      const tokens = await portalCliente.trocarSenha(atual, nova)
      await applyTokens(tokens, true)
      await refreshUser()
      toast.showSuccess('Senha atualizada.')
      navigate('/portal/tickets', { replace: true })
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar a senha.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-md space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Definir nova senha</h1>
        <p className="mt-1 text-sm text-slate-600">
          Por segurança, altere a senha temporária antes de continuar.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Senha atual</span>
          <input
            type="password"
            className={fieldClass}
            value={atual}
            onChange={(e) => setAtual(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Nova senha</span>
          <input
            type="password"
            className={fieldClass}
            value={nova}
            onChange={(e) => setNova(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Confirmar nova senha</span>
          <input
            type="password"
            className={fieldClass}
            value={confirma}
            onChange={(e) => setConfirma(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>
        <Button type="submit" className="w-full" disabled={saving}>
          {saving ? 'Salvando…' : 'Salvar e continuar'}
        </Button>
      </form>
    </div>
  )
}
