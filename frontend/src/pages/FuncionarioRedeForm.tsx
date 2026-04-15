import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { funcionariosRede, redes, empresas, type FuncionariosRede, type Redes, type Empresas } from '../api/client'
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

type Tipo = 'socio' | 'supervisor' | 'colaborador'

function redePadraoRecente(list: Redes.Rede[]) {
  const sorted = [...list].sort((a, b) => (Date.parse(b.created_at ?? '') || 0) - (Date.parse(a.created_at ?? '') || 0))
  return sorted[0]?.id ?? ''
}

export function FuncionarioRedeForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/funcionarios-rede')

  const funcionarioId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)

  const [redesList, setRedesList] = useState<Redes.Rede[]>([])
  const [empresasList, setEmpresasList] = useState<Empresas.Empresa[]>([])

  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [tipo, setTipo] = useState<Tipo>('colaborador')
  const [ativo, setAtivo] = useState(true)
  const [redeId, setRedeId] = useState<number | ''>('')
  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [empresaIds, setEmpresaIds] = useState<number[]>([])

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
    if (!isEdit) return
    if (!id || Number.isNaN(funcionarioId)) {
      toast.showWarning('Funcionário inválido.')
      voltarAnterior()
      return
    }
    let cancelled = false
    setLoading(true)
    funcionariosRede
      .get(funcionarioId)
      .then((item) => {
        if (cancelled) return
        setNome(item.nome)
        setEmail(item.email)
        setTipo(item.tipo as Tipo)
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
      })
      .catch(() => {
        if (!cancelled) {
          toast.showWarning('Funcionário não encontrado.')
          voltarAnterior()
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, funcionarioId, toast, voltarAnterior, empresasList])

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
    if (tipo === 'colaborador') {
      const em = empresasList.find((x) => x.id === empresaId)
      if (!em || em.rede_id !== rid) {
        toast.showWarning('Selecione uma empresa desta rede.')
        return
      }
    }
    if (tipo === 'supervisor') {
      if (!empresaIds.length) {
        toast.showWarning('Marque ao menos uma empresa da rede.')
        return
      }
      const invalid = empresaIds.some((id) => !empresasNaRede.some((e) => e.id === id))
      if (invalid) {
        toast.showWarning('Todas as empresas do supervisor devem ser da rede selecionada.')
        return
      }
    }
    setSaving(true)
    try {
      let saved: FuncionariosRede.Funcionario
      if (isEdit && !Number.isNaN(funcionarioId)) {
        const payload: FuncionariosRede.Update = {
          nome: nome.trim(),
          email,
          tipo,
          ativo,
          rede_id: tipo === 'socio' ? rid : undefined,
          empresa_id: tipo === 'colaborador' ? Number(empresaId) : undefined,
          empresa_ids: tipo === 'supervisor' ? empresaIds : undefined,
        }
        saved = await funcionariosRede.update(funcionarioId, payload)
        toast.showSuccess('Funcionário atualizado.')
      } else {
        const payload: FuncionariosRede.Create = {
          nome: nome.trim(),
          email,
          tipo,
          ativo,
          rede_id: tipo === 'socio' ? rid : undefined,
          empresa_id: tipo === 'colaborador' ? Number(empresaId) : undefined,
          empresa_ids: tipo === 'supervisor' ? empresaIds : undefined,
        }
        saved = await funcionariosRede.create(payload)
        toast.showSuccess('Funcionário cadastrado.')
      }
      navigate(`/funcionarios-rede/${saved.id}`, { replace: true })
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Erro')
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

  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-10">
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
              <Input label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <Select
                label="Tipo"
                value={tipo}
                onChange={(v) => {
                  const t = v as Tipo
                  setTipo(t)
                  setEmpresaId('')
                  setEmpresaIds([])
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

            {tipo !== 'socio' && (
              <FormSection title="Vínculo">
                {tipo === 'colaborador' && (
                  <SelectComPesquisa
                    id="funcionario-empresa-form"
                    label="Empresa desta rede"
                    value={empresaId}
                    onChange={(id) => setEmpresaId(id)}
                    required
                    disabled={!redeId}
                    items={empresasDaRede.map((x) => ({ id: x.id, label: x.nome, createdAt: x.created_at }))}
                    hint={!redeId ? 'Selecione a rede primeiro.' : 'Últimas empresas desta rede. Digite para buscar.'}
                  />
                )}
                {tipo === 'supervisor' && (
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Empresas desta rede</label>
                    {!redeId ? (
                      <p className="text-sm text-slate-500 dark:text-slate-400">Selecione a rede primeiro.</p>
                    ) : empresasDaRede.length === 0 ? (
                      <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma empresa ativa nesta rede.</p>
                    ) : (
                      <div className="flex max-h-44 flex-wrap gap-2 overflow-auto rounded-xl border border-slate-200 bg-slate-50/40 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                        {empresasDaRede.map((e) => (
                          <CheckboxField key={e.id} checked={empresaIds.includes(e.id)} onChange={() => toggleEmpresa(e.id)}>
                            {e.nome}
                          </CheckboxField>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </FormSection>
            )}

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

