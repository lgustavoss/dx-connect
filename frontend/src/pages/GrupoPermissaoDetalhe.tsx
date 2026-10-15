import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ApiError, permissaoGrupos, type PermissaoGrupos } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { IconTrash } from '../components/ui/IconTrash'
import { CadastroFormPageShell } from '../components/ui/CadastroFormPageShell'
import { Card } from '../components/ui/Card'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { SelectComPesquisa } from '../components/ui/SelectComPesquisa'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { useAuth } from '../contexts/AuthContext'
import { temPermissao } from '../lib/permissoes'
import { SemPermissao } from './SemPermissao'
import { AREAS, expandir, linhasDoModulo, rotuloAcao } from './GrupoPermissaoForm'

const LISTA = '/configuracoes/equipe/grupos-permissao'
type Aba = 'permissoes' | 'pessoas'
type Item = PermissaoGrupos.CatalogoItem

function pillClass() {
  return 'inline-flex h-8 items-center rounded-full bg-cyan-500/15 px-3 text-sm font-medium text-cyan-800 ring-1 ring-inset ring-cyan-600/30 dark:bg-cyan-400/15 dark:text-cyan-100 dark:ring-cyan-300/30'
}

export function GrupoPermissaoDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const voltar = useVoltarAnterior(LISTA)
  const [searchParams, setSearchParams] = useSearchParams()
  const grupoId = id ? parseInt(id, 10) : NaN
  const aba: Aba = searchParams.get('aba') === 'pessoas' ? 'pessoas' : 'permissoes'
  const podeEditarGrupo = temPermissao(user, 'grupos.editar')
  const podeEditarPessoas = temPermissao(user, 'atendentes.editar')

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [inexistente, setInexistente] = useState(false)
  const [grupo, setGrupo] = useState<PermissaoGrupos.Grupo | null>(null)
  const [catalogo, setCatalogo] = useState<Item[]>([])
  const [membros, setMembros] = useState<PermissaoGrupos.Membro[]>([])
  const [candidatos, setCandidatos] = useState<PermissaoGrupos.Membro[]>([])
  const [escolha, setEscolha] = useState<number | ''>('')
  const [saving, setSaving] = useState(false)
  const [remover, setRemover] = useState<PermissaoGrupos.Membro | null>(null)

  const carregarPessoas = useCallback(async () => {
    if (Number.isNaN(grupoId)) return
    const lista = await permissaoGrupos.membros(grupoId)
    setMembros(lista)
    if (!podeEditarPessoas) {
      setCandidatos([])
      return
    }
    const livres = await permissaoGrupos.candidatos(grupoId)
    setCandidatos(livres)
  }, [grupoId, podeEditarPessoas])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setInexistente(false)
    if (Number.isNaN(grupoId)) {
      setInexistente(true)
      setLoading(false)
      return
    }
    Promise.all([permissaoGrupos.catalogo(), permissaoGrupos.list(), permissaoGrupos.membros(grupoId)])
      .then(async ([itens, grupos, pessoas]) => {
        if (cancelled) return
        const encontrado = grupos.find((item) => item.id === grupoId) ?? null
        if (!encontrado) {
          setInexistente(true)
          return
        }
        setCatalogo(itens)
        setGrupo(encontrado)
        setMembros(pessoas)
        if (podeEditarPessoas) {
          const livres = await permissaoGrupos.candidatos(grupoId)
          if (!cancelled) setCandidatos(livres)
        }
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) setForbidden(true)
        else toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o grupo.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [grupoId, podeEditarPessoas, toast])

  function mudarAba(proxima: Aba) {
    const next = new URLSearchParams(searchParams)
    if (proxima === 'permissoes') next.delete('aba')
    else next.set('aba', proxima)
    setSearchParams(next, { replace: true })
  }

  async function adicionar() {
    if (escolha === '' || Number.isNaN(grupoId)) return
    setSaving(true)
    try {
      await permissaoGrupos.vincular(grupoId, escolha)
      toast.showSuccess('Pessoa adicionada ao grupo.')
      setEscolha('')
      await carregarPessoas()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível adicionar a pessoa.'))
    } finally {
      setSaving(false)
    }
  }

  async function confirmarRemocao() {
    if (!remover || Number.isNaN(grupoId)) return
    setSaving(true)
    try {
      await permissaoGrupos.desvincular(grupoId, remover.id)
      toast.showSuccess('Pessoa removida do grupo.')
      setRemover(null)
      await carregarPessoas()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível remover a pessoa.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <CadastroFormPageShell onVoltar={voltar} wide>
        <div className="h-96 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </CadastroFormPageShell>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para ver este grupo."
        voltarPara={LISTA}
        voltarLabel="Voltar para grupos"
      />
    )
  }

  if (inexistente || !grupo) {
    return <CarregamentoFalhou titulo="Grupo não encontrado." onVoltar={voltar} />
  }

  const efetivas = new Set(expandir(catalogo, grupo.permissoes))
  const acessoTotal = efetivas.has('admin')
  const areas = AREAS.map((area) => {
    const linhas = area.modulos
      .flatMap((modulo) => linhasDoModulo(modulo, catalogo.filter((item) => item.modulo === modulo)))
      .map((linha) => ({ ...linha, itens: linha.itens.filter((item) => efetivas.has(item.codigo)) }))
      .filter((linha) => linha.itens.length > 0)
    return { ...area, linhas }
  }).filter((area) => area.linhas.length > 0)

  const tabBtn = (key: Aba, label: string) => (
    <button
      type="button"
      onClick={() => mudarAba(key)}
      aria-current={aba === key ? 'page' : undefined}
      className={
        aba === key
          ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:text-white'
          : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
      }
    >
      {label}
    </button>
  )

  return (
    <CadastroFormPageShell onVoltar={voltar} wide>
      <Card
        title={grupo.nome}
        titleActions={
          podeEditarGrupo ? (
            <Button variant="secondary" onClick={() => navigate(`${LISTA}/${grupo.id}/editar`)}>
              Editar
            </Button>
          ) : null
        }
      >
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {grupo.sistema ? (
            <span className="rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
              Padrão
            </span>
          ) : null}
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {membros.length === 1 ? '1 pessoa' : `${membros.length} pessoas`}
          </span>
        </div>

        <div className="mb-5 flex gap-1 border-b border-slate-200 dark:border-slate-800">
          {tabBtn('permissoes', 'Permissões')}
          {tabBtn('pessoas', 'Pessoas')}
        </div>

        {aba === 'permissoes' ? (
          acessoTotal ? (
            <p className="text-sm text-slate-600 dark:text-slate-300">Acesso total. Este grupo pode tudo.</p>
          ) : areas.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma permissão marcada.</p>
          ) : (
            <div className="space-y-4">
              {areas.map((area) => {
                const totalAcoes = area.linhas.reduce((n, linha) => n + linha.itens.length, 0)
                return (
                <section
                  key={area.id}
                  className="overflow-hidden rounded-2xl border border-slate-200/90 bg-slate-50/35 dark:border-slate-800/55 dark:bg-slate-900/40"
                >
                  <h3 className="flex items-center justify-between gap-3 border-b border-slate-200/80 bg-slate-100/80 px-4 py-2.5 sm:px-5 dark:border-slate-800/55 dark:bg-slate-800/70">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-300">
                      {area.titulo}
                    </span>
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                      {totalAcoes} {totalAcoes === 1 ? 'ação' : 'ações'}
                    </span>
                  </h3>
                  <div className="px-4 sm:px-5">
                    {area.linhas.map((linha) => (
                      <div
                        key={linha.id}
                        className="grid grid-cols-1 items-center gap-2 border-b border-slate-200/70 py-2.5 last:border-b-0 sm:grid-cols-[13rem_minmax(0,1fr)] sm:gap-x-6 dark:border-slate-800/50"
                      >
                        <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{linha.titulo}</span>
                        <div className="flex flex-wrap gap-2">
                          {linha.itens.map((item) => (
                            <span key={item.codigo} title={item.descricao} className={pillClass()}>
                              {rotuloAcao(item)}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
                )
              })}
            </div>
          )
        ) : (
          <div className="space-y-4">
            {podeEditarPessoas ? (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="min-w-0 flex-1 sm:max-w-md">
                  <SelectComPesquisa
                    id="grupo-adicionar-pessoa"
                    label="Adicionar pessoa"
                    value={escolha}
                    onChange={setEscolha}
                    items={candidatos.map((pessoa) => ({
                      id: pessoa.id,
                      label: pessoa.ativo ? `${pessoa.nome} — ${pessoa.email}` : `${pessoa.nome} — ${pessoa.email} (inativo)`,
                    }))}
                    placeholder="Buscar por nome ou e-mail"
                    hint="Digite o nome ou o e-mail."
                    recentCount={Math.max(candidatos.length, 1)}
                    disabled={candidatos.length === 0 || saving}
                  />
                </div>
                <Button disabled={escolha === '' || saving} onClick={() => void adicionar()}>
                  Adicionar
                </Button>
              </div>
            ) : null}

            {membros.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma pessoa neste grupo.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[520px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                      <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Pessoa</th>
                      <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">E-mail</th>
                      <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500">
                        <span className="sr-only">Ações</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {membros.map((pessoa) => (
                      <tr key={pessoa.id}>
                        <td className="px-4 py-3.5">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-slate-800 dark:text-slate-100">{pessoa.nome}</span>
                            {pessoa.ativo ? null : (
                              <span className="rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                                Inativo
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">{pessoa.email}</td>
                        <td className="px-4 py-3.5 text-right">
                          {podeEditarPessoas ? (
                            <Button variant="ghost" aria-label={`Remover ${pessoa.nome} do grupo`} onClick={() => setRemover(pessoa)}>
                              <IconTrash ariaHidden={false} />
                            </Button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={remover != null}
        title="Remover do grupo"
        message={remover ? `Remover ${remover.nome} deste grupo?` : undefined}
        confirmLabel="Remover"
        variant="danger"
        loading={saving}
        onConfirm={() => void confirmarRemocao()}
        onCancel={() => {
          if (!saving) setRemover(null)
        }}
      />
    </CadastroFormPageShell>
  )
}
