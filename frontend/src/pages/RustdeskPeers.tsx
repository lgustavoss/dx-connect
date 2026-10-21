import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  ApiError,
  empresaPdvs,
  empresas,
  rustdeskPeers,
  type EmpresaPdv,
  type Empresas,
  type RustdeskFrota,
} from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { IconCopy } from '../components/ui/IconCopy'
import { IconTrash } from '../components/ui/IconTrash'
import { Input } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { temPermissao } from '../lib/permissoes'
import { formatarIdRustdesk } from '../lib/rustdeskId'
import {
  iniciarDownloadInstaladorWindows,
  urlDownloadInstaladorNaInstancia,
} from '../lib/rustdeskInstaller'
import { conectarAcessoRemoto, senhaDoPdv } from '../lib/acessoRemotoConectar'
import { isDeskRudderDesktop } from '../lib/deskrudderDesktop'
import { IconeConectarRemoto } from '../components/IconeConectarRemoto'

const FILTROS: { id: RustdeskFrota.Filtro; rotulo: string }[] = [
  { id: 'todos', rotulo: 'Todos' },
  { id: 'online', rotulo: 'Online' },
  { id: 'offline', rotulo: 'Offline' },
  { id: 'sem_vinculo', rotulo: 'Sem vínculo' },
  { id: 'vinculado', rotulo: 'Vinculados' },
]

function IconeVinculo({ ligado }: { ligado: boolean }) {
  return (
    <svg className="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeWidth={2} d="M9 17H7A5 5 0 0 1 7 7h2" />
      <path strokeLinecap="round" strokeWidth={2} d="M15 7h2a5 5 0 1 1 0 10h-2" />
      <path strokeLinecap="round" strokeWidth={2} d="M8 12h8" />
      {ligado ? <path strokeLinecap="round" strokeWidth={2.5} d="M4 20L20 4" /> : null}
    </svg>
  )
}

function BotaoIcone({
  title,
  onClick,
  disabled = false,
  children,
}: {
  title: string
  onClick?: () => void
  disabled?: boolean
  children: ReactNode
}) {
  return (
    <span title={title} className="inline-flex">
      <button
        type="button"
        aria-label={title}
        disabled={disabled}
        onClick={onClick}
        className="inline-flex size-8 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 disabled:pointer-events-none disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
      >
        {children}
      </button>
    </span>
  )
}

function textoConfiguracao(config: RustdeskFrota.Configuracao) {
  return [
    `Servidor de ID: ${config.servidor_id}`,
    `Servidor de Relay: ${config.servidor_relay}`,
    `Chave: ${config.chave}`,
  ].join('\n')
}

function CampoConfiguracao({
  rotulo,
  valor,
  onCopiar,
}: {
  rotulo: string
  valor: string
  onCopiar: (texto: string, sucesso: string) => void
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{rotulo}</p>
        <p className="truncate font-mono text-sm text-slate-800 dark:text-slate-100" title={valor}>
          {valor}
        </p>
      </div>
      <BotaoIcone title={`Copiar ${rotulo}`} onClick={() => onCopiar(valor, `${rotulo} copiado.`)}>
        <IconCopy className="size-4" />
      </BotaoIcone>
    </div>
  )
}

function PainelDownloadInstalador({ onCopiar }: { onCopiar: (texto: string, sucesso: string) => void }) {
  const linkCurto = urlDownloadInstaladorNaInstancia()
  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/40">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-3xl">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Instalador Windows</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Envie este link para o posto: ao abrir no navegador, o download começa sem entrar no painel.
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          title="Baixar DeskRudder Acesso Remoto para Windows"
          onClick={() => iniciarDownloadInstaladorWindows()}
        >
          Baixar instalador Windows
        </Button>
      </div>
      <CampoConfiguracao rotulo="Link para o posto" valor={linkCurto} onCopiar={onCopiar} />
    </section>
  )
}

function PainelConfiguracao({
  config,
  onCopiar,
}: {
  config: RustdeskFrota.Configuracao | null
  onCopiar: (texto: string, sucesso: string) => void
}) {
  if (!config) return null
  if (!config.configurado) {
    return (
      <p className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800/40 dark:text-slate-300">
        Os dados para colar no DeskRudder Acesso Remoto ainda não foram informados nesta instância.
      </p>
    )
  }
  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/40">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-3xl">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Configuração do DeskRudder Acesso Remoto</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            No computador do cliente, abra o DeskRudder Acesso Remoto em Configurações e depois Rede. Cole cada valor no
            campo com o mesmo nome. O servidor de API fica em branco.
          </p>
        </div>
        <Button type="button" variant="secondary" onClick={() => onCopiar(textoConfiguracao(config), 'Configuração copiada.')}>
          Copiar tudo
        </Button>
      </div>
      <div className="grid gap-2 md:grid-cols-3">
        <CampoConfiguracao rotulo="Servidor de ID" valor={config.servidor_id} onCopiar={onCopiar} />
        <CampoConfiguracao rotulo="Servidor de Relay" valor={config.servidor_relay} onCopiar={onCopiar} />
        <CampoConfiguracao rotulo="Chave" valor={config.chave} onCopiar={onCopiar} />
      </div>
    </section>
  )
}

