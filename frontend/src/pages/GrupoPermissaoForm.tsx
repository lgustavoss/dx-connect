import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, permissaoGrupos, type PermissaoGrupos } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { CadastroFormPageShell } from '../components/ui/CadastroFormPageShell'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { FormSection } from '../components/ui/FormSection'
import { InlineCadastroFooter } from '../components/ui/InlineCadastroPanel'
import { Input } from '../components/ui/Input'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { SemPermissao } from './SemPermissao'

const LISTA = '/configuracoes/equipe/grupos-permissao'
const PADRAO_NOVO = ['operacional', 'chat.encerrar_sem_demanda']
const ROTULO_ACAO: Record<string, string> = {
  ver: 'Ver',
  criar: 'Criar',
  editar: 'Editar',
  excluir: 'Excluir',
}
const ORDEM_ACAO = ['ver', 'criar', 'editar', 'excluir']

export const AREAS: { id: string; titulo: string; modulos: string[] }[] = [
  {
    id: 'atendimento',
    titulo: 'Atendimento',
    modulos: ['Atendimento', 'Chat', 'WhatsApp', 'Ponto', 'Dashboard', 'Relatórios'],
  },
  {
    id: 'comercial',
    titulo: 'Comercial',
    modulos: ['CRM', 'Propostas', 'Contratos', 'Custos', 'Implantação', 'Tipos de negócio', 'Faturamento'],
  },
  { id: 'cadastros', titulo: 'Cadastros', modulos: ['Redes', 'Empresas', 'Funcionários da rede'] },
  { id: 'ajuda', titulo: 'Ajuda', modulos: ['Ajuda'] },
  { id: 'equipe', titulo: 'Equipe', modulos: ['Setores', 'Atendentes', 'Grupos de permissão'] },
  {
    id: 'config',
    titulo: 'Configurações',
    modulos: [
      'Status de ticket',
      'Natureza e motivo',
      'Respostas prontas',
      'Roteamento',
      'SLA',
      'Canais',
      'Instalação',
      'PDV',
      'Auditoria',
      'Sugestões',
    ],
  },
]

const TITULO_RECURSO: Record<string, string> = {
  tickets: 'Tickets',
  atendimento: 'Fora do próprio setor',
  chat: 'Chat',
  whatsapp: 'WhatsApp',
  ponto: 'Ponto',
  presenca: 'Equipe online',
  dashboard: 'Dashboard',
  relatorios: 'Relatórios',
  crm: 'Leads e negociações',
  funil: 'Funil',
  propostas: 'Propostas',
  contratos: 'Contratos',
  custos: 'Custos',
  implantacao: 'Checklist',
  tipos_negocio: 'Tipos de negócio',
  faturamento: 'Faturamento',
  'ajuda.categorias': 'Categorias',
  'ajuda.artigos': 'Artigos',
  ajuda: 'Consulta e portal',
  'canais.whatsapp': 'WhatsApp',
  'canais.email': 'E-mail',
  pdv: 'Catálogos',
  'pdv.acessos': 'Acessos da empresa',
}

type Item = PermissaoGrupos.CatalogoItem

type Linha = { id: string; titulo: string; itens: Item[] }

function recursoDe(codigo: string): string {
  const i = codigo.lastIndexOf('.')
  return i === -1 ? codigo : codigo.slice(0, i)
}

function acaoDe(codigo: string): string {
  const i = codigo.lastIndexOf('.')
  return i === -1 ? codigo : codigo.slice(i + 1)
}

export function rotuloAcao(item: Item): string {
  return ROTULO_ACAO[acaoDe(item.codigo)] ?? item.nome
}

function FlagPermissao({
  checked,
  title,
  onClick,
  children,
}: {
  checked: boolean
  title: string
  onClick: () => void
  children: string
}) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      title={title}
      onClick={onClick}
      className={`inline-flex h-8 items-center rounded-full px-3 text-sm font-medium ring-1 ring-inset transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/70 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900 ${
        checked
          ? 'bg-cyan-500/15 text-cyan-800 ring-cyan-600/30 dark:bg-cyan-400/15 dark:text-cyan-100 dark:ring-cyan-300/30'
          : 'bg-slate-100 text-slate-600 ring-transparent hover:bg-slate-200 dark:bg-slate-800/80 dark:text-slate-300 dark:hover:bg-slate-800'
      }`}
    >
      {children}
    </button>
  )
}

