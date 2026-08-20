import { useCallback, useEffect, useState } from 'react'
import { ApiError, atendentes, ponto, type Atendentes, type Ponto } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { SemPermissao } from './SemPermissao'

function formatarHora(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function inicioMesIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

function hojeIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function rotuloStatus(s: Ponto.HojeItem['status']): string {
  switch (s) {
    case 'falta':
      return 'Falta'
    case 'parcial':
      return 'Parcial'
    case 'folga':
      return 'Folga'
    case 'folga_com_ponto':
      return 'Folga c/ ponto'
    case 'atraso':
      return 'Atraso'
    case 'feriado':
      return 'Feriado'
    case 'ok':
      return 'Ok'
    default:
      return 'Livre'
  }
}

function formatarDuracao(segundos: number | null | undefined): string {
  if (segundos == null || segundos < 0) return '—'
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  if (h <= 0) return `${m} min`
  return `${h} h ${String(m).padStart(2, '0')} min`
}

function toDatetimeLocalValue(d = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function PontoEquipe() {
  const toast = useToast()
  const { user } = useAuth()
  const [items, setItems] = useState<Ponto.BatidaAdmin[]>([])
  const [total, setTotal] = useState(0)
  const [hoje, setHoje] = useState<Ponto.HojeLista | null>(null)
  const [equipe, setEquipe] = useState<Atendentes.Atendente[]>([])
  const [atendenteId, setAtendenteId] = useState('')
  const [desde, setDesde] = useState(inicioMesIso)
  const [ate, setAte] = useState(hojeIso)
  const [loading, setLoading] = useState(true)
  const [semPermissao, setSemPermissao] = useState(false)
  const [ajusteAtendente, setAjusteAtendente] = useState('')
  const [ajusteTipo, setAjusteTipo] = useState<Ponto.Tipo>('entrada')
  const [ajusteQuando, setAjusteQuando] = useState(toDatetimeLocalValue())
  const [ajusteMotivo, setAjusteMotivo] = useState('')
  const [salvandoAjuste, setSalvandoAjuste] = useState(false)
  const [justifs, setJustifs] = useState<Ponto.Justificativa[]>([])
  const [digest, setDigest] = useState<Ponto.Digest | null>(null)
  const [banco, setBanco] = useState<Ponto.BancoHoras | null>(null)
  const [settings, setSettings] = useState<Ponto.Settings | null>(null)
  const [feriados, setFeriados] = useState<Ponto.Feriado[]>([])
  const [feriadoData, setFeriadoData] = useState('')
  const [feriadoNome, setFeriadoNome] = useState('')
  const [salvandoSettings, setSalvandoSettings] = useState(false)

  const carregar = useCallback(
    async (silencioso = false) => {
      try {
        const [hist, dia, js, dig, st, fer] = await Promise.all([
          ponto.batidasAdmin({
            atendente_id: atendenteId ? Number(atendenteId) : undefined,
            desde,
            ate,
            limit: 100,
          }),
          ponto.hoje(),
          ponto.justificativasAdmin('pendente'),
          ponto.digest(),
          ponto.settings(),
          ponto.feriados(new Date().getFullYear()),
        ])
        setItems(hist.items)
        setTotal(hist.total)
        setHoje(dia)
        setJustifs(js)
        setDigest(dig)
        setSettings(st)
        setFeriados(fer)
        setSemPermissao(false)
        if (atendenteId) {
          const bh = await ponto.bancoHorasAdmin(Number(atendenteId), desde, ate)
          setBanco(bh)
        } else {
          setBanco(null)
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setSemPermissao(true)
          return
        }
        if (!silencioso) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o ponto da equipe.'))
        }
      } finally {
        setLoading(false)
      }
    },
    [ate, atendenteId, desde, toast],
  )

  useEffect(() => {
    void coletarTodasPaginas<Atendentes.Atendente>((o, l) =>
      atendentes.list({ incluir_inativos: false, offset: o, limit: l }),
    ).then(setEquipe)
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  async function exportarCsv() {
    try {
      const blob = await ponto.exportCsv({
        atendente_id: atendenteId ? Number(atendenteId) : undefined,
        desde,
        ate,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'ponto_batidas.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível exportar o CSV.'))
    }
  }

  async function salvarAjuste() {
    if (!ajusteAtendente || !ajusteMotivo.trim()) {
      toast.showWarning('Informe atendente e motivo do ajuste.')
      return
    }
    setSalvandoAjuste(true)
    try {
      const iso = new Date(ajusteQuando).toISOString()
      await ponto.criarAjuste({
        atendente_id: Number(ajusteAtendente),
        tipo: ajusteTipo,
        registrado_em: iso,
        motivo: ajusteMotivo.trim(),
      })
      toast.showSuccess('Ajuste registrado.')
      setAjusteMotivo('')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o ajuste.'))
    } finally {
      setSalvandoAjuste(false)
    }
  }

  async function anularBatida(id: number) {
    const motivo = window.prompt('Motivo da anulação (obrigatório):')
    if (!motivo || motivo.trim().length < 3) return
    try {
      await ponto.anular(id, motivo.trim())
      toast.showSuccess('Batida anulada.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível anular.'))
    }
  }

  async function decidirJust(id: number, estado: 'aprovada' | 'rejeitada') {
    const motivo = window.prompt(estado === 'aprovada' ? 'Motivo da aprovação:' : 'Motivo da rejeição:')
    if (!motivo || motivo.trim().length < 3) return
    try {
      await ponto.decidirJustificativa(id, { estado, decisao_motivo: motivo.trim() })
      toast.showSuccess(estado === 'aprovada' ? 'Justificativa aprovada.' : 'Justificativa rejeitada.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível decidir.'))
    }
  }

  async function salvarSettings() {
    if (!settings) return
    setSalvandoSettings(true)
    try {
      const st = await ponto.updateSettings({
        usar_feriados_nacionais: settings.usar_feriados_nacionais,
        fecho_automatico_ativo: settings.fecho_automatico_ativo,
        fecho_apos_horas: settings.fecho_apos_horas,
      })
      setSettings(st)
      toast.showSuccess('Configurações de ponto salvas.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar as configurações.'))
    } finally {
      setSalvandoSettings(false)
    }
  }

  async function adicionarFeriado() {
    if (!feriadoData || !feriadoNome.trim()) {
      toast.showWarning('Informe data e nome do feriado.')
      return
    }
    try {
      await ponto.criarFeriado({ data: feriadoData, nome: feriadoNome.trim() })
      toast.showSuccess('Feriado cadastrado.')
      setFeriadoNome('')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível criar o feriado.'))
    }
  }

  async function apagarFeriado(id: number) {
    try {
      await ponto.removerFeriado(id)
      toast.showSuccess('Feriado removido.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível remover o feriado.'))
    }
  }

  if (user?.role !== 'admin' || semPermissao) {
    return (
      <SemPermissao
        title="Acesso restrito a administradores."
        voltarPara="/ponto"
        voltarLabel="Ir para Meu ponto"
      />
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Ponto da equipe"
        subtitle="Batidas, visão do dia, ajustes auditados e exportação CSV."
      />

      <div className="space-y-4">
        <Card title="Digest do dia">
          {digest ? (
            <div className="flex flex-wrap gap-4 text-sm">
              <span>
                Faltas: <strong>{digest.faltas}</strong>
              </span>
              <span>
                Atrasos: <strong>{digest.atrasos}</strong>
              </span>
              <span>
                Jornadas abertas: <strong>{digest.jornadas_abertas}</strong>
              </span>
              <span>
                Online sem ponto: <strong>{digest.online_sem_ponto}</strong>
              </span>
              <span>
                Justificativas pendentes: <strong>{digest.justificativas_pendentes}</strong>
              </span>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Carregando…</p>
          )}
        </Card>

        <Card title="Hoje">
          {loading && !hoje ? (
            <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                  <tr>
                    <th className="py-2 pr-3 font-medium">Nome</th>
                    <th className="py-2 pr-3 font-medium">Online</th>
                    <th className="py-2 pr-3 font-medium">Esperado</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 font-medium">Entrada</th>
                  </tr>
                </thead>
                <tbody>
                  {(hoje?.itens ?? []).map((item) => (
                    <tr key={item.atendente_id} className="border-b border-slate-100 dark:border-slate-800/80">
                      <td className="py-2 pr-3">
                        {item.nome}
                        {item.em_pausa ? (
                          <span className="ml-2 text-xs text-amber-700 dark:text-amber-300">pausa</span>
                        ) : null}
                        {item.atrasado ? (
                          <span className="ml-2 text-xs text-amber-700 dark:text-amber-300">atraso</span>
                        ) : null}
                        {item.feriado ? (
                          <span className="ml-2 text-xs text-slate-500">feriado</span>
                        ) : null}
                      </td>
                      <td className="py-2 pr-3">
                        {item.online_sem_ponto ? (
                          <span className="text-amber-700 dark:text-amber-300">Online sem ponto</span>
                        ) : item.online ? (
                          'Online'
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="py-2 pr-3">{item.esperado ? 'Trabalho' : '—'}</td>
                      <td className="py-2 pr-3">{rotuloStatus(item.status)}</td>
                      <td className="py-2">{formatarHora(item.entrada_em)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Justificativas pendentes">
          {justifs.length === 0 ? (
            <p className="text-sm text-slate-500">Nenhuma pendente.</p>
          ) : (
            <ul className="space-y-3">
              {justifs.map((j) => (
                <li
                  key={j.id}
                  className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                >
                  <div className="text-sm">
                    <p className="font-medium">
                      {j.atendente_nome ?? j.atendente_id} · {j.data_ref} · {j.tipo}
                    </p>
                    <p className="text-slate-600 dark:text-slate-300">{j.motivo}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button type="button" variant="secondary" onClick={() => void decidirJust(j.id, 'aprovada')}>
                      Aprovar
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => void decidirJust(j.id, 'rejeitada')}>
                      Rejeitar
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Ajuste manual">
          <div className="flex flex-wrap items-end gap-3">
            <Select
              label="Atendente"
              value={ajusteAtendente}
              onChange={(v) => setAjusteAtendente(String(v))}
              options={[
                { value: '', label: 'Selecione' },
                ...equipe.map((a) => ({ value: String(a.id), label: a.nome })),
              ]}
            />
            <Select
              label="Tipo"
              value={ajusteTipo}
              onChange={(v) => setAjusteTipo(String(v) as Ponto.Tipo)}
              options={[
                { value: 'entrada', label: 'Entrada' },
                { value: 'saida', label: 'Saída' },
                { value: 'pausa_inicio', label: 'Início de pausa' },
                { value: 'pausa_fim', label: 'Fim de pausa' },
              ]}
            />
            <Input
              label="Data/hora"
              type="datetime-local"
              value={ajusteQuando}
              onChange={(e) => setAjusteQuando(e.target.value)}
            />
            <Input
              label="Motivo"
              value={ajusteMotivo}
              onChange={(e) => setAjusteMotivo(e.target.value)}
              placeholder="Obrigatório"
            />
            <Button type="button" disabled={salvandoAjuste} onClick={() => void salvarAjuste()}>
              Registrar ajuste
            </Button>
          </div>
        </Card>

        <Card title="Histórico">
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Select
              label="Atendente"
              value={atendenteId}
              onChange={(v) => setAtendenteId(String(v))}
              options={[
                { value: '', label: 'Todos' },
                ...equipe.map((a) => ({ value: String(a.id), label: a.nome })),
              ]}
            />
            <Input label="De" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
            <Input label="Até" type="date" value={ate} onChange={(e) => setAte(e.target.value)} />
            <Button type="button" variant="secondary" onClick={() => void carregar()}>
              Filtrar
            </Button>
            <Button type="button" variant="secondary" onClick={() => void exportarCsv()}>
              Exportar CSV
            </Button>
          </div>
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
            {total} batida{total === 1 ? '' : 's'} no filtro
            {banco ? (
              <>
                {' '}
                · Banco de {banco.atendente_nome ?? 'selecionado'}:{' '}
                <strong>
                  {banco.saldo_segundos >= 0 ? '+' : '−'}
                  {formatarDuracao(Math.abs(banco.saldo_segundos))}
                </strong>
              </>
            ) : null}
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                <tr>
                  <th className="py-2 pr-3 font-medium">Atendente</th>
                  <th className="py-2 pr-3 font-medium">Tipo</th>
                  <th className="py-2 pr-3 font-medium">Horário</th>
                  <th className="py-2 pr-3 font-medium">Origem</th>
                  <th className="py-2 font-medium">Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-slate-500">
                      Nenhuma batida neste filtro.
                    </td>
                  </tr>
                ) : (
                  items.map((b) => (
                    <tr key={b.id} className="border-b border-slate-100 dark:border-slate-800/80">
                      <td className="py-2 pr-3">{b.atendente_nome}</td>
                      <td className="py-2 pr-3">{b.tipo.replace('_', ' ')}</td>
                      <td className="py-2 pr-3">{formatarHora(b.registrado_em)}</td>
                      <td className="py-2 pr-3">{b.origem ?? '—'}</td>
                      <td className="py-2">
                        <Button type="button" variant="ghost" onClick={() => void anularBatida(b.id)}>
                          Anular
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Configurações do ponto">
          {settings ? (
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={settings.usar_feriados_nacionais}
                  onChange={(e) =>
                    setSettings({ ...settings, usar_feriados_nacionais: e.target.checked })
                  }
                />
                Usar feriados nacionais (BR) na conformidade
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={settings.fecho_automatico_ativo}
                  onChange={(e) =>
                    setSettings({ ...settings, fecho_automatico_ativo: e.target.checked })
                  }
                />
                Fechar jornada automaticamente após N horas (desligado por padrão)
              </label>
              <Input
                label="Horas para fecho automático"
                type="number"
                min={4}
                max={48}
                value={String(settings.fecho_apos_horas)}
                onChange={(e) =>
                  setSettings({ ...settings, fecho_apos_horas: Number(e.target.value) || 14 })
                }
              />
              <Button type="button" disabled={salvandoSettings} onClick={() => void salvarSettings()}>
                Salvar configurações
              </Button>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Carregando…</p>
          )}
        </Card>

        <Card title="Feriados da instância">
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Input
              label="Data"
              type="date"
              value={feriadoData}
              onChange={(e) => setFeriadoData(e.target.value)}
            />
            <Input
              label="Nome"
              value={feriadoNome}
              onChange={(e) => setFeriadoNome(e.target.value)}
              placeholder="Ex.: Aniversário da rede"
            />
            <Button type="button" onClick={() => void adicionarFeriado()}>
              Adicionar
            </Button>
          </div>
          <ul className="space-y-2 text-sm">
            {feriados.length === 0 ? (
              <li className="text-slate-500">Nenhum feriado custom cadastrado este ano.</li>
            ) : (
              feriados.map((f) => (
                <li
                  key={f.id}
                  className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                >
                  <span>
                    {f.data} · {f.nome}
                  </span>
                  <Button type="button" variant="ghost" onClick={() => void apagarFeriado(f.id)}>
                    Remover
                  </Button>
                </li>
              ))
            )}
          </ul>
        </Card>
      </div>
    </PageContainer>
  )
}