function dicaExcluir(peer: RustdeskFrota.Peer) {
  if (!peer.sem_vinculo) return 'É necessário desvincular antes de excluir.'
  if (peer.online !== false) return 'Só é possível excluir um computador offline.'
  return 'Excluir do servidor'
}

function formatarQuando(iso?: string | null) {
  if (!iso) return '—'
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return '—'
  return data.toLocaleString('pt-BR')
}

function textoBuscaVinculo(v: RustdeskFrota.Vinculo, extra = '') {
  return [v.rede_nome, v.empresa_nome, v.rotulo_nome, v.pdv_codigo, extra].filter(Boolean).join(' ')
}

function resumoVinculo(v: RustdeskFrota.Vinculo) {
  const rotulo = v.rotulo_nome?.trim() || 'Equipamento'
  const rede = v.rede_nome?.trim() ? `${v.rede_nome} · ` : ''
  return `${rede}${v.empresa_nome} · ${rotulo} ${v.pdv_codigo}`
}

type AcaoPendente =
  | { tipo: 'desvincular'; rustdeskId: string; pdvId: number; titulo: string; texto: string }
  | { tipo: 'excluir'; rustdeskId: string; titulo: string; texto: string }

function bateBusca(busca: string, texto: string) {
  const termos = busca.trim().toLocaleLowerCase('pt-BR').split(/\s+/).filter(Boolean)
  if (termos.length === 0) return true
  const alvo = texto.toLocaleLowerCase('pt-BR')
  return termos.every((termo) => alvo.includes(termo))
}

function LinhaVinculo({ v }: { v: RustdeskFrota.Vinculo }) {
  const rotulo = v.rotulo_nome?.trim() || 'Equipamento'
  return (
    <div>
      <Link className="font-medium text-sky-700 hover:underline dark:text-sky-300" to={`/empresas/${v.empresa_id}`}>
        {v.empresa_nome}
      </Link>
      <div className="text-xs text-slate-500 dark:text-slate-400">
        {v.rede_nome ? <span>{v.rede_nome} · </span> : null}
        <span>
          {rotulo} {v.pdv_codigo}
        </span>
        {!v.pdv_ativo ? <span> · inativo</span> : null}
      </div>
    </div>
  )
}

function SeloOnline({ online }: { online?: boolean | null }) {
  if (online === true) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
        <span className="size-1.5 rounded-full bg-emerald-500" />
        Online
      </span>
    )
  }
  if (online === false) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
        <span className="size-1.5 rounded-full bg-slate-400" />
        Offline
      </span>
    )
  }
  return <span className="text-xs text-slate-400">Sem sinal</span>
}

