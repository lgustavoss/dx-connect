import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { redes, type Redes } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { FormSection } from '../components/ui/FormSection'

export function RedeForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/redes')

  const redeId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [nome, setNome] = useState('')
  const [loginRetaguarda, setLoginRetaguarda] = useState('')
  const [ativo, setAtivo] = useState(true)

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(redeId)) {
      toast.showWarning('Rede inválida.')
      voltarAnterior()
      return
    }
    let cancelled = false
    setLoading(true)
    redes
      .get(redeId)
      .then((r) => {
        if (cancelled) return
        setNome(r.nome)
        setLoginRetaguarda(r.login_retaguarda ?? '')
        setAtivo(r.ativo)
      })
      .catch(() => {
        if (!cancelled) {
          toast.showWarning('Rede não encontrada.')
          voltarAnterior()
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, redeId, toast, voltarAnterior])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const n = nome.trim()
    if (!n) {
      toast.showWarning('Informe o nome da rede.')
      return
    }
    const lr = loginRetaguarda.trim() || null
    setSaving(true)
    try {
      let r: Redes.Rede
      if (isEdit && !Number.isNaN(redeId)) {
        r = await redes.update(redeId, { nome: n, login_retaguarda: lr, ativo })
        toast.showSuccess('Rede atualizada.')
      } else {
        r = await redes.create({ nome: n, login_retaguarda: lr, ativo })
        toast.showSuccess('Rede cadastrada.')
      }
      navigate(`/redes/${r.id}`, { replace: true })
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Erro')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="h-9 w-56 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
        <div className="h-64 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 pb-10">
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={voltarAnterior}
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <span aria-hidden>←</span> Voltar
        </button>
      </div>

      <Card title={isEdit ? 'Editar rede' : 'Nova rede'}>
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            <FormSection title="Dados da rede">
              <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
              <Input
                label="Login do retaguarda"
                value={loginRetaguarda}
                onChange={(e) => setLoginRetaguarda(e.target.value)}
                placeholder="Ex.: duplex_admin"
              />
            </FormSection>

            <FormSection title="Situação no sistema">
              <Switch
                bare
                checked={ativo}
                onCheckedChange={setAtivo}
                label="Rede ativa"
                description="Inativos ficam ocultos nas listagens padrão."
                showStatusPill
                statusOnText="Ativo"
                statusOffText="Inativo"
              />
            </FormSection>
          </div>

          <div className="sticky bottom-0 -mx-6 mt-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button type="button" variant="secondary" onClick={voltarAnterior} className="w-full sm:w-auto">
                Cancelar
              </Button>
              <Button type="submit" loading={saving} className="w-full sm:w-auto">
                Salvar
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  )
}

