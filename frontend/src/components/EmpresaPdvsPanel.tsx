import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, empresaPdvs, pdvRotulos, pdvTiposAcessoRemoto, type EmpresaPdv, type PdvCatalogo } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Button } from './ui/Button'
import { VoltarButton } from './ui/VoltarButton'
import { FormSection } from './ui/FormSection'
import { IconEye } from './ui/IconEye'
import { IconPencil } from './ui/IconPencil'
import { IconTrash } from './ui/IconTrash'
import { Input, TEXTAREA_FIELD_CLASS } from './ui/Input'
import { InlineCadastroFooter } from './ui/InlineCadastroPanel'
import { PasswordEyeToggle } from './ui/PasswordEyeToggle'
import { Select } from './ui/Select'
import { Switch } from './ui/Switch'
import { useToast } from './ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { useAuth } from '../contexts/AuthContext'
import { temPermissao } from '../lib/permissoes'
import { formatarIdRustdesk, tipoHospedadoNoServidor } from '../lib/rustdeskId'
import { conectarAcessoRemoto, senhaDoAcesso } from '../lib/acessoRemotoConectar'
import { IconeConectarRemoto } from './IconeConectarRemoto'

const MAX_ACESSOS = 10

function idFormatado(tipoNome: string | null | undefined, visto: boolean | undefined, id: string | null | undefined) {
  if (!tipoHospedadoNoServidor(tipoNome) && !visto) return id ?? ''
  return formatarIdRustdesk(id)
}

function acessosDaLinha(row: EmpresaPdv.Item): EmpresaPdv.Acesso[] {
  if (row.acessos && row.acessos.length > 0) return row.acessos
  if (!row.acesso_remoto_id && !row.tem_senha_remota && !row.tipo_acesso_remoto_id) return []
  return [
    {
      id: 0,
      tipo_acesso_remoto_id: row.tipo_acesso_remoto_id,
      tipo_acesso_remoto_nome: row.tipo_acesso_remoto_nome,
      acesso_remoto_id: row.acesso_remoto_id,
      tem_senha_remota: row.tem_senha_remota,
      pode_conectar: Boolean(row.acesso_remoto_id && tipoHospedadoNoServidor(row.tipo_acesso_remoto_nome)),
      rustdesk_visto: row.rustdesk_visto,
      rustdesk_online: row.rustdesk_online,
    },
  ]
}

function acessoParaConectar(row: EmpresaPdv.Item): EmpresaPdv.Acesso | undefined {
  return acessosDaLinha(row).find((a) => a.pode_conectar && a.acesso_remoto_id?.trim())
}

type AcessoForm = {
  key: string
  id?: number
  tipo_acesso_remoto_id: number | null
  acesso_remoto_id: string
  acesso_remoto_senha: string
}

type Props = {
  empresaId: number
  onEmpresaNome?: (nome: string) => void
  onIndisponivel?: () => void
  onFormAberto?: (aberto: boolean) => void
}

const emptyForm = (): EmpresaPdv.Create => ({
  codigo: '',
  rotulo_id: 0,
  papel: 'principal',
  usa_tef: false,
  observacoes: '',
  ativo: true,
})

function emptyAcesso(): AcessoForm {
  return { key: `n-${Date.now()}-${Math.random()}`, tipo_acesso_remoto_id: null, acesso_remoto_id: '', acesso_remoto_senha: '' }
}

function papelRotulo(papel: string) {
  return papel === 'auxiliar' ? 'Auxiliar' : 'Principal'
}