export function RustdeskPeers() {
  const toast = useToast()
  const { user } = useAuth()
  const podeVincular = temPermissao(user, 'empresas.editar')
  const [filtro, setFiltro] = useState<RustdeskFrota.Filtro>('todos')
  const [busca, setBusca] = useState('')
  const [lista, setLista] = useState<RustdeskFrota.Lista | null>(null)
  const [loading, setLoading] = useState(true)
  const [peerAlvo, setPeerAlvo] = useState<RustdeskFrota.Peer | null>(null)
  const [buscaEmpresa, setBuscaEmpresa] = useState('')
  const [empresasOpcoes, setEmpresasOpcoes] = useState<Empresas.EmpresaListaItem[]>([])
  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [pdvs, setPdvs] = useState<EmpresaPdv.Item[]>([])
  const [pdvId, setPdvId] = useState<number | ''>('')
  const [salvando, setSalvando] = useState(false)
  const [confirmacao, setConfirmacao] = useState<string | null>(null)
  const [acaoPendente, setAcaoPendente] = useState<AcaoPendente | null>(null)
  const [configuracao, setConfiguracao] = useState<RustdeskFrota.Configuracao | null>(null)
  const [remotoDesktopInstalado, setRemotoDesktopInstalado] = useState<boolean | null>(null)

  useEffect(() => {
    if (!isDeskRudderDesktop() || !window.deskrudderDesktop) {
      setRemotoDesktopInstalado(null)
      return
    }
    void window.deskrudderDesktop.remotoStatus().then((s) => setRemotoDesktopInstalado(s.instalado))
  }, [])

  async function copiarTexto(texto: string, sucesso: string) {
    try {
      await navigator.clipboard.writeText(texto)
      toast.showSuccess(sucesso)
    } catch {
      toast.showError('Não foi possível copiar. Selecione o texto manualmente.')
    }
  }

  const carregar = useCallback(() => {
    setLoading(true)
    rustdeskPeers
      .list({ filtro })
      .then(setLista)
      .catch((err) => toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os computadores.')))
      .finally(() => setLoading(false))
  }, [filtro, toast])

  useEffect(() => {
    carregar()
    const timer = window.setInterval(carregar, 30_000)
    return () => window.clearInterval(timer)
  }, [carregar])

  useEffect(() => {
    rustdeskPeers
      .configuracao()
      .then(setConfiguracao)
      .catch(() => setConfiguracao(null))
  }, [])

  useEffect(() => {
    if (!peerAlvo || !podeVincular) return
    const timer = window.setTimeout(() => {
      empresas
        .list({ busca: buscaEmpresa.trim() || undefined, limit: 20, ordenar_por: 'nome', ordem: 'asc' })
        .then((r) => setEmpresasOpcoes(r.items))
        .catch(() => setEmpresasOpcoes([]))
    }, 250)
    return () => window.clearTimeout(timer)
  }, [peerAlvo, podeVincular, buscaEmpresa])

  useEffect(() => {
    if (!empresaId) {
      setPdvs([])
      setPdvId('')
      return
    }
    empresaPdvs
      .list(empresaId, { incluir_inativos: true })
      .then((r) => {
        setPdvs(r.items)
        setPdvId(r.items[0]?.id ?? '')
      })
      .catch((err) => {
        setPdvs([])
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os PDVs.'))
      })
  }, [empresaId, toast])

  function abrirVinculo(peer: RustdeskFrota.Peer) {
    setPeerAlvo(peer)
    setBuscaEmpresa('')
    setEmpresaId('')
    setPdvs([])
    setPdvId('')
    setConfirmacao(null)
  }

  async function confirmarVinculo(substituir: boolean) {
    if (!peerAlvo || !pdvId) {
      toast.showWarning('Escolha a empresa e o PDV.')
      return
    }
    setSalvando(true)
    try {
      await rustdeskPeers.vincular(peerAlvo.rustdesk_id, {
        pdv_id: Number(pdvId),
        confirmar_substituicao: substituir,
      })
      toast.showSuccess('ID vinculado ao PDV.')
      setPeerAlvo(null)
      carregar()
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConfirmacao(err.message)
        return
      }
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível vincular o ID.'))
    } finally {
      setSalvando(false)
    }
  }

  async function conectar(peer: RustdeskFrota.Peer) {
    const unico = peer.vinculos.length === 1 ? peer.vinculos[0] : null
    let senha: string | null = null
    let avisou = false
    if (unico) {
      const r = await senhaDoPdv(unico.empresa_id, unico.pdv_id, toast)
      senha = r.senha
      avisou = r.avisou
    } else if (peer.vinculos.length > 1) {
      toast.showWarning('Este ID está em mais de um PDV. A senha não foi preenchida.')
      avisou = true
    }
    await conectarAcessoRemoto(peer.rustdesk_id, senha, toast, avisou)
  }

  function pedirDesvincular(rustdeskId: string, v: RustdeskFrota.Vinculo) {
    const id = formatarIdRustdesk(rustdeskId)
    setAcaoPendente({
      tipo: 'desvincular',
      rustdeskId,
      pdvId: v.pdv_id,
      titulo: 'Desvincular ID',
      texto: `Tirar ${id} de ${resumoVinculo(v)}? O computador continua nesta lista. O tipo de acesso remoto do cadastro não muda.`,
    })
  }

  function pedirExcluir(peer: RustdeskFrota.Peer) {
    const id = formatarIdRustdesk(peer.rustdesk_id)
    setAcaoPendente({
      tipo: 'excluir',
      rustdeskId: peer.rustdesk_id,
      titulo: 'Excluir do servidor',
      texto: `Apagar ${id} do servidor de acesso remoto? Ele sai desta lista. Se esse computador ligar de novo, o ID volta a aparecer.`,
    })
  }

  async function confirmarAcao() {
    if (!acaoPendente) return
    setSalvando(true)
    try {
      if (acaoPendente.tipo === 'desvincular') {
        await rustdeskPeers.desvincular(acaoPendente.rustdeskId, acaoPendente.pdvId)
        toast.showSuccess('ID desvinculado. Se ele não for mais usado e o computador estiver offline, exclua do servidor.')
      } else {
        await rustdeskPeers.excluir(acaoPendente.rustdeskId)
        toast.showSuccess('ID excluído do servidor de acesso remoto.')
      }
      setAcaoPendente(null)
      carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível concluir a ação.'))
    } finally {
      setSalvando(false)
    }
  }

  return (
    <PageContainer maxWidth="7xl">
      <PageHeader
        title="Acesso remoto"
        subtitle="Computadores registrados no servidor deste cliente. Online significa que aceita conexão remota agora. O vínculo grava o ID no PDV; a senha continua a do cadastro. ID de PC de atendente, sem vínculo e offline, pode ser excluído."
      />

      {remotoDesktopInstalado === false ? (
        <p
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100"
        >
          O DeskRudder Acesso Remoto (controle) não foi encontrado neste PC. Reinstale o{' '}
          <strong className="font-semibold">DeskRudder Setup</strong> do atendente (com elevação) ou coloque o
          cliente controle em{' '}
          <code className="rounded bg-amber-100/80 px-1 dark:bg-amber-900/50">
            Program Files (x86)\DeskRudder\Acesso Remoto
          </code>
          . Sem isso, conectar pela frota pode falhar.
        </p>
      ) : null}

      <div className="space-y-3">
        <PainelDownloadInstalador onCopiar={(texto, sucesso) => void copiarTexto(texto, sucesso)} />
        <PainelConfiguracao config={configuracao} onCopiar={(texto, sucesso) => void copiarTexto(texto, sucesso)} />
      </div>

      {lista?.agent_indisponivel ? (
        <p className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800/40 dark:text-slate-300">
          Não foi possível consultar o servidor de acesso remoto agora. A lista abaixo é a última leitura que deu certo.
        </p>
      ) : null}
      <Input
        label="Buscar"
        placeholder="Rede, empresa, rótulo, código ou ID"
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
      />

      <div className="flex flex-wrap gap-2">
        {FILTROS.map((item) => (
          <Button
            key={item.id}
            type="button"
            variant={filtro === item.id ? 'primary' : 'secondary'}
            onClick={() => setFiltro(item.id)}
          >
            {item.rotulo}
          </Button>
        ))}
      </div>

      {loading && !lista ? (
        <p className="text-sm text-slate-500">Carregando computadores…</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40">
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">IP</th>
                <th className="px-4 py-3">Situação</th>
                <th className="px-4 py-3">Última atividade</th>
                <th className="px-4 py-3">Vínculo</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {(() => {
                const visiveis = (lista?.items ?? []).filter((peer) =>
                  bateBusca(
                    busca,
                    [
                      peer.rustdesk_id,
                      formatarIdRustdesk(peer.rustdesk_id),
                      peer.ip,
                      ...peer.vinculos.map((v) => textoBuscaVinculo(v)),
                    ].join(' '),
                  ),
                )
                if (visiveis.length === 0) {
                  return (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                        Nenhum computador neste filtro.
                      </td>
                    </tr>
                  )
                }
                return visiveis.map((peer) => (
                  <tr key={peer.rustdesk_id}>
                    <td className="px-4 py-3 font-mono tracking-wide">{formatarIdRustdesk(peer.rustdesk_id)}</td>
                    <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-300">{peer.ip || '—'}</td>
                    <td className="px-4 py-3">
                      <SeloOnline online={peer.online} />
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{formatarQuando(peer.last_seen)}</td>
                    <td className="px-4 py-3">
                      {peer.vinculos.length === 0 ? (
                        <span className="text-slate-400">Sem vínculo</span>
                      ) : (
                        <ul className="space-y-2">
                          {peer.vinculos.map((v) => (
                            <li key={v.pdv_id}>
                              <LinhaVinculo v={v} />
                            </li>
                          ))}
                        </ul>
                      )}
                      {peer.id_repetido ? (
                        <p className="mt-1 text-xs text-slate-400">Este ID está em mais de um PDV.</p>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center justify-end gap-0.5">
                        <BotaoIcone title="Conectar" onClick={() => void conectar(peer)}>
                          <IconeConectarRemoto />
                        </BotaoIcone>
                        {podeVincular ? (
                          <>
                          {peer.vinculos.length === 0 ? (
                            <BotaoIcone title="Vincular" onClick={() => abrirVinculo(peer)}>
                              <IconeVinculo ligado={false} />
                            </BotaoIcone>
                          ) : (
                            peer.vinculos.map((v) => (
                              <BotaoIcone
                                key={v.pdv_id}
                                title={peer.vinculos.length > 1 ? `Desvincular de ${resumoVinculo(v)}` : 'Desvincular'}
                                onClick={() => pedirDesvincular(peer.rustdesk_id, v)}
                              >
                                <IconeVinculo ligado />
                              </BotaoIcone>
                            ))
                          )}
                          <BotaoIcone
                            title={dicaExcluir(peer)}
                            disabled={!peer.sem_vinculo || peer.online !== false}
                            onClick={() => pedirExcluir(peer)}
                          >
                            <IconTrash className="size-4" />
                          </BotaoIcone>
                          </>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))
              })()}
            </tbody>
          </table>
        </div>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Cadastros fora do servidor</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          PDV, servidor ou outro rótulo com acesso remoto cujo ID ainda não apareceu neste servidor.
        </p>
        {(lista?.pdvs_nao_vistos.length ?? 0) === 0 ? (
          <p className="text-sm text-slate-500">Nenhum PDV nessa situação.</p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
            {lista?.pdvs_nao_vistos
              .filter((item) =>
                bateBusca(
                  busca,
                  textoBuscaVinculo(
                    item,
                    [item.acesso_remoto_id, formatarIdRustdesk(item.acesso_remoto_id)].filter(Boolean).join(' '),
                  ),
                ),
              )
              .map((item) => (
              <li key={item.pdv_id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                <LinhaVinculo v={item} />
                <span className="flex flex-wrap items-center gap-3">
                  <span className="font-mono tracking-wide text-slate-600 dark:text-slate-300">
                    {formatarIdRustdesk(item.acesso_remoto_id)}
                  </span>
                  {podeVincular && item.acesso_remoto_id ? (
                    <BotaoIcone title="Desvincular" onClick={() => pedirDesvincular(item.acesso_remoto_id ?? '', item)}>
                      <IconeVinculo ligado />
                    </BotaoIcone>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {peerAlvo ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              Vincular ID {formatarIdRustdesk(peerAlvo.rustdesk_id)}
            </h3>
            <p className="mt-1 text-sm text-slate-500">O ID substitui o acesso remoto deste PDV. A senha não muda.</p>
            <div className="mt-4 space-y-4">
              <Input
                label="Buscar empresa"
                value={buscaEmpresa}
                onChange={(e) => setBuscaEmpresa(e.target.value)}
              />
              <Select
                label="Empresa"
                value={empresaId}
                onChange={(v) => setEmpresaId(v === '' ? '' : Number(v))}
                options={empresasOpcoes.map((e) => ({ value: e.id, label: e.nome }))}
                placeholder="Selecione a empresa"
              />
              <Select
                label="PDV"
                value={pdvId}
                onChange={(v) => setPdvId(v === '' ? '' : Number(v))}
                options={pdvs.map((p) => ({
                  value: p.id,
                  label: `${p.codigo}${p.rotulo_nome ? ` · ${p.rotulo_nome}` : ''}${p.ativo ? '' : ' (inativo)'}`,
                }))}
                placeholder={empresaId ? 'Selecione o PDV' : 'Escolha a empresa primeiro'}
                disabled={!empresaId}
              />
              {confirmacao ? <p className="text-sm text-slate-600 dark:text-slate-300">{confirmacao}</p> : null}
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <Button type="button" variant="cancel" onClick={() => setPeerAlvo(null)}>
                Cancelar
              </Button>
              {confirmacao ? (
                <Button type="button" loading={salvando} onClick={() => void confirmarVinculo(true)}>
                  Substituir ID
                </Button>
              ) : (
                <Button type="button" loading={salvando} onClick={() => void confirmarVinculo(false)}>
                  Vincular
                </Button>
              )}
            </div>
          </div>
        </div>
      ) : null}

      {acaoPendente ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{acaoPendente.titulo}</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{acaoPendente.texto}</p>
            <div className="mt-6 flex justify-end gap-2">
              <Button type="button" variant="cancel" onClick={() => setAcaoPendente(null)} disabled={salvando}>
                Cancelar
              </Button>
              <Button
                type="button"
                variant={acaoPendente.tipo === 'excluir' ? 'danger' : 'primary'}
                loading={salvando}
                onClick={() => void confirmarAcao()}
              >
                {acaoPendente.tipo === 'excluir' ? 'Excluir' : 'Desvincular'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </PageContainer>
  )
}
