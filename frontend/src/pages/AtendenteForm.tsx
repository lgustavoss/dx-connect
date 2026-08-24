import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, atendentes, setores, type Setores } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { IconEye, IconEyeOff } from '../components/ui/IconEye'
import { Switch } from '../components/ui/Switch'
import { CheckboxField } from '../components/ui/CheckboxField'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { FormSection } from '../components/ui/FormSection'
import { InlineCadastroFooter } from '../components/ui/InlineCadastroPanel'
import { CadastroFormPageShell } from '../components/ui/CadastroFormPageShell'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'

export function AtendenteForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/atendentes')

  const atendenteId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [email, setEmail] = useState('')
  const [nome, setNome] = useState('')
  const [senha, setSenha] = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [role, setRole] = useState<'admin' | 'atendente' | 'comercial'>('atendente')
  const [ativo, setAtivo] = useState(true)
  const [setorIds, setSetorIds] = useState<number[]>([])
  const [usaEscala, setUsaEscala] = useState(false)
  const [escalaHorasTrabalho, setEscalaHorasTrabalho] = useState('12')
  const [escalaHorasFolga, setEscalaHorasFolga] = useState('36')
  const [escalaInicioEm, setEscalaInicioEm] = useState('')
  const [presetEscala, setPresetEscala] = useState('12x36')
  const [horarioEntrada, setHorarioEntrada] = useState('')
  const [horarioSaida, setHorarioSaida] = useState('')
  const [toleranciaAtraso, setToleranciaAtraso] = useState('0')

  useEffect(() => {
    coletarTodasPaginas<Setores.Setor>((o, l) =>
      setores.list({ incluir_inativos: true, offset: o, limit: l }),
    ).then(setSetoresList)
  }, [])

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(atendenteId)) {
      setInexistente({ detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setInexistente(null)
    atendentes
      .get(atendenteId)
      .then((a) => {
        if (cancelled) return
        setEmail(a.email)
        setNome(a.nome)
        setSenha('')
        setMostrarSenha(false)
        setRole((a.role as 'admin' | 'atendente' | 'comercial') || 'atendente')
        setAtivo(a.ativo)
        setSetorIds(a.setor_ids ?? [])
        setUsaEscala(Boolean(a.usa_escala))
        setEscalaHorasTrabalho(a.escala_horas_trabalho != null ? String(a.escala_horas_trabalho) : '12')
        setEscalaHorasFolga(a.escala_horas_folga != null ? String(a.escala_horas_folga) : '36')
        setEscalaInicioEm(a.escala_inicio_em ?? '')
        setHorarioEntrada(a.horario_previsto_entrada ?? '')
        setHorarioSaida(a.horario_previsto_saida ?? '')
        setToleranciaAtraso(String(a.tolerancia_atraso_minutos ?? 0))
        if (a.escala_horas_trabalho === 12 && a.escala_horas_folga === 36) setPresetEscala('12x36')
        else if (a.escala_horas_trabalho === 6 && a.escala_horas_folga === 18) setPresetEscala('6x18')
        else if (a.escala_horas_trabalho === 24 && a.escala_horas_folga === 48) setPresetEscala('24x48')
        else setPresetEscala('custom')
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setInexistente({})
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Atendente não encontrado.')
        toast.showWarning([m.titulo, m.detalhe].filter(Boolean).join(' '))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, atendenteId, toast])

  function toggleSetor(setorId: number) {
    setSetorIds((prev) => (prev.includes(setorId) ? prev.filter((x) => x !== setorId) : [...prev, setorId]))
  }

  function aplicarPreset(v: string | number | '') {
    const s = String(v)
    setPresetEscala(s)
    if (s === '12x36') {
      setEscalaHorasTrabalho('12')
      setEscalaHorasFolga('36')
    } else if (s === '6x18') {
      setEscalaHorasTrabalho('6')
      setEscalaHorasFolga('18')
    } else if (s === '24x48') {
      setEscalaHorasTrabalho('24')
      setEscalaHorasFolga('48')
    }
  }

  function payloadEscala() {
    if (!usaEscala) {
      return {
        usa_escala: false,
        escala_horas_trabalho: null,
        escala_horas_folga: null,
        escala_inicio_em: null,
        horario_previsto_entrada: null,
        horario_previsto_saida: null,
        tolerancia_atraso_minutos: 0,
      }
    }
    return {
      usa_escala: true,
      escala_horas_trabalho: Number(escalaHorasTrabalho) || null,
      escala_horas_folga: Number(escalaHorasFolga) || null,
      escala_inicio_em: escalaInicioEm || null,
      horario_previsto_entrada: horarioEntrada.trim() || null,
      horario_previsto_saida: horarioSaida.trim() || null,
      tolerancia_atraso_minutos: Math.max(0, Number(toleranciaAtraso) || 0),
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const escala = payloadEscala()
      if (isEdit && !Number.isNaN(atendenteId)) {
        await atendentes.update(atendenteId, {
          email,
          nome: nome.trim(),
          role,
          ativo,
          setor_ids: setorIds,
          ...escala,
          ...(senha ? { senha } : {}),
        })
        toast.showSuccess('Atendente atualizado.')
        navigate(`/atendentes/${atendenteId}`, { replace: true })
      } else {
        if (!senha) throw new Error('Senha obrigatória para novo atendente')
        const created = await atendentes.create({
          email,
          nome: nome.trim(),
          senha,
          role,
          setor_ids: setorIds,
          ativo,
          ...escala,
        })
        toast.showSuccess('Atendente cadastrado.')
        navigate(`/atendentes/${created.id}`, { replace: true })
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o atendente.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <CadastroFormPageShell onVoltar={voltarAnterior}>
        <div className="h-72 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </CadastroFormPageShell>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para editar atendentes."
        voltarPara="/atendentes"
        voltarLabel="Voltar para Atendentes"
      />
    )
  }

  if (inexistente) {
    return (
      <CarregamentoFalhou
        className="mx-auto w-full min-w-0 max-w-5xl space-y-4 pb-10"
        titulo="Atendente não encontrado."
        detalhe={inexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <Card title={isEdit ? 'Editar atendente' : 'Novo atendente'}>
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            <FormSection title="Dados do atendente">
              <Input label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
              <Input
                label={isEdit ? 'Nova senha (deixe em branco para manter)' : 'Senha'}
                type={mostrarSenha ? 'text' : 'password'}
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required={!isEdit}
                endAdornment={
                  <button
                    type="button"
                    onClick={() => setMostrarSenha((v) => !v)}
                    className="inline-flex size-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 dark:text-slate-400 dark:hover:bg-white/70 dark:hover:text-slate-200"
                    aria-label={mostrarSenha ? 'Ocultar senha' : 'Mostrar senha'}
                    aria-pressed={mostrarSenha}
                  >
                    {mostrarSenha ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
                  </button>
                }
              />
              <Select
                label="Perfil"
                value={role}
                onChange={(v) =>
                  setRole(v === 'admin' ? 'admin' : v === 'comercial' ? 'comercial' : 'atendente')
                }
                options={[
                  { value: 'atendente', label: 'Atendente' },
                  { value: 'comercial', label: 'Comercial' },
                  { value: 'admin', label: 'Administrador' },
                ]}
              />
            </FormSection>
            <FormSection title="Setores">
              {role === 'admin' && (
                <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
                  Opcional, mas recomendado: vincule administradores a setores para poderem ser responsáveis em tickets do setor.
                </p>
              )}
              <div className="max-h-44 overflow-auto rounded-lg border border-slate-200 p-3 dark:border-slate-800/80">
                <div className="flex flex-wrap gap-2">
                  {setoresList.map((s) => (
                    <CheckboxField key={s.id} checked={setorIds.includes(s.id)} onChange={() => toggleSetor(s.id)}>
                      {s.nome}
                    </CheckboxField>
                  ))}
                </div>
              </div>
            </FormSection>
            <FormSection title="Situação no sistema">
              <Switch
                bare
                checked={ativo}
                onCheckedChange={setAtivo}
                label="Atendente ativo"
                description="Inativos não acessam o sistema."
                showStatusPill
                statusOnText="Ativo"
                statusOffText="Inativo"
              />
            </FormSection>
            <FormSection title="Escala de trabalho">
              <Switch
                bare
                checked={usaEscala}
                onCheckedChange={setUsaEscala}
                label="Usa escala"
                description="Quando ativo, o sistema calcula dias de trabalho e folga a partir do ciclo horas × horas."
                showStatusPill
                statusOnText="Sim"
                statusOffText="Não"
              />
              {usaEscala && (
                <div className="mt-4 space-y-3">
                  <Select
                    label="Preset"
                    value={presetEscala}
                    onChange={aplicarPreset}
                    options={[
                      { value: '12x36', label: '12×36 (comum em plantão)' },
                      { value: '6x18', label: '6×18' },
                      { value: '24x48', label: '24×48' },
                      { value: 'custom', label: 'Personalizado' },
                    ]}
                  />
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input
                      label="Horas trabalhadas"
                      type="number"
                      min={1}
                      value={escalaHorasTrabalho}
                      onChange={(e) => {
                        setPresetEscala('custom')
                        setEscalaHorasTrabalho(e.target.value)
                      }}
                      required
                    />
                    <Input
                      label="Horas de folga"
                      type="number"
                      min={1}
                      value={escalaHorasFolga}
                      onChange={(e) => {
                        setPresetEscala('custom')
                        setEscalaHorasFolga(e.target.value)
                      }}
                      required
                    />
                  </div>
                  <Input
                    label="Início da escala"
                    type="date"
                    value={escalaInicioEm}
                    onChange={(e) => setEscalaInicioEm(e.target.value)}
                    required
                  />
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Input
                      label="Entrada prevista"
                      type="time"
                      value={horarioEntrada}
                      onChange={(e) => setHorarioEntrada(e.target.value)}
                    />
                    <Input
                      label="Saída prevista"
                      type="time"
                      value={horarioSaida}
                      onChange={(e) => setHorarioSaida(e.target.value)}
                    />
                    <Input
                      label="Tolerância atraso (min)"
                      type="number"
                      min={0}
                      max={120}
                      value={toleranciaAtraso}
                      onChange={(e) => setToleranciaAtraso(e.target.value)}
                    />
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Ciclo contínuo a partir desta data (ex.: 12 h de trabalho e 36 h de folga, repetindo). Horário
                    previsto é opcional e sinaliza atraso na conformidade.
                  </p>
                </div>
              )}
            </FormSection>
          </div>
          <InlineCadastroFooter onCancel={voltarAnterior} saving={saving} />
        </form>
      </Card>
    </CadastroFormPageShell>
  )
}
