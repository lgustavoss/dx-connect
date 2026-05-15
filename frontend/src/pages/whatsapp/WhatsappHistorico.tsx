import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { whatsappChats, type WhatsappChats } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { exibirProtocolo } from '../../lib/exibirProtocolo'

const PAGE_SIZE = 15 // Reduzi para 15 para melhorar o fôlego da página em listas longas

export function WhatsappHistorico() {
  const toast = useToast()
  const [items, setItems] = useState<WhatsappChats.Chat[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busca, setBusca] = useState('')

  const load = useCallback(async (from: number) => {
    setLoading(true)
    try {
      // Nota: Se seu backend suportar busca, você passaria o termo aqui
      const { items: rows, total: t } = await whatsappChats.encerrados({ 
        offset: from, 
        limit: PAGE_SIZE 
      })
      setItems(rows)
      setTotal(t)
      setOffset(from)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao carregar histórico.'))
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    void load(0)
  }, [load])

  // Cálculo de páginas
  const paginaAtual = Math.floor(offset / PAGE_SIZE) + 1
  const totalPaginas = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="flex flex-col space-y-8 animate-in fade-in duration-500 pb-10">
      
      {/* Header com Filtros Rápidos */}
      <header className="flex flex-col gap-6 border-b pb-6 dark:border-slate-800 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Histórico de Mensagens</h1>
          <p className="text-sm text-slate-500">Consulte atendimentos finalizados e protocolos antigos.</p>
        </div>

        <div className="flex flex-1 max-w-md gap-2">
          <div className="relative flex-1">
            <Input 
              placeholder="Buscar por nome, telefone ou protocolo (ex.: #C202604-0001)…" 
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-10"
            />
            <span className="absolute left-3 top-2.5 text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            </span>
          </div>
          <Button variant="secondary" onClick={() => void load(0)}>Filtrar</Button>
        </div>
      </header>

      {/* Tabela de Resultados (Cards) */}
      <div className="space-y-4">
        {loading && items.length === 0 ? (
          // Skeletons
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 w-full animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ))
        ) : items.length === 0 ? (
          <Card className="flex flex-col items-center justify-center border-dashed border-2 py-16 text-center">
            <div className="rounded-full bg-slate-50 p-4 dark:bg-slate-900/50">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-300"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8"/><path d="M8 13h6"/></svg>
            </div>
            <h3 className="mt-4 font-semibold text-slate-900 dark:text-slate-100">Nenhum registro encontrado</h3>
            <p className="text-sm text-slate-500">Tente ajustar seus termos de busca.</p>
          </Card>
        ) : (
          <div className="grid gap-3">
            {items.map((c) => (
              <Card key={c.id} className="group border-none p-4 shadow-sm ring-1 ring-slate-200 transition-all hover:ring-cyan-500/50 dark:ring-slate-800">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  
                  {/* Info do Cliente e Protocolo */}
                  <div className="flex min-w-[240px] flex-1 items-center gap-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-50 text-slate-400 group-hover:bg-cyan-50 group-hover:text-cyan-600 dark:bg-slate-900 dark:group-hover:bg-cyan-900/20 transition-colors">
                      <span className="text-sm font-bold">{c.cliente_nome?.charAt(0).toUpperCase() || 'C'}</span>
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="truncate font-bold text-slate-900 dark:text-slate-100">{c.cliente_nome || 'Cliente'}</h3>
                        <span className="font-mono text-[10px] font-bold text-slate-400">{c.wa_id}</span>
                      </div>
                      <p
                        className="truncate font-mono text-xs font-bold text-cyan-600 dark:text-cyan-400"
                        title={exibirProtocolo(c.protocolo)}
                      >
                        {exibirProtocolo(c.protocolo)}
                      </p>
                    </div>
                  </div>

                  {/* Metadados: Atendente e Data */}
                  <div className="flex items-center gap-8">
                    <div className="hidden text-right sm:block">
                      <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Atendido por</p>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-300">{c.atendente_nome || 'Sistema'}</p>
                    </div>
                    
                    <div className="text-right">
                      <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Finalizado em</p>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                        {c.encerramento_at ? new Date(c.encerramento_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                      </p>
                    </div>

                    <Link
                      to={`/whatsapp/c/${c.id}`}
                      className="rounded-full bg-slate-100 p-2 text-slate-400 transition-all hover:bg-cyan-600 hover:text-white dark:bg-slate-800 dark:hover:bg-cyan-700"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                    </Link>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Paginação Estilizada */}
      <footer className="flex flex-col items-center justify-between gap-4 border-t pt-6 dark:border-slate-800 sm:flex-row">
        <div className="text-sm text-slate-500">
          Mostrando <span className="font-bold text-slate-900 dark:text-slate-200">{offset + 1}</span>-
          <span className="font-bold text-slate-900 dark:text-slate-200">{Math.min(offset + PAGE_SIZE, total)}</span> de{' '}
          <span className="font-bold text-slate-900 dark:text-slate-200">{total}</span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            disabled={offset <= 0 || loading}
            onClick={() => void load(offset - PAGE_SIZE)}
            className="h-9 px-4"
          >
            Anterior
          </Button>
          
          <div className="flex h-9 items-center gap-1 rounded-md bg-slate-100 px-3 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
            <span>Página</span>
            <span className="text-cyan-600">{paginaAtual}</span>
            <span>de</span>
            <span>{totalPaginas}</span>
          </div>

          <Button
            variant="secondary"
            disabled={offset + PAGE_SIZE >= total || loading}
            onClick={() => void load(offset + PAGE_SIZE)}
            className="h-9 px-4"
          >
            Próxima
          </Button>
        </div>
      </footer>
    </div>
  )
}