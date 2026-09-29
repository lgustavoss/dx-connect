import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, atendentes, setores, type Atendentes, type Setores } from '../api/client'
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
import { HorarioSemanaEditor } from '../components/horario/HorarioSemanaEditor'
import { AtendenteLocaisSection } from '../components/AtendenteLocaisSection'
import {
  horarioSemanaFromApi,
  horarioSemanaPadrao,
  validarHorarioSemana,
  type HorarioSemana,
} from '../lib/horarioSemana'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'

type ModoJornada = Atendentes.ModoJornada
type AbaAtendente = 'dados' | 'ponto'

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
  const [aba, setAba] = useState<AbaAtendente>('dados')
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [email, setEmail] = useState('')
  const [nome, setNome] = useState('')
  const [senha, setSenha] = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [role, setRole] = useState<'admin' | 'atendente' | 'comercial'>('atendente')
  const [ativo, setAtivo] = useState(true)
  const [mustChangePassword, setMustChangePassword] = useState(true)
  const [setorIds, setSetorIds] = useState<number[]>([])
  const [modoJornada, setModoJornada] = useState<ModoJornada>('nenhum')
  const [horarioSemana, setHorarioSemana] = useState<HorarioSemana>(() => horarioSemanaPadrao())
  const [escalaHorasTrabalho, setEscalaHorasTrabalho] = useState('12')
  const [escalaHorasFolga, setEscalaHorasFolga] = useState('36')
  const [escalaInicioEm, setEscalaInicioEm] = useState('')
  const [presetEscala, setPresetEscala] = useState('12x36')
  const [horarioEntrada, setHorarioEntrada] = useState('')
  const [horarioSaida, setHorarioSaida] = useState('')
  const [usarLocalEmpresa, setUsarLocalEmpresa] = useState(true)
  const [localEmpresaRaio, setLocalEmpresaRaio] = useState('')

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
        setMustChangePassword(Boolean(a.must_change_password))
        setSetorIds(a.setor_ids ?? [])
        const modo: ModoJornada =
          a.modo_jornada === 'semanal' || a.modo_jornada === 'ciclo' || a.modo_jornada === 'nenhum'
            ? a.modo_jornada
            : a.usa_escala
              ? 'ciclo'
              : 'nenhum'
        setModoJornada(modo)
        setHorarioSemana(horarioSemanaFromApi(a.horario_semana ?? undefined))
        setEscalaHorasTrabalho(a.escala_horas_trabalho != null ? String(a.escala_horas_trabalho) : '12')
        setEscalaHorasFolga(a.escala_horas_folga != null ? String(a.escala_horas_folga) : '36')
        setEscalaInicioEm(a.escala_inicio_em ?? '')
        setHorarioEntrada(a.horario_previsto_entrada ?? '')
        setHorarioSaida(a.horario_previsto_saida ?? '')
        setUsarLocalEmpresa(a.usar_local_empresa !== false)
        setLocalEmpresaRaio(
          a.local_empresa_raio_metros != null ? String(a.local_empresa_raio_metros) : '',
        )
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
          const falha = interpretarFalhaCarregamento(err, 'Atendente não encontrado.')
          setInexistente({ detalhe: falha.detalhe ?? falha.titulo })
          return
        }
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o atendente.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [atendenteId, id, isEdit, toast])

  function toggleSetor(setorId: number) {
    setSetorIds((prev) =>
      prev.includes(setorId) ? prev.filter((x) => x !== setorId) : [...prev, setorId],
    )
  }

  function aplicarPreset(v: string | number) {
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

  function payloadJornada(): Atendentes.Create | Atendentes.Update {
    // Tolerância e teto de HE WhatsApp saíram do cadastro: déficit vai ao banco; WhatsApp exige jornada aberta.
    if (modoJornada === 'nenhum') {
      return {
        modo_jornada: 'nenhum',
        usa_escala: false,
        horario_semana: null,
        escala_horas_trabalho: null,
        escala_horas_folga: null,
        escala_inicio_em: null,
        horario_previsto_entrada: null,
        horario_previsto_saida: null,
        tolerancia_atraso_minutos: 0,
        he_teto_minutos: null,
        he_teto_mensal_minutos: null,
      }
    }
    if (modoJornada === 'semanal') {
      return {
        modo_jornada: 'semanal',
        usa_escala: true,
        horario_semana: horarioSemana,
        escala_horas_trabalho: null,
        escala_horas_folga: null,
        escala_inicio_em: null,
        horario_previsto_entrada: null,
        horario_previsto_saida: null,
        tolerancia_atraso_minutos: 0,
        he_teto_minutos: null,
        he_teto_mensal_minutos: null,
      }
    }
    return {
      modo_jornada: 'ciclo',
      usa_escala: true,
      horario_semana: null,
      escala_horas_trabalho: Math.max(1, Number(escalaHorasTrabalho) || 12),
      escala_horas_folga: Math.max(1, Number(escalaHorasFolga) || 36),
      escala_inicio_em: escalaInicioEm || null,
      horario_previsto_entrada: horarioEntrada.trim() || null,
      horario_previsto_saida: horarioSaida.trim() || null,
      tolerancia_atraso_minutos: 0,
      he_teto_minutos: null,
      he_teto_mensal_minutos: null,
    }
  }

  function payloadLocais(): Pick<
    Atendentes.Update,
    'usar_local_empresa' | 'local_empresa_raio_metros'
  > {
    const raioRaw = localEmpresaRaio.trim()
    return {
      usar_local_empresa: usarLocalEmpresa,
      local_empresa_raio_metros: raioRaw ? Math.max(10, Number(raioRaw) || 200) : null,
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (modoJornada === 'semanal') {
      const erroHs = validarHorarioSemana(horarioSemana)
      if (erroHs) {
        toast.showWarning(erroHs)
        setAba('ponto')
        return
      }
    }
    if (modoJornada === 'ciclo' && !escalaInicioEm) {
      toast.showWarning('Informe o início da escala.')
      setAba('ponto')
      return
    }
    setSaving(true)
    try {
      const escala = payloadJornada()
      const locais = payloadLocais()
      if (isEdit && !Number.isNaN(atendenteId)) {
        await atendentes.update(atendenteId, {
          email,
          nome: nome.trim(),
          role,
          ativo,
          must_change_password: mustChangePassword,
          setor_ids: setorIds,
          ...escala,
          ...locais,
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
          must_change_password: mustChangePassword,
          ...escala,
          ...locais,
        })
        toast.showSuccess('Atendente cadastrado.')
        navigate(`/atendentes/${created.id}/editar`, { replace: true })
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

  const abas: { id: AbaAtendente; label: string }[] = [
    { id: 'dados', label: 'Dados' },
    { id: 'ponto', label: 'Ponto' },
  ]

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <Card title={isEdit ? 'Editar atendente' : 'Novo atendente'}>
        <form onSubmit={handleSubmit}>
          <div className="mb-5 flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800">
            {abas.map((t) => (
              <button
                key={t.id}
                type="button"
                aria-current={aba === t.id ? 'page' : undefined}
                onClick={() => setAba(t.id)}
                className={`px-4 py-2.5 text-sm font-medium transition ${
                  aba === t.id
                    ? 'border-b-2 border-cyan-600 text-cyan-800 dark:border-cyan-400 dark:text-cyan-200'
                    : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="space-y-6">
            {aba === 'dados' ? (
              <>
                <FormSection title="Identificação">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input
                      label="Nome"
                      value={nome}
                      onChange={(e) => setNome(e.target.value)}
                      required
                    />
                    <Input
                      label="E-mail"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
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
                          {mostrarSenha ? (
                            <IconEyeOff ariaHidden={false} />
                          ) : (
                            <IconEye ariaHidden={false} />
                          )}
                        </button>
                      }
                    />
                    <Select
                      label="Perfil"
                      value={role}
                      onChange={(v) =>
                        setRole(
                          v === 'admin' ? 'admin' : v === 'comercial' ? 'comercial' : 'atendente',
                        )
                      }
                      options={[
                        { value: 'atendente', label: 'Atendente' },
                        { value: 'comercial', label: 'Comercial' },
                        { value: 'admin', label: 'Administrador' },
                      ]}
                    />
                  </div>
                </FormSection>

                <FormSection title="Setores">
                  {role === 'admin' && (
                    <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
                      Opcional, mas recomendado: vincule administradores a setores para poderem ser
                      responsáveis em tickets do setor.
                    </p>
                  )}
                  <div className="max-h-44 overflow-auto rounded-lg border border-slate-200 p-3 dark:border-slate-800/80">
                    <div className="flex flex-wrap gap-2">
                      {setoresList.map((s) => (
                        <CheckboxField
                          key={s.id}
                          checked={setorIds.includes(s.id)}
                          onChange={() => toggleSetor(s.id)}
                        >
                          {s.nome}
                        </CheckboxField>
                      ))}
                    </div>
                  </div>
                </FormSection>

                <FormSection title="Situação e acesso">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Switch
                      tight
                      checked={ativo}
                      onCheckedChange={setAtivo}
                      label="Atendente ativo"
                      description="Inativos não acessam o sistema."
                      showStatusPill
                      statusOnText="Ativo"
                      statusOffText="Inativo"
                      className="w-full"
                    />
                    <Switch
                      tight
                      checked={mustChangePassword}
                      onCheckedChange={setMustChangePassword}
                      label="Exigir troca de senha no próximo login"
                      description={
                        isEdit
                          ? 'Se ligar (ou definir nova senha), a pessoa só usa o sistema após trocar a senha.'
                          : 'Recomendado para senha provisória definida por você.'
                      }
                      showStatusPill
                      statusOnText="Sim"
                      statusOffText="Não"
                      className="w-full"
                    />
                  </div>
                </FormSection>
              </>
            ) : null}

            {aba === 'ponto' ? (
              <>
                <FormSection
                  title="Jornada de trabalho"
                  description="Define os dias esperados no calendário e no banco de horas. Déficit parcial e falta são tratados no módulo Ponto — sem tolerância nem liberação de HE por aqui."
                >
                  <Select
                    label="Modo de jornada"
                    value={modoJornada}
                    onChange={(v) => setModoJornada(String(v) as ModoJornada)}
                    options={[
                      { value: 'nenhum', label: 'Nenhum (sem falta nem avisos de horário)' },
                      { value: 'semanal', label: 'Escala semanal (dias da semana)' },
                      { value: 'ciclo', label: 'Escala ciclo (ex.: 12×36)' },
                    ]}
                  />
                  {modoJornada === 'semanal' && (
                    <div className="mt-4">
                      <HorarioSemanaEditor value={horarioSemana} onChange={setHorarioSemana} />
                    </div>
                  )}
                  {modoJornada === 'ciclo' && (
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
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
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
                        <Input
                          label="Início da escala"
                          type="date"
                          value={escalaInicioEm}
                          onChange={(e) => setEscalaInicioEm(e.target.value)}
                          required
                        />
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
                      </div>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Ciclo contínuo a partir da data de início. Entrada/saída previstas orientam o
                        calendário; o ajuste fino de tempo vai para o banco de horas.
                      </p>
                    </div>
                  )}
                </FormSection>

                {isEdit && !Number.isNaN(atendenteId) ? (
                  <FormSection
                    title="Locais de trabalho"
                    description="Usados na geolocalização do ponto (política definida em Ponto da equipe → Configurações)."
                  >
                    <AtendenteLocaisSection
                      atendenteId={atendenteId}
                      usarLocalEmpresa={usarLocalEmpresa}
                      localEmpresaRaio={localEmpresaRaio}
                      onUsarLocalEmpresaChange={setUsarLocalEmpresa}
                      onLocalEmpresaRaioChange={setLocalEmpresaRaio}
                    />
                  </FormSection>
                ) : (
                  <FormSection title="Locais de trabalho">
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Salve o atendente na aba Dados para configurar o local da empresa e locais
                      extras (mapa e raio).
                    </p>
                  </FormSection>
                )}
              </>
            ) : null}
          </div>
          <InlineCadastroFooter onCancel={voltarAnterior} saving={saving} />
        </form>
      </Card>
    </CadastroFormPageShell>
  )
}
