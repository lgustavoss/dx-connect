import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, saasSetores } from '../../api/client'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import { CadastroFormPageShell } from '../../components/ui/CadastroFormPageShell'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { FormSection } from '../../components/ui/FormSection'
import { InlineCadastroFooter } from '../../components/ui/InlineCadastroPanel'
import { Input } from '../../components/ui/Input'
import { Switch } from '../../components/ui/Switch'
import { useToast } from '../../components/ui/Toast'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { SemPermissao } from '../SemPermissao'

export function SaasSetorForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/saas/setores')

  const setorId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)
  const [nome, setNome] = useState('')
  const [ativo, setAtivo] = useState(true)

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(setorId)) {
      setInexistente({ detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    setInexistente(null)
    saasSetores
      .get(setorId)
      .then((row) => {
        if (cancelled) return
        setNome(row.nome)
        setAtivo(row.ativo)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          return
        }
        setInexistente(interpretarFalhaCarregamento(err, 'Setor não encontrado.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, setorId])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!nome.trim()) {
      toast.showError('Informe o nome do setor.')
      return
    }
    setSaving(true)
    try {
      if (isEdit) {
        await saasSetores.update(setorId, { nome: nome.trim(), ativo })
        toast.showSuccess('Setor atualizado.')
      } else {
        await saasSetores.create({ nome: nome.trim() })
        toast.showSuccess('Setor criado.')
      }
      navigate('/saas/setores')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o setor.'))
    } finally {
      setSaving(false)
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Conta exclusiva da equipe SaaS."
        detail="Entre com a conta ops em /login/admin."
        voltarPara="/login/admin"
        voltarLabel="Voltar ao login admin"
      />
    )
  }
  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel SaaS não disponível nesta instância."
        voltarPara="/login/admin"
        voltarLabel="Voltar ao login admin"
      />
    )
  }
  if (inexistente) {
    return (
      <CarregamentoFalhou
        titulo={inexistente.detalhe ? 'Setor não encontrado.' : 'Não foi possível carregar.'}
        detalhe={inexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <form onSubmit={(ev) => void onSubmit(ev)} className="space-y-4">
        <FormSection
          title={isEdit ? 'Editar setor' : 'Novo setor'}
          description="Cargo da equipe DeskRudder (ex.: Admin, Desenvolvimento, Comercial). Sem ordem fixa — a lista é alfabética."
        >
          {loading ? (
            <p className="text-sm text-slate-500">Carregando…</p>
          ) : (
            <div className="space-y-4">
              <Input label="Nome" value={nome} onChange={(ev) => setNome(ev.target.value)} required />
              {isEdit ? (
                <Switch
                  checked={ativo}
                  onCheckedChange={setAtivo}
                  label="Setor ativo"
                  showStatusPill
                  description="Inativos não podem ser vinculados a novos usuários."
                />
              ) : null}
            </div>
          )}
        </FormSection>
        <InlineCadastroFooter
          onCancel={voltarAnterior}
          saving={saving}
          submitLabel={isEdit ? 'Salvar' : 'Criar'}
        />
      </form>
    </CadastroFormPageShell>
  )
}