function ordenarAcoes(itens: Item[]): Item[] {
  return [...itens].sort((a, b) => {
    const ia = ORDEM_ACAO.indexOf(acaoDe(a.codigo))
    const ib = ORDEM_ACAO.indexOf(acaoDe(b.codigo))
    return (ia === -1 ? 50 : ia) - (ib === -1 ? 50 : ib)
  })
}

export function linhasDoModulo(modulo: string, itens: Item[]): Linha[] {
  const porRecurso = new Map<string, Item[]>()
  for (const item of itens) {
    if (item.codigo === 'admin' || item.codigo === 'comercial' || item.codigo === 'operacional') continue
    const recurso = recursoDe(item.codigo)
    const lista = porRecurso.get(recurso) ?? []
    lista.push(item)
    porRecurso.set(recurso, lista)
  }
  const recursos = [...porRecurso.keys()]
  return recursos.map((recurso) => ({
    id: `${modulo}:${recurso}`,
    titulo: recursos.length === 1 ? modulo : (TITULO_RECURSO[recurso] ?? modulo),
    itens: ordenarAcoes(porRecurso.get(recurso) ?? []),
  }))
}

function marcarCodigo(catalogo: Item[], codigos: string[], codigo: string, ligado: boolean): string[] {
  const recurso = recursoDe(codigo)
  let proximos = codigos.filter((item) => item !== 'admin' && item !== 'comercial' && item !== 'operacional')
  if (ligado) {
    if (!proximos.includes(codigo)) proximos.push(codigo)
    const ver = recurso ? `${recurso}.ver` : ''
    if (ver && ver !== codigo && catalogo.some((item) => item.codigo === ver) && !proximos.includes(ver)) {
      proximos.push(ver)
    }
    return proximos
  }
  if (recurso && codigo.endsWith('.ver')) {
    return proximos.filter((item) => recursoDe(item) !== recurso)
  }
  return proximos.filter((item) => item !== codigo)
}

export function expandir(catalogo: Item[], codigos: string[]): string[] {
  if (codigos.includes('admin')) return ['admin']
  let proximos = codigos.filter((codigo) => codigo !== 'comercial' && codigo !== 'operacional')
  for (const pacote of ['comercial', 'operacional']) {
    if (!codigos.includes(pacote)) continue
    for (const item of catalogo) {
      if (item.pacote === pacote && !proximos.includes(item.codigo)) proximos.push(item.codigo)
    }
  }
  for (const codigo of [...proximos]) {
    proximos = marcarCodigo(catalogo, proximos, codigo, true)
  }
  return proximos
}

function payloadDe(catalogo: Item[], codigos: string[]): string[] {
  if (codigos.includes('admin')) return ['admin']
  let payload = codigos.filter((codigo) => codigo !== 'comercial' && codigo !== 'operacional' && codigo !== 'admin')
  for (const pacote of ['operacional', 'comercial']) {
    const doPacote = catalogo.filter((item) => item.pacote === pacote).map((item) => item.codigo)
    if (doPacote.length > 0 && doPacote.every((codigo) => payload.includes(codigo))) {
      payload = [...payload.filter((codigo) => !doPacote.includes(codigo)), pacote]
    }
  }
  return payload
}

