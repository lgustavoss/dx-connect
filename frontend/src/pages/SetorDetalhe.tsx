import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, atendentes, setores, type Atendentes, type Setores } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { DetailRow } from '../components/ui/DetailRow'
import { BadgeAtivo } from '../components/ui/BadgeAtivo'
import { SelectComPesquisa } from '../components/ui/SelectComPesquisa'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'

const MODO_OPCOES: { value: Setores.DistribuicaoModo; label: string }[] = [
  { value: 'manual', label: 'Manual — fila sem atribuição automática' },
  { value: 'auto_apos_timeout', label: 'Automático após tempo na fila' },
  { value: 'auto_imediato', label: 'Automático imediato ao entrar na fila' },
]

const ESTRATEGIA_OPCOES: { value: Setores.DistribuicaoEstrategia; label: string }[] = [
  { value: 'round_robin', label: 'Round-robin (revezamento)' },
  { value: 'menor_carga_abertos', label: 'Menor carga (tickets abertos)' },
]

/** Mesmo nome de setor = mesmo “setor lógico” (vários IDs no banco). */
function idsSetoresMesmoNome(setoresList: Setores.Setor[], setorId: number): Set<number> {
  const alvo = setoresList.find((x) => x.id === setorId)
  if (!alvo) return new Set([setorId])
  const nome = alvo.nome.trim().toLowerCase()
  return new Set(setoresList.filter((x) => x.nome.trim().toLowerCase() === nome).map((x) => x.id))
}

