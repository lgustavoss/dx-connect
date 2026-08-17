import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, tickets, type Tickets } from '../../api/client'
import { Button } from '../ui/Button'
import { CheckboxField } from '../ui/CheckboxField'
import { Input } from '../ui/Input'
import { useToast } from '../ui/Toast'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import { marcarTicketAtivo, TICKETS_PATH } from '../../lib/ticketAtivo'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

interface Props {
  ticketId: number
  disabled?: boolean
  onCriados: () => void | Promise<void>
}

export function TicketFilhosMassaPanel({ ticketId, disabled, onCriados }: Props) {
  const toast = useToast()
  const [opcoes, setOpcoes] = useState<Tickets.FilhosMassaOpcoes | null>(null)
  const [carregandoOpcoes, setCarregandoOpcoes] = useState(true)
  const [erroOpcoes, setErroOpcoes] = useState<string | null>(null)
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set())
  const [assunto, setAssunto] = useState('')
  const [descricao, setDescricao] = useState('')
  const [criando, setCriando] = useState(false)
  const [ultimosCriados, setUltimosCriados] = useState<Tickets.FilhoMassaCriado[]>([])

  const elegiveis = useMemo(
    () => opcoes?.empresas.filter((e) => !e.ja_tem_filho) ?? [],
    [opcoes],
  )

  const carregarOpcoes = useCallback(async () => {
    setCarregandoOpcoes(true)
    setErroOpcoes(null)
    try {
      const data = await tickets.filhosMassaOpcoes(ticketId)
      setOpcoes(data)
      setAssunto(data.assunto_padrao)
      setDescricao(data.descricao_padrao ?? '')
      const ids = data.empresas.filter((e) => !e.ja_tem_filho).map((e) => e.id)
      setSelecionados(new Set(ids))
      setUltimosCriados([])
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : mensagemFalhaParaToast(err, 'Não foi possível carregar as empresas.')
      setErroOpcoes(msg)
      setOpcoes(null)
    } finally {
      setCarregandoOpcoes(false)
    }
  }, [ticketId])

  useEffect(() => {
    void carregarOpcoes()
  }, [carregarOpcoes])

  const toggleEmpresa = (id: number) => {
    setSelecionados((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selecionarTodos = () => setSelecionados(new Set(elegiveis.map((e) => e.id)))
  const limparSelecao = () => setSelecionados(new Set())

  const handleCriar = async () => {
    if (selecionados.size === 0) {
      toast.showWarning('Selecione ao menos uma empresa.')
      return
    }
    const assuntoTrim = assunto.trim()
    if (!assuntoTrim) {
      toast.showWarning('Informe o assunto dos tickets filhos.')
      return
    }
    setCriando(true)
    try {
      const res = await tickets.criarFilhosMassa(ticketId, {
        empresa_ids: Array.from(selecionados),
        assunto: assuntoTrim,
        descricao: descricao.trim() || null,
      })
      setUltimosCriados(res.criados)
      toast.showSuccess(`${res.total} ticket${res.total === 1 ? '' : 's'} filho${res.total === 1 ? '' : 's'} criado${res.total === 1 ? '' : 's'}.`)
      await onCriados()
      await carregarOpcoes()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível criar os tickets filhos.'))
    } finally {
      setCriando(false)
    }
  }

  if (carregandoOpcoes) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Carregando empresas da rede…</p>
  }

  if (erroOpcoes) {
    return <p className="text-sm text-amber-700 dark:text-amber-400">{erroOpcoes}</p>
  }

  if (!opcoes) return null

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Rede: <span className="font-medium text-slate-700 dark:text-slate-200">{opcoes.rede_nome ?? `#${opcoes.rede_id}`}</span>
        {' · '}
        Um ticket filho será aberto para cada empresa selecionada, vinculado a este ticket pai.
      </p>

      <Input
        label="Assunto dos filhos"
        value={assunto}
        onChange={(e) => setAssunto(e.target.value)}
        disabled={disabled || criando}
      />

      <label className="block text-sm">
        <span className="mb-1 block font-medium text-slate-700 dark:text-slate-200">Descrição dos filhos</span>
        <textarea
          className="min-h-[72px] w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-500/30 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          value={descricao}
          onChange={(e) => setDescricao(e.target.value)}
          disabled={disabled || criando}
          rows={3}
        />
      </label>

      <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Empresas ({selecionados.size}/{elegiveis.length} selecionadas)
          </p>
          {elegiveis.length > 1 && (
            <div className="flex gap-2">
              <Button type="button" variant="ghost" className="px-2 py-1 text-xs" disabled={disabled || criando} onClick={selecionarTodos}>
                Todas
              </Button>
              <Button type="button" variant="ghost" className="px-2 py-1 text-xs" disabled={disabled || criando} onClick={limparSelecao}>
                Nenhuma
              </Button>
            </div>
          )}
        </div>

        {elegiveis.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Todas as empresas ativas desta rede já possuem ticket filho vinculado.
          </p>
        ) : (
          <div className="mt-2 flex max-h-48 flex-wrap gap-2 overflow-y-auto">
            {opcoes.empresas.map((emp) => (
              <CheckboxField
                key={emp.id}
                checked={selecionados.has(emp.id)}
                disabled={disabled || criando || emp.ja_tem_filho}
                onChange={() => toggleEmpresa(emp.id)}
              >
                {emp.nome}
                {emp.ja_tem_filho ? ' (já tem filho)' : ''}
              </CheckboxField>
            ))}
          </div>
        )}
      </div>

      {ultimosCriados.length > 0 && (
        <ul className="rounded-lg border border-emerald-200 bg-emerald-50/80 px-3 py-2 text-sm dark:border-emerald-900/50 dark:bg-emerald-950/30">
          {ultimosCriados.map((c) => (
            <li key={c.id}>
              <Link
                to={TICKETS_PATH}
                onClick={() => marcarTicketAtivo(c.id)}
                className="font-medium text-emerald-800 underline hover:text-emerald-950 dark:text-emerald-300 dark:hover:text-emerald-200"
              >
                {exibirProtocolo(c.protocolo)}
              </Link>
              <span className="text-emerald-700 dark:text-emerald-400"> — {c.empresa_nome}</span>
            </li>
          ))}
        </ul>
      )}

      <Button
        type="button"
        variant="primary"
        loading={criando}
        disabled={disabled || elegiveis.length === 0 || selecionados.size === 0}
        onClick={() => void handleCriar()}
      >
        Criar {selecionados.size > 0 ? selecionados.size : ''} ticket{selecionados.size === 1 ? '' : 's'} filho
        {selecionados.size === 1 ? '' : 's'}
      </Button>
    </div>
  )
}
