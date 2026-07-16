import { useCallback, useEffect, useState } from 'react'
import { ApiError, presenca, type Presenca } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { SemPermissao } from './SemPermissao'

const POLL_MS = 20_000

function formatarAbsoluto(iso: string): string {
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return iso
  }
}

function formatarRelativo(iso: string, agora: number): string {
  const ms = agora - new Date(iso).getTime()
  if (Number.isNaN(ms) || ms < 0) return 'agora'
  const sec = Math.floor(ms / 1000)
  if (sec < 60) return 'há poucos segundos'
  const min = Math.floor(sec / 60)
  if (min < 60) return min === 1 ? 'há 1 min' : `há ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return h === 1 ? 'há 1 h' : `há ${h} h`
  const d = Math.floor(h / 24)
  return d === 1 ? 'há 1 dia' : `há ${d} dias`
}

function rotuloRole(role: string): string {
  if (role === 'admin') return 'Admin'
  return 'Atendente'
}

export function PresencaOnline() {
  const toast = useToast()
  const { user } = useAuth()
  const [itens, setItens] = useState<Presenca.ItemOnline[]>([])
  const [loading, setLoading] = useState(true)
  const [semPermissao, setSemPermissao] = useState(false)
  const [atualizadoEm, setAtualizadoEm] = useState<Date | null>(null)
  const [agora, setAgora] = useState(() => Date.now())
  const [alvoForcar, setAlvoForcar] = useState<Presenca.ItemOnline | null>(null)
  const [forcando, setForcando] = useState(false)

  const carregar = useCallback(
    async (silencioso = false) => {
      try {
        const data = await presenca.online()
        setItens(data.itens)
        setAtualizadoEm(new Date())
        setSemPermissao(false)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setSemPermissao(true)
          return
        }
        if (!silencioso) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar a presença.'))
        }
      } finally {
        setLoading(false)
      }
    },
    [toast],
  )

  useEffect(() => {
    void carregar()
  }, [carregar])

  useEffect(() => {
    const id = window.setInterval(() => {
      void carregar(true)
    }, POLL_MS)
    return () => window.clearInterval(id)
  }, [carregar])

  useEffect(() => {
    const id = window.setInterval(() => setAgora(Date.now()), 30_000)
    return () => window.clearInterval(id)
  }, [])

  if (semPermissao) {
    return (
      <PageContainer>
        <SemPermissao
          title="Somente administradores veem quem está online."
          detail="Peça a um admin para consultar a equipe conectada ao painel."
        />
      </PageContainer>
    )
  }

  return (
    <PageContainer maxWidth="5xl">
      <PageHeader
        title="Equipe online"
        subtitle="Atendentes com o painel aberto agora — útil para saber quem pode atender chats e tickets."
        actions={
          <Button type="button" variant="secondary" onClick={() => void carregar()} disabled={loading}>
            Atualizar
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
        <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 font-medium text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
          <span className="size-2 rounded-full bg-emerald-500" aria-hidden />
          {itens.length === 1 ? '1 online' : `${itens.length} online`}
        </span>
        {atualizadoEm ? (
          <span>Atualizado às {atualizadoEm.toLocaleTimeString('pt-BR')}</span>
        ) : null}
      </div>

      {loading && itens.length === 0 ? (
        <Card className="space-y-3 p-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800/80" />
          ))}
        </Card>
      ) : itens.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-base font-medium text-slate-800 dark:text-slate-100">
            Nenhum atendente online no momento
          </p>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Quem abrir o painel aparece aqui automaticamente (conexão em tempo real).
          </p>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="-mx-2 overflow-x-auto sm:-mx-0">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <tr>
                  <th className="px-2 py-2 font-medium sm:px-3">Atendente</th>
                  <th className="px-2 py-2 font-medium sm:px-3">Setores</th>
                  <th className="px-2 py-2 font-medium sm:px-3">Perfil</th>
                  <th className="px-2 py-2 font-medium sm:px-3">Online desde</th>
                  <th className="px-2 py-2 font-medium sm:px-3">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {itens.map((item) => {
                  const souEu = item.atendente_id === user?.id
                  return (
                    <tr key={item.atendente_id}>
                      <td className="px-2 py-3 sm:px-3">
                        <div className="flex items-center gap-3">
                          <span
                            className="size-2.5 shrink-0 rounded-full bg-emerald-500"
                            title="Online"
                            aria-label="Online"
                          />
                          <div className="min-w-0">
                            <p className="font-medium text-slate-900 dark:text-slate-100">
                              {item.nome}
                              {souEu ? (
                                <span className="ml-1.5 text-xs font-normal text-slate-500">(você)</span>
                              ) : null}
                            </p>
                            <p className="truncate text-xs text-slate-500 dark:text-slate-400">{item.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-2 py-3 text-slate-700 dark:text-slate-300 sm:px-3">
                        {item.setores.length === 0
                          ? '—'
                          : item.setores.map((s) => s.nome).join(', ')}
                      </td>
                      <td className="px-2 py-3 text-slate-700 dark:text-slate-300 sm:px-3">
                        {rotuloRole(item.role)}
                      </td>
                      <td className="px-2 py-3 sm:px-3">
                        <span
                          className="font-medium text-slate-800 dark:text-slate-100"
                          title={formatarAbsoluto(item.online_desde)}
                        >
                          {formatarRelativo(item.online_desde, agora)}
                        </span>
                        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                          {formatarAbsoluto(item.online_desde)}
                        </p>
                      </td>
                      <td className="px-2 py-3 sm:px-3">
                        {!souEu ? (
                          <Button
                            type="button"
                            variant="secondary"
                            className="!px-2.5 !py-1 text-xs text-rose-700 hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-950/40"
                            onClick={() => setAlvoForcar(item)}
                          >
                            Forçar saída
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <ConfirmDialog
        open={alvoForcar != null}
        title="Forçar saída?"
        message={
          alvoForcar
            ? `${alvoForcar.nome} será desconectado do painel e precisará fazer login novamente.`
            : ''
        }
        confirmLabel="Forçar saída"
        cancelLabel="Cancelar"
        variant="danger"
        loading={forcando}
        onCancel={() => {
          if (!forcando) setAlvoForcar(null)
        }}
        onConfirm={() => {
          if (!alvoForcar) return
          setForcando(true)
          void presenca
            .forcarSaida(alvoForcar.atendente_id)
            .then(() => {
              toast.showSuccess(`${alvoForcar.nome} foi desconectado.`)
              setAlvoForcar(null)
              void carregar(true)
            })
            .catch((err) => {
              toast.showError(mensagemFalhaParaToast(err, 'Não foi possível forçar a saída.'))
            })
            .finally(() => setForcando(false))
        }}
      />
    </PageContainer>
  )
}
