import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ApiError, funcionariosRede, redes, empresas, type FuncionariosRede, type Redes, type Empresas } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { SelectComPesquisa } from '../components/ui/SelectComPesquisa'
import { Select } from '../components/ui/Select'
import { Switch } from '../components/ui/Switch'
import { CheckboxField } from '../components/ui/CheckboxField'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { FormSection } from '../components/ui/FormSection'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'

type Tipo = 'socio' | 'supervisor' | 'colaborador'
type Escopo = FuncionariosRede.EscopoEmpresas

function redePadraoRecente(list: Redes.Rede[]) {
  const sorted = [...list].sort((a, b) => (Date.parse(b.created_at ?? '') || 0) - (Date.parse(a.created_at ?? '') || 0))
  return sorted[0]?.id ?? ''
}

export function FuncionarioRedeForm() {
  const { id } = useParams<{ id?: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/funcionarios-rede')

  const funcionarioId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [funcionarioInexistente, setFuncionarioInexistente] = useState<{ detalhe?: string } | null>(null)

  const [redesList, setRedesList] = useState<Redes.Rede[]>([])
  const [empresasList, setEmpresasList] = useState<Empresas.Empresa[]>([])

  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [telefone, setTelefone] = useState('')
  const [tipo, setTipo] = useState<Tipo>('colaborador')
  const [escopoEmpresas, setEscopoEmpresas] = useState<Escopo>('selected')
  const [ativo, setAtivo] = useState(true)
  const [redeId, setRedeId] = useState<number | ''>('')
  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [empresaIds, setEmpresaIds] = useState<number[]>([])
  const [senhaPortal, setSenhaPortal] = useState('')
  const [mustChangePassword, setMustChangePassword] = useState(true)
  const [portalHabilitado, setPortalHabilitado] = useState(false)
  const [notificarEmailPortal, setNotificarEmailPortal] = useState(true)

  useEffect(() => {
    coletarTodasPaginas<Redes.Rede>((o, l) => redes.list({ incluir_inativos: true, offset: o, limit: l })).then(
      setRedesList,
    )
    coletarTodasPaginas<Empresas.Empresa>((o, l) =>
      empresas.list<Empresas.Empresa>({ incluir_inativos: true, offset: o, limit: l }),
    ).then(setEmpresasList)
  }, [])

  useEffect(() => {
    if (isEdit) return
    if (redeId !== '' || redesList.length === 0) return
    setRedeId(redePadraoRecente(redesList))
  }, [isEdit, redeId, redesList])

  useEffect(() => {
    if (isEdit) return
    const em = searchParams.get('email')?.trim()
    if (em) setEmail(em)
    const rid = searchParams.get('rede_id')
    if (rid && !Number.isNaN(Number(rid))) setRedeId(Number(rid))
    const eid = searchParams.get('empresa_id')
    if (eid && !Number.isNaN(Number(eid))) {
      const n = Number(eid)
      setEmpresaId(n)
      setEmpresaIds([n])
      setEscopoEmpresas('selected')
    }
  }, [isEdit, searchParams])

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(funcionarioId)) {
      setFuncionarioInexistente({ detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setFuncionarioInexistente(null)
    funcionariosRede
      .get(funcionarioId)
      .then((item) => {
        if (cancelled) return
        setNome(item.nome)
        setEmail(item.email || '')
        setTelefone(item.telefone || '')
        setTipo(item.tipo as Tipo)
        setEscopoEmpresas((item.escopo_empresas as Escopo) || (item.tipo === 'socio' ? 'all' : 'selected'))
        setAtivo(item.ativo)
        let r = item.rede_id ?? ('' as number | '')
        if (r === '' && item.tipo === 'colaborador' && item.empresa_id) {
          const em = empresasList.find((e) => e.id === item.empresa_id)
          if (em) r = em.rede_id
        }
        if (r === '' && item.tipo === 'supervisor' && item.empresa_ids?.length) {
          const em = empresasList.find((e) => e.id === item.empresa_ids![0])
          if (em) r = em.rede_id
        }
        setRedeId(r)
        setEmpresaId(item.empresa_id ?? '')
        setEmpresaIds(item.empresa_ids ?? [])
        setPortalHabilitado(Boolean(item.portal_habilitado))
        setMustChangePassword(Boolean(item.must_change_password))
        setNotificarEmailPortal(item.notificar_email_portal !== false)
        setSenhaPortal('')
      })
      .catch((err) => {
        if (!cancelled) {
          if (err instanceof ApiError && err.status === 403) {
            setForbidden(true)
            return
          }
          if (err instanceof ApiError && err.status === 404) {
            setFuncionarioInexistente({})
            return
          }
          const m = interpretarFalhaCarregamento(err, 'Funcionário não encontrado.')
          toast.showWarning([m.titulo, m.detalhe].filter(Boolean).join(' '))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, funcionarioId, toast, empresasList])

  const empresasDaRede = useMemo(
    () => empresasList.filter((em) => em.rede_id === Number(redeId) && (em.ativo || em.id === empresaId || empresaIds.includes(em.id))),
    [empresasList, redeId, empresaId, empresaIds],
  )

  function toggleEmpresa(id: number) {
    setEmpresaIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!redeId) {
      toast.showWarning('Selecione a rede.')
      return
    }
    const rid = Number(redeId)
    const empresasNaRede = empresasList.filter((em) => em.rede_id === rid)
    const escopo = escopoEmpresas
    let ids = [...empresaIds]
    if (escopo === 'selected') {
      if (tipo === 'colaborador' && empresaId) {
        ids = [Number(empresaId)]
      }
      if (!ids.length) {
        toast.showWarning('Marque ao menos uma empresa da rede ou escolha «Todas as empresas».')
        return
      }
      const invalid = ids.some((id) => !empresasNaRede.some((e) => e.id === id))
      if (invalid) {
        toast.showWarning('Todas as empresas selecionadas devem pertencer à rede escolhida.')
        return
      }
    }
    setSaving(true)
    const emailPayload = email.trim() || null
    try {
      let saved: FuncionariosRede.Funcionario
      if (isEdit && !Number.isNaN(funcionarioId)) {
        const payload: FuncionariosRede.Update = {
          nome: nome.trim(),
          email: emailPayload,
          telefone: telefone.replace(/\D/g, '') || null,
          tipo,
          escopo_empresas: escopo,
          ativo,
          rede_id: rid,
          empresa_id: escopo === 'selected' && tipo === 'colaborador' && ids.length === 1 ? ids[0] : undefined,
          empresa_ids: escopo === 'selected' ? ids : [],
          notificar_email_portal: notificarEmailPortal,
          must_change_password: mustChangePassword,
          ...(senhaPortal.trim() ? { senha_portal: senhaPortal.trim() } : {}),
        }
        saved = await funcionariosRede.update(funcionarioId, payload)
        toast.showSuccess('Funcionário atualizado.')
      } else {
        const payload: FuncionariosRede.Create = {
          nome: nome.trim(),
          email: emailPayload,
          telefone: telefone.replace(/\D/g, '') || null,
          tipo,
          escopo_empresas: escopo,
          ativo,
          rede_id: rid,
          empresa_id: escopo === 'selected' && tipo === 'colaborador' && ids.length === 1 ? ids[0] : undefined,
          empresa_ids: escopo === 'selected' ? ids : [],
          must_change_password: mustChangePassword,
          ...(senhaPortal.trim() ? { senha_portal: senhaPortal.trim() } : {}),
        }
        saved = await funcionariosRede.create(payload)
        toast.showSuccess('Funcionário cadastrado.')
      }
      navigate(`/funcionarios-rede/${saved.id}`, { replace: true })
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o funcionário.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="h-9 w-56 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
        <div className="h-72 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-5xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para editar este funcionário."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara="/funcionarios-rede"
          voltarLabel="Voltar para Funcionários"
        />
      </div>
    )
  }

  if (funcionarioInexistente) {
    return (
      <CarregamentoFalhou
        className="mx-auto max-w-5xl space-y-4 pb-10"
        titulo="Funcionário não encontrado."
        detalhe={funcionarioInexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-10">
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={voltarAnterior}
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <span aria-hidden>←</span> Voltar
        </button>
      </div>

      <Card title={isEdit ? 'Editar funcionário' : 'Novo funcionário'}>
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            <FormSection title="Dados do funcionário">
              <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
              <Input
                label="E-mail (opcional)"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <p className="text-xs text-slate-500">
                Usado para identificar remetente em tickets por e-mail. Contactos só WhatsApp podem ficar em branco.
              </p>
              <Input
                label="WhatsApp (opcional)"
                value={telefone}
                onChange={(e) => setTelefone(e.target.value)}
                placeholder="5511999999999"
              />
              <p className="text-xs text-slate-500">
                Número para iniciar conversa pelo hub Contatos. Preferencialmente com DDI (55).
              </p>
              <Select
                label="Tipo"
                value={tipo}
                onChange={(v) => {
                  const t = v as Tipo
                  setTipo(t)
                  setEmpresaId('')
                  setEmpresaIds([])
                  if (t === 'socio') setEscopoEmpresas('all')
                  if (t === 'socio' && !redeId) setRedeId(redePadraoRecente(redesList))
                }}
                options={[
                  { value: 'socio', label: 'Sócio' },
                  { value: 'supervisor', label: 'Supervisor' },
                  { value: 'colaborador', label: 'Colaborador' },
                ]}
              />
              <SelectComPesquisa
                id="funcionario-rede-form"
                label="Rede"
                value={redeId}
                onChange={(id) => {
                  setRedeId(id)
                  setEmpresaId('')
                  setEmpresaIds([])
                }}
                required
                items={redesList.map((r) => ({ id: r.id, label: r.nome, createdAt: r.created_at }))}
                hint="Últimas redes cadastradas. Digite para buscar outras."
              />
            </FormSection>

            <FormSection title="Escopo de empresas">
              <div className="flex flex-col gap-2 sm:flex-row sm:gap-6">
                <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                  <input
                    type="radio"
                    name="escopo-empresas"
                    checked={escopoEmpresas === 'all'}
                    onChange={() => {
                      setEscopoEmpresas('all')
                      setEmpresaId('')
                      setEmpresaIds([])
                    }}
                  />
                  Todas as empresas da rede
                </label>
                <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                  <input
                    type="radio"
                    name="escopo-empresas"
                    checked={escopoEmpresas === 'selected'}
                    onChange={() => setEscopoEmpresas('selected')}
                  />
                  Selecionar empresas
                </label>
              </div>
              {escopoEmpresas === 'selected' && (
                <div className="mt-3">
                  {tipo === 'colaborador' ? (
                    <SelectComPesquisa
                      id="funcionario-empresa-form"
                      label="Empresa desta rede"
                      value={empresaId}
                      onChange={(id) => {
                        setEmpresaId(id)
                        setEmpresaIds(id ? [id] : [])
                      }}
                      required
                      disabled={!redeId}
                      items={empresasDaRede.map((x) => ({ id: x.id, label: x.nome, createdAt: x.created_at }))}
                      hint={!redeId ? 'Selecione a rede primeiro.' : 'Últimas empresas desta rede. Digite para buscar.'}
                    />
                  ) : (
                    <>
                      <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
                        Empresas desta rede
                      </label>
                      {!redeId ? (
                        <p className="text-sm text-slate-500 dark:text-slate-400">Selecione a rede primeiro.</p>
                      ) : empresasDaRede.length === 0 ? (
                        <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma empresa ativa nesta rede.</p>
                      ) : (
                        <div className="flex max-h-44 flex-wrap gap-2 overflow-auto rounded-xl border border-slate-200 bg-slate-50/40 p-3 dark:border-slate-800 dark:bg-slate-800/40">
                          {empresasDaRede.map((e) => (
                            <CheckboxField key={e.id} checked={empresaIds.includes(e.id)} onChange={() => toggleEmpresa(e.id)}>
                              {e.nome}
                            </CheckboxField>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </FormSection>

            <FormSection title="Portal do cliente">
              <p className="text-xs text-slate-500">
                Com e-mail e senha, o funcionário acessa{' '}
                <span className="font-medium text-slate-700 dark:text-slate-200">/portal</span> para abrir e
                acompanhar chamados.
                {isEdit && portalHabilitado ? (
                  <span className="ml-1 text-teal-700 dark:text-teal-400">Portal já habilitado.</span>
                ) : null}
              </p>
              <Input
                label={isEdit ? 'Nova senha do portal (opcional)' : 'Senha do portal (opcional)'}
                type="password"
                value={senhaPortal}
                onChange={(e) => setSenhaPortal(e.target.value)}
                autoComplete="new-password"
                placeholder={email.trim() ? 'Mínimo 8 caracteres' : 'Informe o e-mail primeiro'}
                disabled={!email.trim()}
              />
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
            </FormSection>

            <FormSection title="Situação no sistema">
              <Switch
                bare
                checked={ativo}
                onCheckedChange={setAtivo}
                label="Funcionário ativo"
                showStatusPill
                statusOnText="Ativo"
                statusOffText="Inativo"
              />
            </FormSection>
          </div>

          <div className="sticky bottom-0 -mx-6 mt-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-800 dark:bg-slate-900">
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