export function SetorDetalhe() {
  const { id } = useParams()
  const toast = useToast()
  const navigate = useNavigate()
  const voltarAnterior = useVoltarAnterior('/setores')

  const setorId = Number(id)
  const [loading, setLoading] = useState(true)
  const [setor, setSetor] = useState<Setores.Setor | null>(null)
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [forbidden, setForbidden] = useState(false)
  const [carregamentoFalhou, setCarregamentoFalhou] = useState<{ titulo: string; detalhe?: string } | null>(null)

  const [vinculados, setVinculados] = useState<Atendentes.Atendente[]>([])
  const [todosAtendentes, setTodosAtendentes] = useState<Atendentes.Atendente[]>([])
  const [addingId, setAddingId] = useState<number | ''>('')
  const [saving, setSaving] = useState(false)

  const [distModo, setDistModo] = useState<Setores.DistribuicaoModo>('manual')
  const [distTimeout, setDistTimeout] = useState(30)
  const [distEstrategia, setDistEstrategia] = useState<Setores.DistribuicaoEstrategia>('round_robin')
  const [distElegiveisIds, setDistElegiveisIds] = useState<number[]>([])
  const [distUsarTodos, setDistUsarTodos] = useState(true)
  const [savingDist, setSavingDist] = useState(false)

  const grupoSetorIds = useMemo(() => {
    if (!Number.isFinite(setorId) || setorId <= 0 || setoresList.length === 0) return new Set<number>()
    return idsSetoresMesmoNome(setoresList, setorId)
  }, [setorId, setoresList])

  const vinculadosIds = useMemo(() => new Set(vinculados.map((a) => a.id)), [vinculados])

  const candidatosParaAdicionar = useMemo(() => {
    const ativos = todosAtendentes.filter((a) => a.ativo)
    return ativos.filter((a) => !vinculadosIds.has(a.id)).sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  }, [todosAtendentes, vinculadosIds])

  const atendenteItems = useMemo(
    () =>
      candidatosParaAdicionar.map((a) => ({
        id: a.id,
        label: `${a.nome} — ${a.email}`,
      })),
    [candidatosParaAdicionar],
  )

  const vinculadosOperacionais = useMemo(
    () => vinculados.filter((a) => a.ativo && a.role !== 'admin').sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
    [vinculados],
  )

  function aplicarDistribuicaoDoSetor(s: Setores.Setor) {
    const d = s.distribuicao
    setDistModo(d?.modo ?? 'manual')
    setDistTimeout(d?.timeout_minutos ?? 30)
    setDistEstrategia(d?.estrategia ?? 'round_robin')
    const eleg = d?.atendentes_elegiveis ?? null
    setDistUsarTodos(eleg === null || eleg === undefined)
    setDistElegiveisIds(eleg ?? [])
  }

  async function reload() {
    if (!Number.isFinite(setorId) || setorId <= 0) {
      setSetor(null)
      setVinculados([])
      setCarregamentoFalhou({
        titulo: 'Setor não encontrado.',
        detalhe: 'O identificador na URL é inválido.',
      })
      setLoading(false)
      return
    }
    setLoading(true)
    setForbidden(false)
    setCarregamentoFalhou(null)
    try {
      const [s, setoresAll, todos] = await Promise.all([
        setores.get(setorId),
        coletarTodasPaginas<Setores.Setor>((o, l) => setores.list({ incluir_inativos: true, offset: o, limit: l })),
        coletarTodasPaginas<Atendentes.Atendente>((o, l) =>
          atendentes.list({ incluir_inativos: true, offset: o, limit: l }),
        ),
      ])
      setSetor(s)
      aplicarDistribuicaoDoSetor(s)
      setSetoresList(setoresAll)
      setTodosAtendentes(todos)

      const vinculadosDoGrupo = await atendentes.listPorSetor(setorId, { incluir_inativos: true })
      setVinculados(vinculadosDoGrupo)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true)
        setSetor(null)
        setVinculados([])
        setCarregamentoFalhou(null)
        return
      }
      setSetor(null)
      setVinculados([])
      setCarregamentoFalhou(interpretarFalhaCarregamento(err, 'Setor não encontrado.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function updateVinculo(atendente: Atendentes.Atendente, nextSetorIds: number[]) {
    await atendentes.update(atendente.id, { setor_ids: nextSetorIds })
  }

  async function handleAdd() {
    if (addingId === '' || saving) return
    const alvo = todosAtendentes.find((a) => a.id === Number(addingId))
    if (!alvo) return
    setSaving(true)
    try {
      const atual = new Set(alvo.setor_ids ?? [])
      atual.add(setorId)
      await updateVinculo(alvo, Array.from(atual))
      toast.showSuccess('Atendente vinculado ao setor.')
      setAddingId('')
      await reload()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível vincular o atendente.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleRemove(atendente: Atendentes.Atendente) {
    if (saving) return
    if (!confirm(`Remover ${atendente.nome} deste setor?`)) return
    setSaving(true)
    try {
      const atual = new Set(atendente.setor_ids ?? [])
      for (const sid of grupoSetorIds) atual.delete(sid)
      await updateVinculo(atendente, Array.from(atual))
      toast.showSuccess('Vínculo removido.')
      await reload()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível remover o vínculo.'))
    } finally {
      setSaving(false)
    }
  }

  function toggleElegivel(atendenteId: number) {
    setDistElegiveisIds((prev) => {
      const s = new Set(prev)
      if (s.has(atendenteId)) s.delete(atendenteId)
      else s.add(atendenteId)
      return Array.from(s).sort((a, b) => a - b)
    })
  }

  async function handleSalvarDistribuicao() {
    if (savingDist || !setor) return
    if (distModo === 'auto_imediato') {
      const ok = confirm(
        'Tickets novos ou devolvidos à fila serão atribuídos automaticamente assim que entrarem. Deseja continuar?',
      )
      if (!ok) return
    }
    if (!distUsarTodos && distElegiveisIds.length === 0) {
      toast.showError('Selecione ao menos um atendente elegível ou marque «todos do setor».')
      return
    }
    setSavingDist(true)
    try {
      const body: Setores.DistribuicaoUpdate = {
        modo: distModo,
        timeout_minutos: Math.max(1, distTimeout),
        estrategia: distEstrategia,
        atendentes_elegiveis: distUsarTodos ? null : distElegiveisIds,
      }
      const atualizado = await setores.updateDistribuicao(setor.id, body)
      setSetor((prev) => (prev ? { ...prev, distribuicao: atualizado } : prev))
      aplicarDistribuicaoDoSetor({ ...setor, distribuicao: atualizado })
      toast.showSuccess('Distribuição automática atualizada.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a distribuição.'))
    } finally {
      setSavingDist(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-slate-500 dark:text-slate-400">
        Carregando setor…
      </div>
    )
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para acessar este setor."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara="/setores"
          voltarLabel="Voltar para Setores"
        />
      </div>
    )
  }

  if (carregamentoFalhou) {
    return (
      <CarregamentoFalhou titulo={carregamentoFalhou.titulo} detalhe={carregamentoFalhou.detalhe} onVoltar={voltarAnterior} />
    )
  }

  if (!setor) {
    return null
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <nav aria-label="breadcrumb" className="flex flex-wrap items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <button
          type="button"
          onClick={voltarAnterior}
          className="font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
        >
          ← Voltar
        </button>
        <span aria-hidden className="text-slate-300 dark:text-slate-600">
          /
        </span>
        <button
          type="button"
          onClick={() => navigate('/setores')}
          className="font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
        >
          Setores
        </button>
        <span aria-hidden className="text-slate-300 dark:text-slate-600">
          /
        </span>
        <span className="font-semibold text-slate-800 dark:text-slate-100">{setor.nome}</span>
      </nav>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{setor.nome}</h1>
          <div className="mt-2">
            <BadgeAtivo ativo={setor.ativo} />
          </div>
        </div>
        <Button onClick={() => navigate(`/setores/${setor.id}/editar`)}>Editar</Button>
      </div>

      <Card title="Dados do setor">
        <dl>
          <DetailRow label="ID" value={String(setor.id)} mono />
          <DetailRow label="Nome" value={setor.nome} />
          <DetailRow label="Slug" value={setor.slug} mono />
          <DetailRow label="Situação" value={setor.ativo ? 'Ativo' : 'Inativo'} />
        </dl>
      </Card>

      <Card title="Distribuição automática de tickets">
        <div className="space-y-4">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Define como tickets sem responsável neste setor são atribuídos. Administradores nunca recebem atribuição
            automática.
          </p>

          <Select
            label="Modo"
            value={distModo}
            onChange={(v) => setDistModo(v as Setores.DistribuicaoModo)}
            options={MODO_OPCOES.map((o) => ({ value: o.value, label: o.label }))}
          />

          {distModo === 'auto_apos_timeout' && (
            <div className="max-w-xs">
              <label htmlFor="dist-timeout" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Tempo na fila antes de atribuir (minutos)
              </label>
              <input
                id="dist-timeout"
                type="number"
                min={1}
                max={1440}
                value={distTimeout}
                onChange={(e) => setDistTimeout(Number(e.target.value) || 1)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              />
            </div>
          )}

          {distModo !== 'manual' && (
            <>
              <Select
                label="Estratégia"
                value={distEstrategia}
                onChange={(v) => setDistEstrategia(v as Setores.DistribuicaoEstrategia)}
                options={ESTRATEGIA_OPCOES.map((o) => ({ value: o.value, label: o.label }))}
              />

              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={distUsarTodos}
                    onChange={(e) => setDistUsarTodos(e.target.checked)}
                    className="size-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  Todos os atendentes vinculados ao setor
                </label>
                {!distUsarTodos && (
                  <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                    {vinculadosOperacionais.length === 0 ? (
                      <p className="text-sm text-slate-500 dark:text-slate-400">Nenhum atendente operacional vinculado.</p>
                    ) : (
                      <ul className="space-y-2">
                        {vinculadosOperacionais.map((a) => (
                          <li key={a.id}>
                            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                              <input
                                type="checkbox"
                                checked={distElegiveisIds.includes(a.id)}
                                onChange={() => toggleElegivel(a.id)}
                                className="size-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                              />
                              {a.nome}
                            </label>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            </>
          )}

          <div>
            <Button onClick={handleSalvarDistribuicao} loading={savingDist}>
              Salvar distribuição
            </Button>
          </div>
        </div>
      </Card>

      <Card title="Atendentes vinculados">
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <div className="flex-1">
              <SelectComPesquisa
                id="setor-add-atendente"
                label="Adicionar atendente"
                value={addingId}
                onChange={(v) => setAddingId(v)}
                items={atendenteItems}
              />
            </div>
            <div className="sm:pb-[2px]">
              <Button onClick={handleAdd} disabled={addingId === ''} loading={saving}>
                Adicionar
              </Button>
            </div>
          </div>

          {vinculados.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400">Nenhum atendente vinculado.</p>
          ) : (
            <div className="-mx-2 overflow-x-auto rounded-lg">
              <table className="w-full min-w-[680px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      Nome
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      E-mail
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      Perfil
                    </th>
                    <th className="w-px whitespace-nowrap px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      Ações
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {vinculados
                    .slice()
                    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
                    .map((a) => (
                      <tr key={a.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                        <td className="px-4 py-3.5">
                          <span className={`font-medium ${a.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>
                            {a.nome}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">{a.email}</td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">{a.role === 'admin' ? 'Administrador' : 'Atendente'}</td>
                        <td className="px-4 py-3.5 text-right">
                          <Button variant="secondary" onClick={() => handleRemove(a)} loading={saving}>
                            Remover
                          </Button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
