import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { whatsappChats, type WhatsappChats } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { useChatHub } from '../../contexts/ChatHubContext'
import { ChatIniciarConversaModal } from '../../components/chat/ChatIniciarConversaModal'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useToast } from '../../components/ui/Toast'

const PAGE = 40

export function ChatListaContatos() {
  const { busca } = useChatHub()
  const location = useLocation()
  const voltarPara = `${location.pathname}${location.search}`
  const toast = useToast()
  const [items, setItems] = useState<WhatsappChats.Contato[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const [modal, setModal] = useState<{
    contato?: WhatsappChats.Contato | null
    telefone?: string | null
    avulso?: boolean
  } | null>(null)

  const load = useCallback(
    async (from: number, append: boolean) => {
      setLoading(true)
      try {
        const res = await whatsappChats.contatos({
          busca: busca.trim() || undefined,
          offset: from,
          limit: PAGE,
        })
        setTotal(res.total)
        setOffset(from)
        setItems((prev) => (append ? [...prev, ...res.items] : res.items))
      } catch (err) {
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar contatos.'))
        if (!append) setItems([])
      } finally {
        setLoading(false)
      }
    },
    [busca, toast],
  )

  useEffect(() => {
    const t = window.setTimeout(() => void load(0, false), 250)
    return () => window.clearTimeout(t)
  }, [load])

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 border-b border-slate-100 px-3 py-2 dark:border-slate-800">
        <Button type="button" variant="secondary" className="h-8 w-full text-xs" onClick={() => setModal({ avulso: true })}>
          + Número avulso
        </Button>
      </div>

      {loading && items.length === 0 ? (
        <p className="p-4 text-center text-sm text-slate-400 animate-pulse">Carregando…</p>
      ) : items.length === 0 ? (
        <p className="p-6 text-center text-sm text-slate-400">
          {busca.trim() ? 'Nenhum contato encontrado.' : 'Nenhum contato cadastrado.'}
        </p>
      ) : (
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {items.map((c) => (
            <li key={c.id}>
              <Link
                to={`/funcionarios-rede/${c.id}`}
                state={{ voltarPara }}
                aria-label={`Ver detalhe de ${c.nome}`}
                className="flex items-start gap-3 px-3 py-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-900/50"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-200 text-sm font-bold text-slate-600 dark:bg-slate-700 dark:text-slate-200">
                  {c.nome.charAt(0)?.toUpperCase() || '?'}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">{c.nome}</p>
                  <div className="mt-0.5 flex flex-wrap gap-1">
                    {c.empresas.length > 0 ? (
                      c.empresas.map((e) => (
                        <span
                          key={e.id}
                          className="inline-flex max-w-[10rem] truncate rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                          title={e.nome}
                        >
                          {e.nome}
                        </span>
                      ))
                    ) : (
                      <span className="text-[10px] text-slate-400">{c.rede_nome || 'Sem empresa'}</span>
                    )}
                  </div>
                  <p className="mt-0.5 truncate font-mono text-[11px] text-slate-500">
                    {c.telefone || 'Sem WhatsApp'}
                  </p>
                </div>
              </Link>
              <div className="px-3 pb-3">
                <Button
                  type="button"
                  className="h-7 px-2 text-[10px]"
                  variant={c.telefone ? 'primary' : 'secondary'}
                  onClick={() => setModal({ contato: c })}
                >
                  {c.telefone ? 'Iniciar conversa' : 'Informar número'}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {items.length < total && (
        <div className="p-3">
          <Button
            type="button"
            variant="ghost"
            className="h-8 w-full text-xs"
            disabled={loading}
            onClick={() => void load(offset + PAGE, true)}
          >
            Carregar mais
          </Button>
        </div>
      )}

      <ChatIniciarConversaModal
        open={modal != null}
        onClose={() => setModal(null)}
        contato={modal?.contato}
        telefoneInicial={modal?.avulso ? '' : modal?.contato?.telefone}
        titulo={modal?.avulso ? 'Número avulso' : undefined}
      />
    </div>
  )
}
