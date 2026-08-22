import { useEffect, useState, type ReactNode } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { portalCliente, type PortalCliente } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { usePortalAuth } from '../../contexts/PortalAuthContext'
import { useToast } from '../../components/ui/Toast'
import { Switch } from '../../components/ui/Switch'
import { CheckboxField } from '../../components/ui/CheckboxField'
import {
  PortalPageHeader,
  portalInputClass,
  portalPrimaryBtnClass,
  portalCancelBtnClass,
} from './portalUi'
import { VoltarButton } from '../../components/ui/VoltarButton'

type TipoEquipe = 'colaborador' | 'supervisor'

function PortalField({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-slate-700">{label}</span>
      {children}
    </label>
  )
}

function PortalFormBlock({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section className="space-y-4">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  )
}

export function PortalEquipeForm() {
  const { id } = useParams<{ id?: string }>()
  const isEdit = Boolean(id)
  const funcionarioId = id ? Number(id) : NaN
  const { user } = usePortalAuth()
  const navigate = useNavigate()
  const toast = useToast()

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [editavel, setEditavel] = useState(true)
  const [empresas, setEmpresas] = useState<PortalCliente.Empresa[]>([])

  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [telefone, setTelefone] = useState('')
  const [tipo, setTipo] = useState<TipoEquipe>('colaborador')
  const [ativo, setAtivo] = useState(true)
  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [empresaIds, setEmpresaIds] = useState<number[]>([])
  const [senhaPortal, setSenhaPortal] = useState('')
  const [mustChangePassword, setMustChangePassword] = useState(true)
  const [portalHabilitado, setPortalHabilitado] = useState(false)
  const [notificarEmailPortal, setNotificarEmailPortal] = useState(true)
  const [outroSocio, setOutroSocio] = useState(false)
  const [membroSocio, setMembroSocio] = useState(false)

  useEffect(() => {
    if (user?.tipo !== 'socio') return
    portalCliente.listEquipeEmpresas().then(setEmpresas).catch(() => undefined)
  }, [user?.tipo])

  useEffect(() => {
    if (!isEdit || !Number.isFinite(funcionarioId) || user?.tipo !== 'socio') return
    let cancelled = false
    setLoading(true)
    portalCliente
      .getEquipeFuncionario(funcionarioId)
      .then((item) => {
        if (cancelled) return
        setNome(item.nome)
        setEmail(item.email || '')
        setTelefone(item.telefone || '')
        if (item.tipo === 'colaborador' || item.tipo === 'supervisor') {
          setTipo(item.tipo)
        }
        setMembroSocio(item.tipo === 'socio')
        setAtivo(item.ativo)
        setEmpresaId(item.empresa_id ?? '')
        setEmpresaIds(item.empresa_ids ?? [])
        setPortalHabilitado(item.portal_habilitado)
        setMustChangePassword(item.must_change_password !== false)
        setNotificarEmailPortal(item.notificar_email_portal !== false)
        setEditavel(item.editavel)
        setOutroSocio(item.tipo === 'socio' && item.id !== user?.id)
      })
      .catch((err) => {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Membro não encontrado.'))
          navigate('/portal/equipe', { replace: true })
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [funcionarioId, isEdit, navigate, toast, user?.id, user?.tipo])

  if (user && user.tipo !== 'socio') {
    return <Navigate to="/portal/tickets" replace />
  }

  if (loading) {
    return <div className="h-64 animate-pulse rounded-xl bg-slate-200/60" />
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (outroSocio) {
      try {
        setSaving(true)
        await portalCliente.updateEquipeFuncionario(funcionarioId, {
          ativo,
          ...(senhaPortal.trim() ? { senha_portal: senhaPortal.trim() } : {}),
          must_change_password: mustChangePassword,
          notificar_email_portal: notificarEmailPortal,
        })
        toast.showSuccess('Sócio atualizado.')
        navigate('/portal/equipe')
      } catch (err) {
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
      } finally {
        setSaving(false)
      }
      return
    }

    if (membroSocio) {
      if (!nome.trim() || !email.trim()) {
        toast.showWarning('Informe nome e e-mail.')
        return
      }
      if (senhaPortal.trim() && senhaPortal.trim().length < 8) {
        toast.showWarning('A senha do portal deve ter ao menos 8 caracteres.')
        return
      }
      setSaving(true)
      try {
        await portalCliente.updateEquipeFuncionario(funcionarioId, {
          nome: nome.trim(),
          email: email.trim(),
          telefone: telefone.trim() || null,
          ativo,
          ...(senhaPortal.trim() ? { senha_portal: senhaPortal.trim() } : {}),
          must_change_password: mustChangePassword,
          notificar_email_portal: notificarEmailPortal,
        })
        toast.showSuccess('Seus dados foram atualizados.')
        navigate('/portal/equipe')
      } catch (err) {
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
      } finally {
        setSaving(false)
      }
      return
    }

    if (!nome.trim() || !email.trim()) {
      toast.showWarning('Informe nome e e-mail.')
      return
    }
    if (tipo === 'colaborador' && !empresaId) {
      toast.showWarning('Selecione a empresa do colaborador.')
      return
    }
    if (tipo === 'supervisor' && !empresaIds.length) {
      toast.showWarning('Marque ao menos uma empresa para o supervisor.')
      return
    }
    if (senhaPortal.trim() && senhaPortal.trim().length < 8) {
      toast.showWarning('A senha do portal deve ter ao menos 8 caracteres.')
      return
    }

    setSaving(true)
    try {
      const senhaPayload = senhaPortal.trim() ? { senha_portal: senhaPortal.trim() } : {}
      if (isEdit) {
        await portalCliente.updateEquipeFuncionario(funcionarioId, {
          nome: nome.trim(),
          email: email.trim(),
          telefone: telefone.trim() || null,
          tipo,
          ativo,
          empresa_id: tipo === 'colaborador' ? Number(empresaId) : undefined,
          empresa_ids: tipo === 'supervisor' ? empresaIds : undefined,
          must_change_password: mustChangePassword,
          notificar_email_portal: notificarEmailPortal,
          ...senhaPayload,
        })
        toast.showSuccess('Membro atualizado.')
      } else {
        await portalCliente.createEquipeFuncionario({
          nome: nome.trim(),
          email: email.trim(),
          telefone: telefone.trim() || null,
          tipo,
          ativo,
          empresa_id: tipo === 'colaborador' ? Number(empresaId) : undefined,
          empresa_ids: tipo === 'supervisor' ? empresaIds : [],
          must_change_password: mustChangePassword,
          ...senhaPayload,
        })
        toast.showSuccess('Membro cadastrado.')
      }
      navigate('/portal/equipe')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setSaving(false)
    }
  }

  function toggleEmpresa(eid: number) {
    setEmpresaIds((prev) => (prev.includes(eid) ? prev.filter((x) => x !== eid) : [...prev, eid]))
  }

  const disabledDados = !editavel || outroSocio

  return (
    <div className="space-y-6">
      <div>
        <VoltarButton onClick={() => navigate('/portal/equipe')} label="Voltar à equipe" />
        <div className="mt-2">
          <PortalPageHeader
            title={isEdit ? 'Editar membro' : 'Novo membro da equipe'}
            subtitle={
              outroSocio
                ? 'Outro sócio: só é possível alterar situação, senha do portal e notificações.'
                : membroSocio
                  ? 'Sócio: acesso a toda a rede (sem vínculo por empresa).'
                  : undefined
            }
          />
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-8 rounded-xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-6"
      >
        <PortalFormBlock title="Dados">
          <PortalField label="Nome *">
            <input
              className={portalInputClass}
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              required
              disabled={disabledDados}
            />
          </PortalField>
          <PortalField label="E-mail *">
            <input
              type="email"
              className={portalInputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={disabledDados}
            />
          </PortalField>
          <PortalField label="Telefone">
            <input
              className={portalInputClass}
              value={telefone}
              onChange={(e) => setTelefone(e.target.value)}
              disabled={disabledDados}
            />
          </PortalField>
          {!outroSocio && !membroSocio && editavel ? (
            <PortalField label="Função">
              <select
                className={portalInputClass}
                value={tipo}
                onChange={(e) => {
                  setTipo(e.target.value as TipoEquipe)
                  setEmpresaId('')
                  setEmpresaIds([])
                }}
              >
                <option value="colaborador">Colaborador</option>
                <option value="supervisor">Supervisor</option>
              </select>
            </PortalField>
          ) : null}
        </PortalFormBlock>

        {!outroSocio && !membroSocio && editavel ? (
          <PortalFormBlock title="Empresas">
            {tipo === 'colaborador' ? (
              <PortalField label="Empresa *">
                <select
                  className={portalInputClass}
                  value={empresaId === '' ? '' : String(empresaId)}
                  onChange={(e) => setEmpresaId(e.target.value ? Number(e.target.value) : '')}
                  required
                >
                  <option value="">Selecione</option>
                  {empresas.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.nome}
                    </option>
                  ))}
                </select>
              </PortalField>
            ) : (
              <div className="flex max-h-44 flex-wrap gap-2 overflow-auto rounded-lg border border-slate-200 bg-slate-50/50 p-3">
                {empresas.map((e) => (
                  <CheckboxField key={e.id} checked={empresaIds.includes(e.id)} onChange={() => toggleEmpresa(e.id)}>
                    {e.nome}
                  </CheckboxField>
                ))}
              </div>
            )}
          </PortalFormBlock>
        ) : null}

        <PortalFormBlock title="Portal do cliente">
          <p className="text-sm text-slate-500">
            Com e-mail e senha, o membro acessa <span className="font-medium text-slate-700">/portal</span>.
            {portalHabilitado ? (
              <span className="ml-1 font-medium text-emerald-700">Portal já habilitado.</span>
            ) : null}
          </p>
          <PortalField label={isEdit ? 'Nova senha do portal (opcional)' : 'Senha do portal (opcional)'}>
            <input
              type="password"
              className={portalInputClass}
              value={senhaPortal}
              onChange={(e) => setSenhaPortal(e.target.value)}
              autoComplete="new-password"
              disabled={!email.trim()}
            />
          </PortalField>
          <Switch
            bare
            checked={mustChangePassword}
            onCheckedChange={setMustChangePassword}
            label="Exigir troca de senha no primeiro acesso"
            showStatusPill
            statusOnText="Sim"
            statusOffText="Não"
          />
          {isEdit ? (
            <Switch
              bare
              checked={notificarEmailPortal}
              onCheckedChange={setNotificarEmailPortal}
              label="Notificar por e-mail sobre respostas nos chamados"
              showStatusPill
              statusOnText="Sim"
              statusOffText="Não"
            />
          ) : null}
        </PortalFormBlock>

        <PortalFormBlock title="Situação">
          <Switch
            bare
            checked={ativo}
            onCheckedChange={setAtivo}
            label="Membro ativo"
            showStatusPill
            statusOnText="Ativo"
            statusOffText="Inativo"
          />
        </PortalFormBlock>

        <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-5 sm:flex-row sm:justify-end">
          <button type="button" className={portalCancelBtnClass} onClick={() => navigate('/portal/equipe')}>
            Cancelar
          </button>
          <button
            type="submit"
            className={portalPrimaryBtnClass}
            style={{ backgroundColor: 'var(--portal-primary)' }}
            disabled={saving}
          >
            {saving ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </form>
    </div>
  )
}