export function GrupoPermissaoForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior(LISTA)
  const grupoId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null
  const antesDoAcesso = useRef<string[]>([])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [inexistente, setInexistente] = useState(false)
  const [catalogo, setCatalogo] = useState<Item[]>([])
  const [nome, setNome] = useState('')
  const [permissoes, setPermissoes] = useState<string[]>([])
  const [busca, setBusca] = useState('')
  const [fechadas, setFechadas] = useState<string[]>([])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setInexistente(false)
    permissaoGrupos
      .catalogo()
      .then(async (itens) => {
        if (cancelled) return
        setCatalogo(itens)
        if (!isEdit) {
          setPermissoes(expandir(itens, PADRAO_NOVO))
          return
        }
        if (Number.isNaN(grupoId)) {
          setInexistente(true)
          return
        }
        const grupos = await permissaoGrupos.list()
        if (cancelled) return
        const grupo = grupos.find((item) => item.id === grupoId)
        if (!grupo) {
          setInexistente(true)
          return
        }
        setNome(grupo.nome)
        setPermissoes(expandir(itens, grupo.permissoes))
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
  }, [grupoId, isEdit, toast])

  const acessoTotal = permissoes.includes('admin')
  const termo = busca.trim().toLowerCase()

  const areas = useMemo(() => {
    const usados = new Set<string>()
    const blocos = AREAS.map((area) => {
      const linhas = area.modulos.flatMap((modulo) => {
        usados.add(modulo)
        return linhasDoModulo(
          modulo,
          catalogo.filter((item) => item.modulo === modulo),
        )
      })
      return { ...area, linhas }
    })
    const restantes = linhasDoModulo(
      'Outros',
      catalogo.filter((item) => !usados.has(item.modulo) && item.codigo !== 'admin'),
    )
    if (restantes.length > 0) blocos.push({ id: 'outros', titulo: 'Outros', modulos: [], linhas: restantes })
    return blocos
  }, [catalogo])

  function alternar(codigo: string) {
    if (acessoTotal) return
    setPermissoes(marcarCodigo(catalogo, permissoes, codigo, !permissoes.includes(codigo)))
  }

  function alternarLinhas(linhas: Linha[], marcarTodos: boolean) {
    if (acessoTotal) return
    const codigos = linhas.flatMap((linha) => linha.itens.map((item) => item.codigo))
    let proximos = permissoes
    for (const codigo of codigos) {
      const ligado = proximos.includes(codigo)
      if (marcarTodos && !ligado) proximos = marcarCodigo(catalogo, proximos, codigo, true)
      if (!marcarTodos && ligado) proximos = marcarCodigo(catalogo, proximos, codigo, false)
    }
    setPermissoes(proximos)
  }

  function alternarAcessoTotal() {
    if (acessoTotal) {
      setPermissoes(antesDoAcesso.current)
      return
    }
    antesDoAcesso.current = permissoes.filter((codigo) => codigo !== 'admin')
    setPermissoes(['admin'])
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    const titulo = nome.trim()
    if (titulo.length < 2) {
      toast.showWarning('Informe o nome do grupo.')
      return
    }
    const payload = payloadDe(catalogo, permissoes)
    if (payload.length === 0) {
      toast.showWarning('Marque pelo menos uma permissão.')
      return
    }
    setSaving(true)
    try {
      if (isEdit && !Number.isNaN(grupoId)) {
        const salvo = await permissaoGrupos.update(grupoId, { nome: titulo, permissoes: payload })
        toast.showSuccess('Grupo atualizado.')
        navigate(`${LISTA}/${salvo.id}`, { replace: true })
      } else {
        const salvo = await permissaoGrupos.create({ nome: titulo, permissoes: payload })
        toast.showSuccess('Grupo criado.')
        navigate(`${LISTA}/${salvo.id}`, { replace: true })
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o grupo.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <CadastroFormPageShell onVoltar={voltarAnterior} wide>
        <div className="h-96 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </CadastroFormPageShell>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para editar grupos."
        voltarPara={LISTA}
        voltarLabel="Voltar para grupos"
      />
    )
  }

  if (inexistente) {
    return <CarregamentoFalhou titulo="Grupo não encontrado." onVoltar={voltarAnterior} />
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior} wide>
      <Card title={isEdit ? 'Editar grupo' : 'Novo grupo'}>
        <form onSubmit={(ev) => void salvar(ev)} className="space-y-5 sm:space-y-6">
          <FormSection
            title="Identificação"
            description="O nome aparece na lista de pessoas. Acesso total libera tudo; o restante é escolhido ação por ação."
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <div className="min-w-0 flex-1">
                <Input label="Nome" value={nome} onChange={(ev) => setNome(ev.target.value)} required />
              </div>
              <div className="flex h-10 shrink-0 items-center">
                <Switch
                  bare
                  tight
                  checked={acessoTotal}
                  onCheckedChange={(ligado) => {
                    if (ligado !== acessoTotal) alternarAcessoTotal()
                  }}
                  label="Acesso total"
                />
              </div>
            </div>
          </FormSection>

          {acessoTotal ? (
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Com o acesso total ligado, este grupo pode tudo. Desmarque acima para ajustar ação por ação.
            </p>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 sm:items-end">
                <Input
                  label="Buscar"
                  value={busca}
                  onChange={(ev) => setBusca(ev.target.value)}
                  placeholder="Empresa, contrato, WhatsApp…"
                  hint="Criar, editar ou excluir também marca ver. Se tirar o ver, as outras ações da mesma linha saem junto."
                />
              </div>

              {areas.map((area) => {
                const linhas = area.linhas.filter((linha) => {
                  if (!termo) return true
                  const texto = `${linha.titulo} ${linha.itens.map((item) => `${item.nome} ${item.descricao}`).join(' ')}`
                  return texto.toLowerCase().includes(termo)
                })
                if (linhas.length === 0) return null
                const todosMarcados = linhas.every((linha) => linha.itens.every((item) => permissoes.includes(item.codigo)))
                const total = linhas.reduce((n, linha) => n + linha.itens.length, 0)
                const marcadas = linhas.reduce(
                  (n, linha) => n + linha.itens.filter((item) => permissoes.includes(item.codigo)).length,
                  0,
                )
                const aberta = termo.length > 0 || !fechadas.includes(area.id)
                return (
                  <section
                    key={area.id}
                    className="rounded-2xl border border-slate-200/90 bg-slate-50/35 dark:border-slate-800/55 dark:bg-slate-900/40"
                  >
                    <div className="flex h-14 items-center justify-between gap-3 px-4 sm:px-5">
                      <button
                        type="button"
                        className="inline-flex h-10 items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100"
                        aria-expanded={aberta}
                        onClick={() =>
                          setFechadas((atual) =>
                            atual.includes(area.id) ? atual.filter((item) => item !== area.id) : [...atual, area.id],
                          )
                        }
                      >
                        <svg
                          className={`size-4 shrink-0 text-slate-400 transition-transform ${aberta ? 'rotate-90' : ''}`}
                          viewBox="0 0 20 20"
                          fill="currentColor"
                          aria-hidden
                        >
                          <path
                            fillRule="evenodd"
                            d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                            clipRule="evenodd"
                          />
                        </svg>
                        {area.titulo}
                      </button>
                      <Button variant="secondary" onClick={() => alternarLinhas(linhas, !todosMarcados)}>
                        {todosMarcados ? 'Limpar' : 'Marcar todas'}
                        <span className="rounded-md bg-slate-200/80 px-1.5 py-0.5 text-xs font-semibold tabular-nums text-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
                          {marcadas}/{total}
                        </span>
                      </Button>
                    </div>
                    {aberta ? (
                      <div className="border-t border-slate-200/80 px-4 sm:px-5 dark:border-slate-800/55">
                        {linhas.map((linha) => (
                          <div
                            key={linha.id}
                            className="grid grid-cols-1 items-center gap-2 border-b border-slate-200/70 py-2.5 last:border-b-0 sm:grid-cols-[13rem_minmax(0,1fr)] sm:gap-x-6 dark:border-slate-800/50"
                          >
                            <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
                              {linha.titulo}
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {linha.itens.map((item) => (
                                <FlagPermissao
                                  key={item.codigo}
                                  checked={permissoes.includes(item.codigo)}
                                  title={item.descricao}
                                  onClick={() => alternar(item.codigo)}
                                >
                                  {rotuloAcao(item)}
                                </FlagPermissao>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </section>
                )
              })}
              {areas.every((area) => {
                const linhas = area.linhas.filter((linha) => {
                  if (!termo) return true
                  const texto = `${linha.titulo} ${linha.itens.map((item) => `${item.nome} ${item.descricao}`).join(' ')}`
                  return texto.toLowerCase().includes(termo)
                })
                return linhas.length === 0
              }) ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma permissão com esse nome.</p>
              ) : null}
            </>
          )}

          <InlineCadastroFooter onCancel={voltarAnterior} saving={saving} />
        </form>
      </Card>
    </CadastroFormPageShell>
  )
}
