import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, saasOpsUsuarios } from '../../api/client'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../../components/ui/Button'
import { CadastroFormPageShell } from '../../components/ui/CadastroFormPageShell'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { FormSection } from '../../components/ui/FormSection'
import { InlineCadastroFooter } from '../../components/ui/InlineCadastroPanel'
import { Input } from '../../components/ui/Input'
import { Switch } from '../../components/ui/Switch'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../contexts/AuthContext'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { SemPermissao } from '../SemPermissao'

export function SaasUsuarioForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const voltarAnterior = useVoltarAnterior('/saas/usuarios')

  const usuarioId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null
  const isSelf = isEdit && user?.id === usuarioId

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [ativo, setAtivo] = useState(true)
  const [tokenConfigurado, setTokenConfigurado] = useState(false)
  const [senhaTemporaria, setSenhaTemporaria] = useState<string | null>(null)
  const [confirmarReset, setConfirmarReset] = useState(false)

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(usuarioId)) {
      setInexistente({ detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    setInexistente(null)
    saasOpsUsuarios
      .get(usuarioId)
      .then((row) => {
        if (cancelled) return
        setNome(row.nome)
        setEmail(row.email)
        setAtivo(row.ativo)
        setTokenConfigurado(row.mcp_token_configurado)
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
        setInexistente(interpretarFalhaCarregamento(err, 'Utilizador não encontrado.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, usuarioId])

  async function copiarSenha() {
    if (!senhaTemporaria) return
    try {
      await navigator.clipboard.writeText(senhaTemporaria)
      toast.showSuccess('Senha copiada.')
    } catch {
      toast.showError('Não foi possível copiar. Seleccione a senha e copie manualmente.')
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!nome.trim() || (!isEdit && !email.trim())) {
      toast.showError('Informe nome e e-mail.')
      return
    }
    setSaving(true)
    try {
      if (isEdit) {
        const row = await saasOpsUsuarios.update(usuarioId, { nome: nome.trim(), ativo })
        setAtivo(row.ativo)
        toast.showSuccess('Utilizador actualizado.')
        navigate('/saas/usuarios')
        return
      }
      const row = await saasOpsUsuarios.create({ nome: nome.trim(), email: email.trim() })
      setSenhaTemporaria(row.senha_temporaria)
      setEmail(row.email)
      toast.showSuccess('Utilizador criado. Copie a senha temporária agora.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível guardar o utilizador.'))
    } finally {
      setSaving(false)
    }
  }

  async function resetSenha() {
    setSaving(true)
    try {
      const row = await saasOpsUsuarios.senhaTemporaria(usuarioId)
      setSenhaTemporaria(row.senha_temporaria)
      toast.showSuccess('Senha temporária gerada. Copie agora.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível gerar a senha.'))
    } finally {
      setSaving(false)
      setConfirmarReset(false)
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Conta exclusiva da equipa SaaS."
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
        titulo={inexistente.detalhe ? 'Utilizador não encontrado.' : 'Não foi possível carregar.'}
        detalhe={inexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <form onSubmit={(ev) => void onSubmit(ev)} className="space-y-4">
        <FormSection
          title={isEdit ? 'Editar utilizador' : 'Novo utilizador'}
          description="Esta conta entra no painel DeskRudder (/login/admin). Não é um atendente da instância do cliente."
        >
          {loading ? (
            <p className="text-sm text-slate-500">A carregar…</p>
          ) : (
            <div className="space-y-4">
              <Input label="Nome" value={nome} onChange={(ev) => setNome(ev.target.value)} required />
              <Input
                label="E-mail"
                type="email"
                value={email}
                onChange={(ev) => setEmail(ev.target.value)}
                required
                disabled={isEdit}
              />
              {isEdit ? (
                <Switch
                  checked={ativo}
                  onCheckedChange={setAtivo}
                  label="Conta activa"
                  showStatusPill
                  disabled={isSelf}
                  description={isSelf ? 'Não podes desactivar a tua própria conta.' : undefined}
                />
              ) : null}
              {isEdit ? (
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Token Cursor: {tokenConfigurado ? 'configurado' : 'ainda não gerado'}.
                  {isSelf ? (
                    <>
                      {' '}
                      <Link to="/saas/conta" className="font-medium text-sky-700 underline dark:text-sky-300">
                        Gerar o teu token
                      </Link>
                    </>
                  ) : (
                    ' Cada pessoa gera o token depois de entrar na própria conta.'
                  )}
                </p>
              ) : null}
              {senhaTemporaria ? (
                <div className="space-y-2">
                  <Input label="Senha temporária (copie agora)" readOnly value={senhaTemporaria} />
                  <Button type="button" variant="secondary" onClick={() => void copiarSenha()}>
                    Copiar senha
                  </Button>
                  <p className="text-xs text-slate-500">
                    Login em /login/admin. No primeiro acesso a pessoa define senha nova e, em Conta / Cursor, gera
                    o token.
                  </p>
                </div>
              ) : null}
            </div>
          )}
        </FormSection>
        {senhaTemporaria && !isEdit ? (
          <div className="flex justify-end">
            <Button type="button" onClick={() => navigate('/saas/usuarios')}>
              Ir para a lista
            </Button>
          </div>
        ) : (
          <InlineCadastroFooter
            onCancel={voltarAnterior}
            saving={saving}
            submitLabel={isEdit ? 'Guardar' : 'Criar'}
          />
        )}
      </form>
      {isEdit && !loading ? (
        <div className="mt-4">
          <Button type="button" variant="secondary" loading={saving} onClick={() => setConfirmarReset(true)}>
            Gerar senha temporária
          </Button>
        </div>
      ) : null}
      <ConfirmDialog
        open={confirmarReset}
        title="Gerar senha temporária?"
        message="A sessão actual desta pessoa no painel deixa de valer. Copie a senha nova e envie-lhe."
        confirmLabel="Gerar senha"
        variant="danger"
        loading={saving}
        onConfirm={() => void resetSenha()}
        onCancel={() => setConfirmarReset(false)}
      />
    </CadastroFormPageShell>
  )
}
