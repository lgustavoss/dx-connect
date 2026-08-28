import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { whatsappChats, type WhatsappChats } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { SelectComPesquisa } from '../../components/ui/SelectComPesquisa'
import { CheckboxField } from '../../components/ui/CheckboxField'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { CONTATO_CLIENTE } from '../../constants/contatoClienteLabels'
import { useTicketsAbertosContato } from '../../hooks/useTicketsAbertosContato'

type Modo = 'vincular' | 'cadastrar'
type TipoCadastro = 'colaborador' | 'supervisor'
type EscopoCadastro = 'all' | 'selected'

type Props = {
  chat: WhatsappChats.Chat
  open: boolean
  onClose: () => void
  onSuccess: (chat: WhatsappChats.Chat) => void
}

export function WhatsappVincFuncionarioModal({ chat, open, onClose, onSuccess }: Props) {
  const toast = useToast()
  const { total: ticketsAbertosContato } = useTicketsAbertosContato(chat.funcionario_rede_id)
  const [modo, setModo] = useState<Modo>('vincular')
  const [salvando, setSalvando] = useState(false)

  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [resultados, setResultados] = useState<WhatsappChats.FuncionarioOpcao[]>([])
  const [loadingBusca, setLoadingBusca] = useState(false)
  const [erroBusca, setErroBusca] = useState<string | null>(null)
  const [selecionado, setSelecionado] = useState<WhatsappChats.FuncionarioOpcao | null>(null)
  const [empresaVinculoId, setEmpresaVinculoId] = useState<number | ''>('')

  const [catalogo, setCatalogo] = useState<WhatsappChats.FuncionarioCatalogo | null>(null)
  const [catalogoLoading, setCatalogoLoading] = useState(false)

  const [nomeCadastro, setNomeCadastro] = useState('')
  const [debouncedNomeCadastro, setDebouncedNomeCadastro] = useState('')
  const [similares, setSimilares] = useState<WhatsappChats.FuncionarioOpcao[]>([])
  const [loadingSimilares, setLoadingSimilares] = useState(false)
  const [emailCadastro, setEmailCadastro] = useState('')
  const [tipoCadastro, setTipoCadastro] = useState<TipoCadastro>('colaborador')
  const [escopoCadastro, setEscopoCadastro] = useState<EscopoCadastro>('selected')
  const [redeIdCadastro, setRedeIdCadastro] = useState<number | ''>('')
  const [empresaIdCadastro, setEmpresaIdCadastro] = useState<number | ''>('')
  const [empresaIdsCadastro, setEmpresaIdsCadastro] = useState<number[]>([])
  const [empresaContextoId, setEmpresaContextoId] = useState<number | ''>('')
  const [erroFormulario, setErroFormulario] = useState<string | null>(null)

  const empresaItemsVincular = useMemo(
    () => (selecionado?.empresas ?? []).map((e) => ({ id: e.id, label: e.nome })),
    [selecionado],
  )

  const empresasDaRede = useMemo(
    () =>
      (catalogo?.empresas ?? []).filter(
        (e) => redeIdCadastro !== '' && e.rede_id === Number(redeIdCadastro),
      ),
    [catalogo, redeIdCadastro],
  )

  const empresasContextoOpcoes = useMemo(() => {
    if (escopoCadastro === 'all') return empresasDaRede
    if (tipoCadastro === 'colaborador' && empresaIdCadastro !== '') {
      const emp = empresasDaRede.find((e) => e.id === Number(empresaIdCadastro))
      return emp ? [emp] : []
    }
    return empresasDaRede.filter((e) => empresaIdsCadastro.includes(e.id))
  }, [empresaIdCadastro, empresaIdsCadastro, empresasDaRede, escopoCadastro, tipoCadastro])

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(timer)
  }, [busca])

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedNomeCadastro(nomeCadastro.trim()), 450)
    return () => clearTimeout(timer)
  }, [nomeCadastro])

  useEffect(() => {
    if (!open) return
    setModo('vincular')
    setBusca('')
    setDebouncedBusca('')
    setResultados([])
    setErroBusca(null)
    setSelecionado(null)
    setEmpresaVinculoId('')
    setNomeCadastro(chat.cliente_nome?.trim() || '')
    setDebouncedNomeCadastro('')
    setSimilares([])
    setEmailCadastro('')
    setTipoCadastro('colaborador')
    setEscopoCadastro('selected')
    setRedeIdCadastro('')
    setEmpresaIdCadastro('')
    setEmpresaIdsCadastro([])
    setEmpresaContextoId('')
    setErroFormulario(null)
    setCatalogoLoading(true)
    whatsappChats
      .catalogoFuncionarios()
      .then((data) => {
        setCatalogo(data)
        if (data.redes.length === 1) setRedeIdCadastro(data.redes[0].id)
      })
      .catch((err) => {
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar redes e empresas.'))
      })
      .finally(() => setCatalogoLoading(false))
  }, [chat.cliente_nome, chat.id, open, toast])

  useEffect(() => {
    if (!open || modo !== 'vincular' || !debouncedBusca) {
      setResultados([])
      setErroBusca(null)
      return
    }
    setLoadingBusca(true)
    setErroBusca(null)
    whatsappChats
      .buscarFuncionarios(debouncedBusca)
      .then(setResultados)
      .catch((err) => {
        setResultados([])
        setErroBusca(mensagemFalhaParaToast(err, 'Não foi possível buscar contatos da rede.'))
      })
      .finally(() => setLoadingBusca(false))
  }, [debouncedBusca, modo, open])

  useEffect(() => {
    if (!open || modo !== 'cadastrar' || debouncedNomeCadastro.length < 3) {
      setSimilares([])
      setLoadingSimilares(false)
      return
    }
    let cancelled = false
    setLoadingSimilares(true)
    whatsappChats
      .buscarFuncionariosSimilares(debouncedNomeCadastro, 5)
      .then((rows) => {
        if (!cancelled) setSimilares(rows)
      })
      .catch(() => {
        if (!cancelled) setSimilares([])
      })
      .finally(() => {
        if (!cancelled) setLoadingSimilares(false)
      })
    return () => {
      cancelled = true
    }
  }, [debouncedNomeCadastro, modo, open])

  useEffect(() => {
    if (!selecionado) {
      setEmpresaVinculoId('')
      return
    }
    if (selecionado.empresas.length === 1) setEmpresaVinculoId(selecionado.empresas[0].id)
    else setEmpresaVinculoId('')
  }, [selecionado])

  useEffect(() => {
    setEmpresaIdCadastro('')
    setEmpresaIdsCadastro([])
    setEmpresaContextoId('')
  }, [redeIdCadastro, tipoCadastro, escopoCadastro])

  useEffect(() => {
    if (empresasContextoOpcoes.length === 1) {
      setEmpresaContextoId(empresasContextoOpcoes[0].id)
    } else if (
      empresaContextoId !== '' &&
      !empresasContextoOpcoes.some((e) => e.id === Number(empresaContextoId))
    ) {
      setEmpresaContextoId('')
    }
  }, [empresaContextoId, empresasContextoOpcoes])

  if (!open) return null

  function toggleEmpresaCadastro(id: number) {
    setEmpresaIdsCadastro((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  function vincularSugestao(funcionario: WhatsappChats.FuncionarioOpcao) {
    setSelecionado(funcionario)
    setBusca(funcionario.nome)
    setDebouncedBusca(funcionario.nome)
    setResultados([funcionario])
    setErroFormulario(null)
    setModo('vincular')
  }

  async function confirmarVinculo() {
    if (!selecionado) {
      setErroFormulario(CONTATO_CLIENTE.selecioneContato)
      return
    }
    if (selecionado.empresas.length > 1 && empresaVinculoId === '') {
      setErroFormulario(CONTATO_CLIENTE.selecioneEmpresaContato)
      return
    }
    setErroFormulario(null)
    setSalvando(true)
    try {
      const atualizado = await whatsappChats.vincularFuncionario(chat.id, {
        funcionario_rede_id: selecionado.id,
        empresa_id: empresaVinculoId === '' ? null : Number(empresaVinculoId),
      })
      toast.showSuccess(CONTATO_CLIENTE.vinculadoSucesso)
      onSuccess(atualizado)
      onClose()
    } catch (err) {
      setErroFormulario(mensagemFalhaParaToast(err, 'Não foi possível vincular o contato.'))
    } finally {
      setSalvando(false)
    }
  }

  async function confirmarCadastro() {
    if (!nomeCadastro.trim()) {
      setErroFormulario(CONTATO_CLIENTE.informeNome)
      return
    }
    if (redeIdCadastro === '') {
      setErroFormulario('Selecione a rede.')
      return
    }
    let empresaIds: number[] = []
    if (escopoCadastro === 'selected') {
      if (tipoCadastro === 'colaborador') {
        if (empresaIdCadastro === '') {
          setErroFormulario('Selecione a empresa.')
          return
        }
        empresaIds = [Number(empresaIdCadastro)]
      } else if (empresaIdsCadastro.length === 0) {
        setErroFormulario('Marque ao menos uma empresa.')
        return
      } else {
        empresaIds = [...empresaIdsCadastro]
      }
    }
    if (empresasContextoOpcoes.length > 1 && empresaContextoId === '') {
      setErroFormulario('Selecione a empresa exibida no chat.')
      return
    }
    setErroFormulario(null)
    setSalvando(true)
    try {
      const emailTrim = emailCadastro.trim()
      const atualizado = await whatsappChats.cadastrarFuncionario(chat.id, {
        nome: nomeCadastro.trim(),
        email: emailTrim || null,
        rede_id: Number(redeIdCadastro),
        tipo: tipoCadastro,
        escopo_empresas: escopoCadastro,
        empresa_ids: empresaIds,
        empresa_id: empresaContextoId === '' ? null : Number(empresaContextoId),
      })
      toast.showSuccess(CONTATO_CLIENTE.cadastradoSucesso)
      onSuccess(atualizado)
      onClose()
    } catch (err) {
      setErroFormulario(mensagemFalhaParaToast(err, 'Não foi possível cadastrar o contato.'))
    } finally {
      setSalvando(false)
    }
  }

  async function desvincular() {
    setSalvando(true)
    try {
      const atualizado = await whatsappChats.desvincularFuncionario(chat.id)
      toast.showSuccess(CONTATO_CLIENTE.desvinculadoSucesso)
      onSuccess(atualizado)
      onClose()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível desvincular o contato.'))
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-slate-900/50 p-0 backdrop-blur-sm md:items-center md:p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <Card className="max-h-[min(90dvh,var(--vv-height,90dvh))] w-full max-w-lg overflow-y-auto rounded-t-2xl rounded-b-none p-6 md:rounded-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold">{CONTATO_CLIENTE.modalTitulo}</h3>
            <p className="mt-1 text-sm text-slate-500">{CONTATO_CLIENTE.modalSubtitulo}</p>
          </div>
          <button
            type="button"
            className="text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
            onClick={onClose}
          >
            &times;
          </button>
        </div>

        {chat.funcionario_rede_id && (
          <div className="mt-4 rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm dark:border-cyan-900/50 dark:bg-cyan-950/30">
            <p className="font-semibold text-cyan-900 dark:text-cyan-100">
              Vínculo atual: {chat.funcionario_nome}
            </p>
            {chat.empresa_nome && (
              <p className="mt-0.5 text-xs text-cyan-800/80 dark:text-cyan-200/80">{chat.empresa_nome}</p>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              <Link
                to={`/funcionarios-rede/${chat.funcionario_rede_id}?aba=chats`}
                state={{ voltarPara: window.location.pathname + window.location.search }}
                className="text-xs font-medium text-cyan-700 underline dark:text-cyan-300"
              >
                Ver histórico de chats
              </Link>
              {ticketsAbertosContato != null && ticketsAbertosContato > 0 ? (
                <Link
                  to={`/funcionarios-rede/${chat.funcionario_rede_id}?aba=tickets`}
                  state={{ voltarPara: window.location.pathname + window.location.search }}
                  className="text-xs font-medium text-amber-800 underline dark:text-amber-200"
                >
                  {ticketsAbertosContato} ticket{ticketsAbertosContato === 1 ? '' : 's'} aberto
                  {ticketsAbertosContato === 1 ? '' : 's'}
                </Link>
              ) : null}
              <button
                type="button"
                className="text-xs font-medium text-red-600 underline"
                onClick={() => void desvincular()}
                disabled={salvando}
              >
                Remover vínculo
              </button>
            </div>
          </div>
        )}

        <div className="mt-4 flex gap-2 rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
          <button
            type="button"
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              modo === 'vincular'
                ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white'
                : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
            onClick={() => {
              setModo('vincular')
              setErroFormulario(null)
            }}
          >
            Vincular existente
          </button>
          <button
            type="button"
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              modo === 'cadastrar'
                ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white'
                : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
            onClick={() => {
              setModo('cadastrar')
              setErroFormulario(null)
            }}
          >
            Cadastrar novo
          </button>
        </div>

        {erroFormulario && (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100"
          >
            {erroFormulario}
          </div>
        )}

        {modo === 'vincular' ? (
          <div className="mt-4 space-y-4">
            <Input
              placeholder={CONTATO_CLIENTE.buscarPlaceholder}
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
            {erroBusca && <p className="text-xs text-amber-500">{erroBusca}</p>}
            {loadingBusca ? (
              <p className="text-sm text-slate-500">Buscando...</p>
            ) : debouncedBusca ? (
              resultados.length > 0 ? (
                <div className="max-h-56 overflow-y-auto divide-y divide-slate-200 rounded-xl border border-slate-200 bg-slate-50 p-1 dark:divide-slate-700 dark:border-slate-800 dark:bg-slate-900">
                  {resultados.map((funcionario) => (
                    <button
                      key={funcionario.id}
                      type="button"
                      onClick={() => setSelecionado(funcionario)}
                      className={`w-full text-left px-4 py-3 transition-colors ${
                        selecionado?.id === funcionario.id
                          ? 'bg-cyan-100 dark:bg-cyan-950/50'
                          : 'hover:bg-white dark:hover:bg-slate-800'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-slate-900 dark:text-slate-100">{funcionario.nome}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {funcionario.email || 'Sem e-mail'}
                          </p>
                          <div className="mt-1 flex flex-wrap items-center gap-1">
                            {funcionario.rede_nome && (
                              <span
                                className="inline-flex max-w-full truncate rounded-md bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-800 dark:bg-violet-950/50 dark:text-violet-200"
                                title={funcionario.rede_nome}
                              >
                                {funcionario.rede_nome}
                              </span>
                            )}
                            {funcionario.empresas.length > 0 ? (
                              funcionario.empresas.map((e) => (
                                <span
                                  key={e.id}
                                  className="inline-flex max-w-[10rem] truncate rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                                  title={e.nome}
                                >
                                  {e.nome}
                                </span>
                              ))
                            ) : (
                              !funcionario.rede_nome && (
                                <span className="text-[10px] text-slate-400">Sem empresa</span>
                              )
                            )}
                          </div>
                        </div>
                        <span className="shrink-0 text-xs uppercase tracking-wide text-slate-400">
                          {funcionario.tipo}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  Nenhum contato encontrado. Use a aba <strong>Cadastrar novo</strong>.
                </p>
              )
            ) : (
              <p className="text-sm text-slate-500">{CONTATO_CLIENTE.digiteParaBuscar}</p>
            )}
            {selecionado && selecionado.empresas.length > 1 && (
              <SelectComPesquisa
                label="Empresa no chat"
                items={empresaItemsVincular}
                value={empresaVinculoId}
                onChange={(id) => setEmpresaVinculoId(id)}
                placeholder="Selecione a empresa"
                menuPlacement="inline"
              />
            )}
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            {catalogoLoading ? (
              <p className="text-sm text-slate-500">Carregando redes e empresas...</p>
            ) : (
              <>
                <Input
                  label="Nome"
                  value={nomeCadastro}
                  onChange={(e) => setNomeCadastro(e.target.value)}
                  required
                />
                {loadingSimilares && debouncedNomeCadastro.length >= 3 && (
                  <p className="text-xs text-slate-500">A procurar nomes semelhantes…</p>
                )}
                {!loadingSimilares && similares.length > 0 && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50/80 px-3 py-3 dark:border-amber-900/50 dark:bg-amber-950/25">
                    <p className="text-sm font-medium text-amber-950 dark:text-amber-100">
                      Encontrámos cadastros com nome semelhante
                    </p>
                    <p className="mt-0.5 text-xs text-amber-800/90 dark:text-amber-200/80">
                      Prefira vincular ao existente para evitar duplicados. Pode ignorar e cadastrar um novo.
                    </p>
                    {similares.some((s) => s.similaridade_alta) && (
                      <p className="mt-2 text-xs font-medium text-amber-900 dark:text-amber-100">
                        Atenção: há correspondência muito próxima (quase o mesmo nome).
                      </p>
                    )}
                    <ul className="mt-3 max-h-40 space-y-2 overflow-y-auto">
                      {similares.map((funcionario) => (
                        <li
                          key={funcionario.id}
                          className="rounded-lg border border-amber-200/80 bg-white/80 px-3 py-2 dark:border-amber-900/40 dark:bg-slate-900/60"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                                {funcionario.nome}
                              </p>
                              <p className="truncate text-xs text-slate-500">
                                {funcionario.email || funcionario.telefone || 'Sem e-mail/telefone'}
                              </p>
                              <div className="mt-1 flex flex-wrap gap-1">
                                {funcionario.rede_nome && (
                                  <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-800 dark:bg-violet-950/50 dark:text-violet-200">
                                    {funcionario.rede_nome}
                                  </span>
                                )}
                                {funcionario.empresas.map((e) => (
                                  <span
                                    key={e.id}
                                    className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                                  >
                                    {e.nome}
                                  </span>
                                ))}
                              </div>
                            </div>
                            <Button
                              type="button"
                              variant="secondary"
                              className="h-8 shrink-0 px-2 text-xs"
                              onClick={() => vincularSugestao(funcionario)}
                            >
                              Vincular a este cadastro
                            </Button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <Input
                  label="E-mail (opcional)"
                  type="email"
                  value={emailCadastro}
                  onChange={(e) => {
                    setEmailCadastro(e.target.value)
                    setErroFormulario(null)
                  }}
                />
                <p className="text-xs text-slate-500">
                  Usado para tickets por e-mail; contatos só WhatsApp podem deixar em branco.
                </p>
                <p className="text-xs text-slate-500">
                  WhatsApp do contato: <span className="font-mono">{chat.wa_id}</span>
                </p>
                <Select
                  label="Tipo"
                  value={tipoCadastro}
                  onChange={(v) => {
                    setTipoCadastro(v as TipoCadastro)
                    setEscopoCadastro('selected')
                  }}
                  options={[
                    { value: 'colaborador', label: 'Colaborador (uma empresa)' },
                    { value: 'supervisor', label: 'Supervisor (várias empresas)' },
                  ]}
                />
                <SelectComPesquisa
                  label="Rede"
                  value={redeIdCadastro}
                  onChange={(id) => setRedeIdCadastro(id)}
                  items={(catalogo?.redes ?? []).map((r) => ({ id: r.id, label: r.nome }))}
                  placeholder="Selecione a rede"
                  required
                  menuPlacement="inline"
                />
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Escopo de empresas</p>
                  <label className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="radio"
                      checked={escopoCadastro === 'selected'}
                      onChange={() => setEscopoCadastro('selected')}
                    />
                    Selecionar empresa(s)
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="radio"
                      checked={escopoCadastro === 'all'}
                      onChange={() => {
                        setEscopoCadastro('all')
                        setEmpresaIdCadastro('')
                        setEmpresaIdsCadastro([])
                      }}
                    />
                    Todas as empresas da rede
                  </label>
                </div>
                {escopoCadastro === 'selected' && redeIdCadastro !== '' && (
                  <>
                    {tipoCadastro === 'colaborador' ? (
                      <SelectComPesquisa
                        label="Empresa"
                        value={empresaIdCadastro}
                        onChange={(id) => setEmpresaIdCadastro(id)}
                        items={empresasDaRede.map((e) => ({ id: e.id, label: e.nome }))}
                        placeholder="Selecione a empresa"
                        required
                        menuPlacement="inline"
                      />
                    ) : empresasDaRede.length > 0 ? (
                      <div className="flex max-h-40 flex-wrap gap-2 overflow-auto rounded-xl border border-slate-200 bg-slate-50/40 p-3 dark:border-slate-800 dark:bg-slate-800/40">
                        {empresasDaRede.map((e) => (
                          <CheckboxField
                            key={e.id}
                            checked={empresaIdsCadastro.includes(e.id)}
                            onChange={() => toggleEmpresaCadastro(e.id)}
                          >
                            {e.nome}
                          </CheckboxField>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">Nenhuma empresa ativa nesta rede.</p>
                    )}
                  </>
                )}
                {empresasContextoOpcoes.length > 1 && (
                  <SelectComPesquisa
                    label="Empresa exibida no chat"
                    value={empresaContextoId}
                    onChange={(id) => setEmpresaContextoId(id)}
                    items={empresasContextoOpcoes.map((e) => ({ id: e.id, label: e.nome }))}
                    placeholder="Selecione a empresa de contexto"
                    required
                    menuPlacement="inline"
                  />
                )}
              </>
            )}
          </div>
        )}

        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Button variant="cancel" onClick={onClose} disabled={salvando}>
            Cancelar
          </Button>
          {modo === 'vincular' ? (
            <Button onClick={() => void confirmarVinculo()} loading={salvando} disabled={!selecionado}>
              Vincular
            </Button>
          ) : (
            <Button onClick={() => void confirmarCadastro()} loading={salvando} disabled={catalogoLoading}>
              Cadastrar e vincular
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}
