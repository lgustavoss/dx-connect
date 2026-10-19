import { useEffect, useState } from 'react'
import { whatsappChats, type WhatsappChats } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'

type Props = {
  open: boolean
  onClose: () => void
  onEscolhida: (negociacaoId: number) => Promise<void>
}

export function WhatsappVincNegociacaoModal({ open, onClose, onEscolhida }: Props) {
  const [q, setQ] = useState('')
  const [itens, setItens] = useState<WhatsappChats.NegociacaoOpcao[]>([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [salvandoId, setSalvandoId] = useState<number | null>(null)
  const [consultaAberta, setConsultaAberta] = useState(false)

  if (open && !consultaAberta) {
    setConsultaAberta(true)
    setCarregando(true)
    setItens([])
    setErro(null)
  }
  if (!open && consultaAberta) {
    setConsultaAberta(false)
  }

  useEffect(() => {
    if (!open) return
    setQ('')
    setErro(null)
    let ativo = true
    setCarregando(true)
    whatsappChats
      .buscarNegociacoes('')
      .then((rows) => {
        if (ativo) setItens(rows)
      })
      .catch((e: unknown) => {
        if (ativo) setErro(mensagemFalhaParaToast(e, 'Não foi possível carregar as negociações.'))
      })
      .finally(() => {
        if (ativo) setCarregando(false)
      })
    return () => {
      ativo = false
    }
  }, [open])

  async function buscar() {
    setCarregando(true)
    setErro(null)
    try {
      setItens(await whatsappChats.buscarNegociacoes(q))
    } catch (e: unknown) {
      setErro(mensagemFalhaParaToast(e, 'Não foi possível buscar.'))
    } finally {
      setCarregando(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center">
      <div className="w-full max-w-lg rounded-2xl bg-white p-4 shadow-xl dark:bg-slate-900">
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Vincular à negociação</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Escolha um card em aberto. A empresa ainda não precisa existir.
        </p>
        <form
          className="mt-3 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            void buscar()
          }}
        >
          <div className="min-w-0 flex-1">
            <Input
              label="Buscar"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Nome, telefone ou título"
            />
          </div>
          <Button type="submit" variant="secondary" className="mt-6 shrink-0" disabled={carregando}>
            Buscar
          </Button>
        </form>
        {erro ? <p className="mt-2 text-sm text-red-600">{erro}</p> : null}
        <ul className="mt-3 max-h-64 space-y-2 overflow-y-auto">
          {carregando ? <li className="text-sm text-slate-500">Carregando…</li> : null}
          {!carregando && itens.length === 0 ? (
            <li className="text-sm text-slate-500">Nenhuma negociação em aberto.</li>
          ) : null}
          {itens.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-left text-sm hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:hover:bg-slate-800"
                disabled={salvandoId != null}
                onClick={() => {
                  setSalvandoId(item.id)
                  void onEscolhida(item.id)
                    .catch((e: unknown) => {
                      setErro(mensagemFalhaParaToast(e, 'Não foi possível vincular.'))
                    })
                    .finally(() => setSalvandoId(null))
                }}
              >
                <span className="font-medium text-slate-900 dark:text-slate-100">
                  {item.lead_nome || item.titulo || `Negociação #${item.id}`}
                </span>
                <span className="mt-0.5 block text-slate-500">
                  {[item.estagio_nome, item.lead_telefone, item.titulo].filter(Boolean).join(' · ')}
                </span>
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </div>
    </div>
  )
}
