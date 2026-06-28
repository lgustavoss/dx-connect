import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { atendentes, whatsappChats, type WhatsappChats, type Atendentes } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import { rotuloAvaliacaoChat } from '../../lib/whatsappChatMeta'
import { CheckboxField } from '../../components/ui/CheckboxField'

const PAGE_SIZE = 15

export function WhatsappAvaliacoes() {
  const toast = useToast()
  const [items, setItems] = useState<WhatsappChats.Avaliacao[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busca, setBusca] = useState('')
  const [atendentesList, setAtendentesList] = useState<Atendentes.Atendente[]>([])
  const [atendenteId, setAtendenteId] = useState<number | ''>('')
  const [notaMin, setNotaMin] = useState<number | ''>('')
  const [desde, setDesde] = useState('')
  const [ate, setAte] = useState('')
  const [incluirSemResposta, setIncluirSemResposta] = useState(false)

  const load = useCallback(
    async (from: number) => {
      setLoading(true)
      try {
        const params: Record<string, string | number | undefined> = {
          offset: from,
          limit: PAGE_SIZE,
        }
        if (busca.trim()) params.busca = busca.trim()
        if (atendenteId !== '') params.atendente_id = atendenteId
        if (notaMin !== '') {
          params.nota_min = notaMin
          params.nota_max = notaMin
        }
        if (desde) params.encerramento_inicio = `${desde}T00:00:00`
        if (ate) params.encerramento_fim = `${ate}T23:59:59`
        if (incluirSemResposta) params.incluir_sem_resposta = 'true'
        const { items: rows, total: t } = await whatsappChats.avaliacoes(params)
        setItems(rows)
        setTotal(t)
        setOffset(from)
      } catch (err) {
        toast.showError(mensagemFalhaParaToast(err, 'Falha ao carregar avaliações.'))
      } finally {
        setLoading(false)
      }
    },
    [atendenteId, ate, busca, desde, incluirSemResposta, notaMin, toast],
  )

  useEffect(() => {
    void load(0)
  }, [load])

  useEffect(() => {
    void atendentes
      .list({ incluir_inativos: true, offset: 0, limit: 100 })
      .then((result) => setAtendentesList(result.items))
      .catch(() => setAtendentesList([]))
  }, [])

  const mediaNotas =
    items.filter((i) => i.nota != null).length > 0
      ? (
          items.filter((i) => i.nota != null).reduce((s, i) => s + (i.nota ?? 0), 0) /
          items.filter((i) => i.nota != null).length
        ).toFixed(1)
      : null

  const paginaAtual = Math.floor(offset / PAGE_SIZE) + 1
  const totalPaginas = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-6">
      <Card className="border-none p-4 shadow-sm ring-1 ring-slate-200 dark:ring-slate-800">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Input label="Busca" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Protocolo, telefone…" />
          <Select
            label="Atendente"
            value={atendenteId}
            onChange={(value) => setAtendenteId(value === '' ? '' : Number(value))}
            options={atendentesList.map((a) => ({ value: a.id, label: a.nome }))}
            placeholder="Todos"
            includeEmpty
            emptyLabel="Todos"
          />
          <Select
            label="Nota"
            value={notaMin}
            onChange={(value) => setNotaMin(value === '' ? '' : Number(value))}
            options={[5, 4, 3, 2, 1].map((n) => ({ value: n, label: String(n) }))}
            placeholder="Todas"
            includeEmpty
            emptyLabel="Todas"
          />
          <div className="grid grid-cols-2 gap-2">
            <Input label="De" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
            <Input label="Até" type="date" value={ate} onChange={(e) => setAte(e.target.value)} />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <CheckboxField checked={incluirSemResposta} onChange={setIncluirSemResposta}>
            Incluir solicitações sem resposta (auditoria)
          </CheckboxField>
          <Button type="button" onClick={() => void load(0)}>
            Filtrar
          </Button>
        </div>
      </Card>

      {mediaNotas && (
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Média nesta página: <span className="font-semibold text-slate-900 dark:text-slate-100">{mediaNotas}</span>
        </p>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <Card className="py-12 text-center text-sm text-slate-500">Nenhuma avaliação encontrada.</Card>
      ) : (
        <div className="grid gap-3">
          {items.map((a) => (
            <Card key={a.chat_id} className="border-none p-4 shadow-sm ring-1 ring-slate-200 dark:ring-slate-800">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="font-semibold text-slate-900 dark:text-slate-100">{a.cliente_nome || 'Cliente'}</p>
                  <p className="font-mono text-xs text-cyan-600 dark:text-cyan-400">{exibirProtocolo(a.protocolo)}</p>
                  <p className="text-xs text-slate-500">{a.atendente_nome || '—'} · {a.setor_nome || 'Sem setor'}</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-slate-900 dark:text-slate-100">{rotuloAvaliacaoChat(a)}</p>
                  <p className="text-xs text-slate-500">
                    {a.encerramento_at
                      ? new Date(a.encerramento_at).toLocaleString('pt-BR')
                      : '—'}
                  </p>
                  <Link
                    to={`/whatsapp/c/${a.chat_id}`}
                    className="mt-1 inline-block text-xs font-medium text-cyan-600 hover:underline dark:text-cyan-400"
                  >
                    Ver conversa
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {totalPaginas > 1 && (
        <footer className="flex items-center justify-between border-t pt-4 dark:border-slate-800">
          <Button type="button" variant="secondary" disabled={offset === 0} onClick={() => void load(offset - PAGE_SIZE)}>
            Anterior
          </Button>
          <span className="text-sm text-slate-500">
            Página {paginaAtual} de {totalPaginas}
          </span>
          <Button
            type="button"
            variant="secondary"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => void load(offset + PAGE_SIZE)}
          >
            Próxima
          </Button>
        </footer>
      )}
    </div>
  )
}
