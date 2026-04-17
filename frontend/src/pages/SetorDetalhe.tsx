import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, atendentes, setores, type Atendentes, type Setores } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { SelectComPesquisa } from '../components/ui/SelectComPesquisa'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { SemPermissao } from './SemPermissao'

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

  const [vinculados, setVinculados] = useState<Atendentes.Atendente[]>([])
  const [todosAtendentes, setTodosAtendentes] = useState<Atendentes.Atendente[]>([])
  const [addingId, setAddingId] = useState<number | ''>('')
  const [saving, setSaving] = useState(false)

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

  async function reload() {
    if (!Number.isFinite(setorId) || setorId <= 0) {
      setSetor(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setForbidden(false)
    try {
      const [s, setoresAll, todos] = await Promise.all([
        setores.get(setorId),
        coletarTodasPaginas<Setores.Setor>((o, l) => setores.list({ incluir_inativos: true, offset: o, limit: l })),
        coletarTodasPaginas<Atendentes.Atendente>((o, l) =>
          atendentes.list({ incluir_inativos: true, offset: o, limit: l }),
        ),
      ])
      setSetor(s)
      setSetoresList(setoresAll)
      setTodosAtendentes(todos)

      const vinculadosDoGrupo = await atendentes.listPorSetor(setorId, { incluir_inativos: true })
      setVinculados(vinculadosDoGrupo)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true)
        setSetor(null)
        setVinculados([])
        return
      }
      setSetor(null)
      setVinculados([])
      toast.showError(err instanceof Error ? err.message : 'Erro ao carregar setor')
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
      toast.showError(err instanceof Error ? err.message : 'Erro ao vincular atendente')
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
      // remove do “setor lógico” (todas duplicatas de mesmo nome)
      for (const sid of grupoSetorIds) atual.delete(sid)
      await updateVinculo(atendente, Array.from(atual))
      toast.showSuccess('Vínculo removido.')
      await reload()
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Erro ao remover vínculo')
    } finally {
      setSaving(false)
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

  if (!setor) {
    return (
      <div className="space-y-4">
        <p className="text-slate-600 dark:text-slate-400">Setor não encontrado.</p>
        <button
          type="button"
          onClick={voltarAnterior}
          className="font-medium text-slate-800 underline decoration-slate-400 underline-offset-2 hover:text-slate-950 dark:text-slate-200 dark:hover:text-white"
        >
          Voltar
        </button>
      </div>
    )
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

      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{setor.nome}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Slug: <span className="font-mono">{setor.slug}</span> • {setor.ativo ? 'Ativo' : 'Inativo'}
          </p>
        </div>
      </div>

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

