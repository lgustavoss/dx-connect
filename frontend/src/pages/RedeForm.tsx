import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, redes, type Redes } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { FormSection } from '../components/ui/FormSection'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { VoltarButton } from '../components/ui/VoltarButton'

export function RedeForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/redes')

  const redeId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  /** Ausência da rede: URL inválida (detalhe) ou 404 da API (sem detalhe). */
  const [redeInexistente, setRedeInexistente] = useState<{ detalhe?: string } | null>(null)
  const [nome, setNome] = useState('')
  const [loginRetaguarda, setLoginRetaguarda] = useState('')
  const [ativo, setAtivo] = useState(true)

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(redeId)) {
      setRedeInexistente({ detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setRedeInexistente(null)
    redes
      .get(redeId)
      .then((r) => {
        if (cancelled) return
        setNome(r.nome)
        setLoginRetaguarda(r.login_retaguarda ?? '')
        setAtivo(r.ativo)
      })
      .catch((err) => {
        if (!cancelled) {
          if (err instanceof ApiError && err.status === 403) {
            setForbidden(true)
            return
          }
          if (err instanceof ApiError && err.status === 404) {
            setRedeInexistente({})
            return
          }
          const m = interpretarFalhaCarregamento(err, 'Rede não encontrada.')
          toast.showWarning([m.titulo, m.detalhe].filter(Boolean).join(' '))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, redeId, toast])

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
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a rede.'))
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

  if (forbidden) {
    return (
      <div className="mx-auto max-w-5xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para editar esta rede."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara="/redes"
          voltarLabel="Voltar para Redes"
        />
      </div>
    )
  }

  if (redeInexistente) {
    return (
      <CarregamentoFalhou
        className="mx-auto max-w-5xl space-y-4 pb-10"
        titulo="Rede não encontrada."
        detalhe={redeInexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-10">
      <div className="flex items-center justify-between gap-3">
        <VoltarButton onClick={voltarAnterior} />
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

          <div className="sticky bottom-0 -mx-6 mt-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-800 dark:bg-slate-900">
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button type="button" variant="cancel" onClick={voltarAnterior} className="w-full sm:w-auto">
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