function SeloEstado({ ligado, sim, nao }: { ligado: boolean; sim: string; nao: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
        ligado
          ? 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-600/15 dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-600/30'
          : 'bg-rose-50 text-rose-800 ring-1 ring-rose-600/20 dark:bg-rose-950/40 dark:text-rose-300 dark:ring-rose-600/30'
      }`}
    >
      {ligado ? sim : nao}
    </span>
  )
}

function CampoSimNao({
  label,
  checked,
  onCheckedChange,
  onText,
  offText,
}: {
  label: string
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  onText: string
  offText: string
}) {
  return (
    <div className="min-w-0">
      <p className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">{label}</p>
      <div className="flex h-10 items-center gap-3">
        <Switch bare tight className="[&_label]:sr-only" checked={checked} onCheckedChange={onCheckedChange} label={label} />
        <span
          className={`text-sm font-medium ${
            checked ? 'text-emerald-700 dark:text-emerald-300' : 'text-slate-500 dark:text-slate-400'
          }`}
        >
          {checked ? onText : offText}
        </span>
      </div>
    </div>
  )
}

export function EmpresaPdvsPanel({ empresaId, onEmpresaNome, onIndisponivel, onFormAberto }: Props) {
  const toast = useToast()
  const { user } = useAuth()
  const podeVer = temPermissao(user, 'pdv.acessos.ver') || temPermissao(user, 'empresas.editar')
  const podeEditar = temPermissao(user, 'empresas.editar')
  const [items, setItems] = useState<EmpresaPdv.Item[]>([])
  const [loading, setLoading] = useState(true)
  const [rotulos, setRotulos] = useState<PdvCatalogo.Item[]>([])
  const [tipos, setTipos] = useState<PdvCatalogo.Item[]>([])
  const [tela, setTela] = useState<'lista' | 'form' | 'ver'>('lista')
  const [editId, setEditId] = useState<number | null>(null)
  const [acessosAbertos, setAcessosAbertos] = useState(true)
  const [form, setForm] = useState<EmpresaPdv.Create>(emptyForm())
  const [acessosForm, setAcessosForm] = useState<AcessoForm[]>([emptyAcesso()])
  const [saving, setSaving] = useState(false)
  const [senhaRevelada, setSenhaRevelada] = useState<{ chave: string; senha: string } | null>(null)
  const [revelandoChave, setRevelandoChave] = useState<string | null>(null)
  const [mostrarSenhaForm, setMostrarSenhaForm] = useState<Record<string, boolean>>({})
  const [conectandoChave, setConectandoChave] = useState<string | null>(null)
  const [detalhe, setDetalhe] = useState<EmpresaPdv.Item | null>(null)
  const topoRef = useRef<HTMLDivElement>(null)

  const load = useCallback(() => {
    setLoading(true)
    empresaPdvs
      .list(empresaId, { incluir_inativos: true })
      .then((r) => {
        setItems(r.items)
        onEmpresaNome?.(r.empresa_nome)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404 && onIndisponivel) {
          onIndisponivel()
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os PDVs.'))
      })
      .finally(() => setLoading(false))
  }, [empresaId, onEmpresaNome, onIndisponivel, toast])

  useEffect(() => {
    if (!podeVer) {
      setLoading(false)
      return
    }
    load()
    if (!podeEditar) return
    coletarTodasPaginas<PdvCatalogo.Item>((o, l) => pdvRotulos.list({ offset: o, limit: l })).then(setRotulos)
    coletarTodasPaginas<PdvCatalogo.Item>((o, l) => pdvTiposAcessoRemoto.list({ offset: o, limit: l })).then(setTipos)
  }, [load, podeVer, podeEditar])

  useEffect(() => {
    setTela('lista')
    setDetalhe(null)
  }, [empresaId])

  useEffect(() => {
    onFormAberto?.(tela !== 'lista')
    return () => onFormAberto?.(false)
  }, [tela, onFormAberto])

  useEffect(() => {
    if (tela === 'lista') return
    topoRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [tela, editId])

  function voltarLista() {
    setTela('lista')
    setDetalhe(null)
    setSenhaRevelada(null)
    setEditId(null)
  }

  function abrirNovo() {
    setEditId(null)
    setDetalhe(null)
    setForm({ ...emptyForm(), rotulo_id: rotulos[0]?.id ?? 0 })
    setAcessosForm([emptyAcesso()])
    setSenhaRevelada(null)
    setMostrarSenhaForm({})
    setTela('form')
  }

  function preencherForm(row: EmpresaPdv.Item) {
    setEditId(row.id)
    setForm({
      codigo: row.codigo,
      rotulo_id: row.rotulo_id,
      papel: row.papel,
      usa_tef: row.usa_tef,
      observacoes: row.observacoes ?? '',
      ativo: row.ativo,
    })
    const acessos = acessosDaLinha(row)
    setAcessosForm(
      acessos.length > 0
        ? acessos.map((a) => ({
            key: `a-${a.id}`,
            id: a.id || undefined,
            tipo_acesso_remoto_id: a.tipo_acesso_remoto_id ?? null,
            acesso_remoto_id: a.acesso_remoto_id ?? '',
            acesso_remoto_senha: '',
          }))
        : [emptyAcesso()],
    )
    setMostrarSenhaForm({})
  }

  function abrirVer(row: EmpresaPdv.Item) {
    setDetalhe(row)
    setEditId(row.id)
    setSenhaRevelada(null)
    setAcessosAbertos(true)
    setTela('ver')
  }

  function abrirEditar(row: EmpresaPdv.Item) {
    setDetalhe(row)
    preencherForm(row)
    setSenhaRevelada(null)
    setTela('form')
  }

  async function conectarAcesso(row: EmpresaPdv.Item, acesso: EmpresaPdv.Acesso, chave: string) {
    if (!acesso.pode_conectar || !acesso.acesso_remoto_id?.trim()) {
      toast.showWarning('Só o DeskRudder abre daqui. Nos outros programas, copie o ID e a senha.')
      return
    }
    setConectandoChave(chave)
    try {
      const { senha, avisou } = await senhaDoAcesso(empresaId, row.id, acesso.id > 0 ? acesso.id : null, toast)
      await conectarAcessoRemoto(acesso.acesso_remoto_id, senha, toast, avisou)
    } finally {
      setConectandoChave(null)
    }
  }

  async function copiarTexto(texto: string, sucesso: string) {
    try {
      await navigator.clipboard.writeText(texto)
      toast.showSuccess(sucesso)
    } catch {
      toast.showError('Não foi possível copiar. Selecione o texto manualmente.')
    }
  }

  async function salvar() {
    if (!form.codigo.trim() || !form.rotulo_id) {
      toast.showWarning('Informe o código e o rótulo do PDV.')
      return
    }
    const acessos: EmpresaPdv.AcessoWrite[] = acessosForm
      .filter((a) => a.tipo_acesso_remoto_id || a.acesso_remoto_id.trim() || a.acesso_remoto_senha.trim() || a.id)
      .map((a) => {
        const item: EmpresaPdv.AcessoWrite = {
          tipo_acesso_remoto_id: a.tipo_acesso_remoto_id,
          acesso_remoto_id: a.acesso_remoto_id.trim() || null,
        }
        if (a.id) item.id = a.id
        if (a.acesso_remoto_senha.trim() || !a.id) item.acesso_remoto_senha = a.acesso_remoto_senha.trim() || null
        return item
      })
    if (acessos.length > MAX_ACESSOS) {
      toast.showWarning(`No máximo ${MAX_ACESSOS} acessos remotos por PDV.`)
      return
    }
    setSaving(true)
    try {
      if (editId) {
        await empresaPdvs.update(empresaId, editId, {
          codigo: form.codigo.trim(),
          rotulo_id: form.rotulo_id,
          papel: form.papel,
          usa_tef: form.usa_tef,
          observacoes: form.observacoes || null,
          ativo: form.ativo,
          acessos,
        })
        toast.showSuccess('PDV atualizado.')
      } else {
        await empresaPdvs.create(empresaId, {
          ...form,
          codigo: form.codigo.trim(),
          observacoes: form.observacoes?.trim() || null,
          acessos,
        })
        toast.showSuccess('PDV cadastrado.')
      }
      voltarLista()
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o PDV.'))
    } finally {
      setSaving(false)
    }
  }

  function renderSeloOnline(acesso: Pick<EmpresaPdv.Acesso, 'rustdesk_online' | 'rustdesk_visto' | 'acesso_remoto_id' | 'tipo_acesso_remoto_nome' | 'pode_conectar'>) {
    if (!acesso.pode_conectar) return null
    if (acesso.rustdesk_online === true) {
      return (
        <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
          Online
        </span>
      )
    }
    if (acesso.rustdesk_online === false) {
      return (
        <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Offline
        </span>
      )
    }
    if (acesso.rustdesk_visto && acesso.rustdesk_online == null) {
      return <span className="text-[10px] text-slate-400">Sem sinal</span>
    }
    if (!acesso.rustdesk_visto && acesso.acesso_remoto_id && tipoHospedadoNoServidor(acesso.tipo_acesso_remoto_nome)) {
      return (
        <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-200">
          Fora do servidor
        </span>
      )
    }
    return null
  }

  function campoCopiavel(texto: string | null | undefined, vazio: string, aoClicar: () => void, carregando = false) {
    if (!texto) return <span className="text-slate-400">{vazio}</span>
    return (
      <button
        type="button"
        className="rounded-md font-mono tracking-wide text-slate-800 underline-offset-2 transition hover:underline dark:text-slate-100"
        title="Clique para copiar"
        disabled={carregando}
        onClick={aoClicar}
      >
        {carregando ? '…' : texto}
      </button>
    )
  }

  async function copiarSenha(pdvId: number, acesso: EmpresaPdv.Acesso, chave: string) {
    if (!acesso.tem_senha_remota || !podeVer) return
    if (senhaRevelada?.chave === chave) {
      await copiarTexto(senhaRevelada.senha, 'Senha copiada.')
      return
    }
    setRevelandoChave(chave)
    try {
      const r =
        acesso.id && acesso.id > 0
          ? await empresaPdvs.revelarCredencialAcesso(empresaId, pdvId, acesso.id)
          : await empresaPdvs.revelarCredencial(empresaId, pdvId)
      setSenhaRevelada({ chave, senha: r.acesso_remoto_senha })
      await copiarTexto(r.acesso_remoto_senha, 'Senha copiada.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível copiar a senha.'))
    } finally {
      setRevelandoChave(null)
    }
  }

  if (!podeVer) {
    return <p className="text-sm text-slate-500">Você não tem permissão para ver os PDVs desta empresa.</p>
  }

  if (tela === 'ver' && detalhe) {
    const acessos = acessosDaLinha(detalhe)
    const obs = detalhe.observacoes?.trim()
    return (
      <div ref={topoRef} className="scroll-mt-4 space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <VoltarButton onClick={voltarLista} label="Voltar à lista" />
            <div>
              <h3 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
                PDV {detalhe.codigo} - {papelRotulo(detalhe.papel)}
              </h3>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {detalhe.rotulo_nome ? (
                  <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-300/60 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-600/40">
                    {detalhe.rotulo_nome}
                  </span>
                ) : null}
                <SeloEstado ligado={!!detalhe.usa_tef} sim="Usa TEF" nao="Sem TEF" />
                <SeloEstado ligado={detalhe.ativo} sim="Ativo" nao="Inativo" />
              </div>
            </div>
          </div>
          {podeEditar ? (
            <Button type="button" onClick={() => abrirEditar(detalhe)}>
              Editar
            </Button>
          ) : null}
        </div>

        <FormSection
          title={
            acessos.length > 0 && !acessosAbertos
              ? `Acessos remotos · ${acessos.length}`
              : 'Acessos remotos'
          }
          description="DeskRudder abre direto do painel. Nos outros programas, clique no ID e na senha para copiar."
          expanded={acessosAbertos}
          onToggle={() => setAcessosAbertos((v) => !v)}
        >
          {acessos.length === 0 ? (
              <p className="text-sm text-slate-500">Nenhum acesso cadastrado.</p>
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                {acessos.map((acesso) => {
                  const chave = `ver-${detalhe.id}-${acesso.id}`
                  const nome = acesso.tipo_acesso_remoto_nome ?? 'Acesso remoto'
                  const idVisivel = acesso.acesso_remoto_id
                    ? idFormatado(acesso.tipo_acesso_remoto_nome, acesso.rustdesk_visto, acesso.acesso_remoto_id)
                    : null
                  const senhaVisivel =
                    senhaRevelada?.chave === chave ? senhaRevelada.senha : acesso.tem_senha_remota ? '••••••••' : null
                  return (
                    <div
                      key={chave}
                      className="space-y-2 rounded-xl border border-slate-200 bg-white/70 p-4 dark:border-slate-700 dark:bg-slate-950/40"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-slate-800 dark:text-slate-100">{nome}</p>
                        {renderSeloOnline(acesso)}
                      </div>
                      <p className="text-sm">
                        <span className="mr-2 text-slate-500">ID:</span>
                        {campoCopiavel(idVisivel, '—', () => void copiarTexto(idVisivel ?? '', 'ID de acesso copiado.'))}
                      </p>
                      <p className="text-sm">
                        <span className="mr-2 text-slate-500">Senha:</span>
                        {campoCopiavel(
                          senhaVisivel,
                          '—',
                          () => void copiarSenha(detalhe.id, acesso, chave),
                          revelandoChave === chave,
                        )}
                      </p>
                      {acesso.pode_conectar ? (
                        <Button
                          type="button"
                          variant="secondary"
                          className="mt-1"
                          disabled={conectandoChave === chave}
                          onClick={() => void conectarAcesso(detalhe, acesso, chave)}
                        >
                          {conectandoChave === chave ? 'Abrindo…' : 'Conectar'}
                        </Button>
                      ) : (
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          O painel não abre o {nome}. Clique no ID e na senha para copiar e cole no programa.
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
        </FormSection>

        <FormSection title="Observações">
          <p className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-200">
            {obs ? obs : <span className="text-slate-400">Nenhuma observação.</span>}
          </p>
        </FormSection>
      </div>
    )
  }

  if (tela === 'form') {
    const codigoTitulo = form.codigo.trim()
    const tituloForm = editId ? `Editar PDV${codigoTitulo ? ` ${codigoTitulo}` : ''}` : 'Novo PDV'
    return (
      <div ref={topoRef} className="scroll-mt-4">
      <form
        className="space-y-6"
        onSubmit={(e) => {
          e.preventDefault()
          void salvar()
        }}
      >
        <div className="space-y-2">
          <VoltarButton onClick={voltarLista} label="Voltar à lista" />
          <div>
            <h3 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{tituloForm}</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Cadastre o PDV e os programas usados para acessar este equipamento.
            </p>
          </div>
        </div>

        <FormSection
          title="Dados do PDV"
          description="O código identifica este PDV na empresa (ex.: 001), sem o prefixo PDV. O rótulo é o tipo de equipamento (SRV, PDV…)."
        >
          <div className="grid gap-4 sm:grid-cols-3">
            <Input
              label="Código"
              placeholder="001"
              value={form.codigo}
              onChange={(e) => setForm((f) => ({ ...f, codigo: e.target.value }))}
              required
            />
            <Select
              label="Rótulo"
              value={form.rotulo_id || ''}
              onChange={(v) => setForm((f) => ({ ...f, rotulo_id: Number(v) }))}
              options={rotulos.map((r) => ({ value: r.id, label: r.nome }))}
            />
            <Select
              label="Papel"
              value={form.papel}
              onChange={(v) => setForm((f) => ({ ...f, papel: v as 'principal' | 'auxiliar' }))}
              options={[
                { value: 'principal', label: 'Principal' },
                { value: 'auxiliar', label: 'Auxiliar' },
              ]}
            />
            <CampoSimNao
              label="Usa TEF"
              checked={!!form.usa_tef}
              onCheckedChange={(v) => setForm((f) => ({ ...f, usa_tef: v }))}
              onText="Sim"
              offText="Não"
            />
            <CampoSimNao
              label="PDV ativo"
              checked={form.ativo ?? true}
              onCheckedChange={(v) => setForm((f) => ({ ...f, ativo: v }))}
              onText="Ativo"
              offText="Inativo"
            />
          </div>
        </FormSection>

        <FormSection
          title="Acessos remotos"
          description="DeskRudder abre direto do painel. Nos outros programas, o atendente copia o ID e a senha."
          action={
            acessosForm.length < MAX_ACESSOS ? (
              <Button type="button" variant="secondary" onClick={() => setAcessosForm((lista) => [...lista, emptyAcesso()])}>
                Adicionar
              </Button>
            ) : null
          }
        >
          <div className="space-y-3">
            {acessosForm.map((acesso, idx) => {
              const tipoNome = tipos.find((t) => t.id === acesso.tipo_acesso_remoto_id)?.nome
              const conectar = tipoHospedadoNoServidor(tipoNome)
              return (
                <div
                  key={acesso.key}
                  className="rounded-xl border border-slate-200 bg-white/70 p-4 dark:border-slate-700 dark:bg-slate-950/40"
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                        {tipoNome || `Acesso ${idx + 1}`}
                      </p>
                      {conectar ? (
                        <span className="rounded-full bg-cyan-50 px-2 py-0.5 text-[11px] font-medium text-cyan-800 ring-1 ring-cyan-600/15 dark:bg-cyan-950/50 dark:text-cyan-200 dark:ring-cyan-500/25">
                          Abre no painel
                        </span>
                      ) : tipoNome ? (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 ring-1 ring-slate-300/60 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-600/40">
                          Copiar ID e senha
                        </span>
                      ) : null}
                    </div>
                    {acessosForm.length > 1 ? (
                      <Button
                        type="button"
                        variant="ghost"
                        className="!px-2 !py-2"
                        aria-label={`Remover ${tipoNome || `acesso ${idx + 1}`}`}
                        onClick={() => setAcessosForm((lista) => lista.filter((a) => a.key !== acesso.key))}
                      >
                        <IconTrash className="size-4" />
                      </Button>
                    ) : null}
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <Select
                      label="Ferramenta"
                      value={acesso.tipo_acesso_remoto_id ?? ''}
                      onChange={(v) =>
                        setAcessosForm((lista) =>
                          lista.map((a) =>
                            a.key === acesso.key ? { ...a, tipo_acesso_remoto_id: v === '' ? null : Number(v) } : a,
                          ),
                        )
                      }
                      includeEmpty
                      emptyLabel="Selecione"
                      options={tipos.map((t) => ({ value: t.id, label: t.nome }))}
                    />
                    <Input
                      label="ID"
                      value={acesso.acesso_remoto_id}
                      onChange={(e) =>
                        setAcessosForm((lista) =>
                          lista.map((a) => (a.key === acesso.key ? { ...a, acesso_remoto_id: e.target.value } : a)),
                        )
                      }
                    />
                    <Input
                      label="Senha"
                      hint={acesso.id ? 'Deixe vazio para manter a atual.' : undefined}
                      type={mostrarSenhaForm[acesso.key] ? 'text' : 'password'}
                      value={acesso.acesso_remoto_senha}
                      onChange={(e) =>
                        setAcessosForm((lista) =>
                          lista.map((a) => (a.key === acesso.key ? { ...a, acesso_remoto_senha: e.target.value } : a)),
                        )
                      }
                      autoComplete="new-password"
                      endAdornment={
                        <PasswordEyeToggle
                          visible={!!mostrarSenhaForm[acesso.key]}
                          onToggle={() => setMostrarSenhaForm((m) => ({ ...m, [acesso.key]: !m[acesso.key] }))}
                        />
                      }
                    />
                  </div>
                  {tipoNome && !conectar ? (
                    <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                      O painel não abre o {tipoNome}. Na consulta, clique no ID e na senha para copiar e colar no programa.
                    </p>
                  ) : null}
                </div>
              )
            })}
          </div>
        </FormSection>

        <FormSection title="Observações">
          <textarea
            id="pdv-observacoes"
            value={form.observacoes ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, observacoes: e.target.value }))}
            rows={3}
            placeholder="Opcional"
            aria-label="Observações"
            className={`!h-auto min-h-[5.5rem] resize-y py-2 ${TEXTAREA_FIELD_CLASS}`}
          />
        </FormSection>

        <InlineCadastroFooter onCancel={voltarLista} saving={saving} />
      </form>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          PDVs desta empresa. Clique na linha para ver os acessos remotos. O código (ex.: 001) identifica o PDV
          (único por empresa).
        </p>
        {podeEditar ? (
          <Button type="button" onClick={abrirNovo}>
            Novo PDV
          </Button>
        ) : null}
      </div>

      {loading && items.length === 0 ? (
        <p className="text-sm text-slate-500">Carregando PDVs…</p>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center dark:border-slate-600">
          <p className="text-sm text-slate-600 dark:text-slate-300">Nenhum PDV cadastrado.</p>
          {podeEditar ? (
            <Button type="button" className="mt-3" onClick={abrirNovo}>
              Cadastrar primeiro PDV
            </Button>
          ) : null}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40">
                <th className="px-4 py-3">Código</th>
                <th className="px-4 py-3">Rótulo</th>
                <th className="px-4 py-3">Papel</th>
                <th className="px-4 py-3">TEF</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {items.map((row) => {
                const conectar = acessoParaConectar(row)
                const chaveLista = `lista-${row.id}-${conectar?.id ?? 0}`
                return (
                  <tr
                    key={row.id}
                    className={`cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40 ${!row.ativo ? 'opacity-60' : ''}`}
                    onClick={() => abrirVer(row)}
                  >
                    <td className="px-4 py-3 font-mono font-medium">{row.codigo}</td>
                    <td className="px-4 py-3">{row.rotulo_nome ?? '—'}</td>
                    <td className="px-4 py-3 capitalize">{row.papel}</td>
                    <td className="px-4 py-3">{row.usa_tef ? 'Sim' : 'Não'}</td>
                    <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="inline-flex items-center justify-end gap-0.5">
                        {conectar?.acesso_remoto_id ? (
                          <button
                            type="button"
                            className="inline-flex size-8 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 disabled:pointer-events-none disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                            title="Conectar no DeskRudder"
                            aria-label={`Conectar ao PDV ${row.codigo}`}
                            disabled={conectandoChave === chaveLista}
                            onClick={() => void conectarAcesso(row, conectar, chaveLista)}
                          >
                            {conectandoChave === chaveLista ? (
                              <span className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                            ) : (
                              <IconeConectarRemoto />
                            )}
                          </button>
                        ) : null}
                        <Button
                          type="button"
                          variant="ghost"
                          className="!px-2 !py-2"
                          onClick={() => abrirVer(row)}
                          aria-label={`Ver PDV ${row.codigo}`}
                        >
                          <IconEye ariaHidden={false} />
                        </Button>
                        {podeEditar ? (
                          <Button
                            type="button"
                            variant="ghost"
                            className="!px-2 !py-2"
                            onClick={() => abrirEditar(row)}
                            aria-label={`Editar PDV ${row.codigo}`}
                          >
                            <IconPencil ariaHidden={false} />
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
