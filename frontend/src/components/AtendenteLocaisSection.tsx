import { useCallback, useEffect, useState } from 'react'
import {
  ponto,
  systemSettings,
  type Ponto,
  type SystemSettings,
} from '../api/client'
import { PontoLocalMapaPicker, type PontoLocalMapaValue } from './PontoLocalMapaPicker'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { Switch } from './ui/Switch'
import { useToast } from './ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'

type Props = {
  atendenteId: number
  usarLocalEmpresa: boolean
  localEmpresaRaio: string
  onUsarLocalEmpresaChange: (v: boolean) => void
  onLocalEmpresaRaioChange: (v: string) => void
}

export function AtendenteLocaisSection({
  atendenteId,
  usarLocalEmpresa,
  localEmpresaRaio,
  onUsarLocalEmpresaChange,
  onLocalEmpresaRaioChange,
}: Props) {
  const toast = useToast()
  const [empresa, setEmpresa] = useState<SystemSettings.EmpresaSistema | null>(null)
  const [locais, setLocais] = useState<Ponto.Local[]>([])
  const [nome, setNome] = useState('')
  const [mapa, setMapa] = useState<PontoLocalMapaValue>({
    latitude: null as number | null,
    longitude: null as number | null,
    endereco: '',
    raio_metros: 200,
  })
  const [editId, setEditId] = useState<number | null>(null)
  const [salvando, setSalvando] = useState(false)

  const carregar = useCallback(async () => {
    const [emp, locs] = await Promise.all([
      systemSettings.getEmpresaSistema(),
      ponto.locais({ atendente_id: atendenteId }),
    ])
    setEmpresa(emp)
    setLocais(locs)
  }, [atendenteId])

  useEffect(() => {
    void carregar().catch((err) => {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar os locais.'))
    })
  }, [carregar, toast])

  const empresaTemPin = empresa?.latitude != null && empresa?.longitude != null

  async function salvarExtra() {
    if (!nome.trim() || mapa.latitude == null || mapa.longitude == null) {
      toast.showWarning('Informe nome e pin (lat/lon) do local.')
      return
    }
    setSalvando(true)
    try {
      const payload = {
        nome: nome.trim(),
        endereco: mapa.endereco?.trim() || null,
        latitude: mapa.latitude,
        longitude: mapa.longitude,
        raio_metros: mapa.raio_metros || 200,
      }
      if (editId != null) {
        await ponto.atualizarLocal(editId, payload)
        toast.showSuccess('Local atualizado.')
      } else {
        await ponto.criarLocal({ ...payload, atendente_id: atendenteId })
        toast.showSuccess('Local adicionado.')
      }
      setEditId(null)
      setNome('')
      setMapa({ latitude: null, longitude: null, endereco: '', raio_metros: 200 })
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o local.'))
    } finally {
      setSalvando(false)
    }
  }

  async function toggleAtivo(loc: Ponto.Local) {
    try {
      await ponto.atualizarLocal(loc.id, { ativo: !loc.ativo })
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar o local.'))
    }
  }

  async function remover(id: number) {
    if (!confirm('Remover este local?')) return
    try {
      await ponto.removerLocal(id)
      await carregar()
      toast.showSuccess('Local removido.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível remover o local.'))
    }
  }

  function editar(loc: Ponto.Local) {
    setEditId(loc.id)
    setNome(loc.nome)
    setMapa({
      latitude: loc.latitude,
      longitude: loc.longitude,
      endereco: loc.endereco ?? '',
      raio_metros: loc.raio_metros,
    })
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <Switch
          bare
          checked={usarLocalEmpresa}
          onCheckedChange={onUsarLocalEmpresaChange}
          label="Local da empresa"
          description={
            empresaTemPin
              ? `Pin em ${empresa!.latitude!.toFixed(5)}, ${empresa!.longitude!.toFixed(5)} · raio padrão ${empresa!.ponto_raio_metros ?? 200} m (Configurações → Empresa).`
              : 'Configure o pin da empresa em Configurações → Empresa para usar este local.'
          }
          showStatusPill
          statusOnText="Ativo"
          statusOffText="Desligado"
        />
        {usarLocalEmpresa ? (
          <div className="mt-3 max-w-xs">
            <Input
              label="Raio neste usuário (m) — opcional"
              type="number"
              min={20}
              max={50000}
              value={localEmpresaRaio}
              onChange={(e) => onLocalEmpresaRaioChange(e.target.value)}
              placeholder={String(empresa?.ponto_raio_metros ?? 200)}
            />
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Vazio = usa o raio padrão da empresa. Salve o cadastro para gravar.
            </p>
          </div>
        ) : null}
      </div>

      <div className="space-y-3">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Outros locais</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Casa, filial ou remoto. A batida vale se estiver dentro do raio de qualquer local ativo.
        </p>
        <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Home office" />
        <PontoLocalMapaPicker value={mapa} onChange={setMapa} />
        <div className="flex flex-wrap gap-2">
          <Button type="button" disabled={salvando} onClick={() => void salvarExtra()}>
            {editId != null ? 'Salvar local' : 'Adicionar local'}
          </Button>
          {editId != null ? (
            <Button
              type="button"
              variant="cancel"
              onClick={() => {
                setEditId(null)
                setNome('')
                setMapa({ latitude: null, longitude: null, endereco: '', raio_metros: 200 })
              }}
            >
              Cancelar edição
            </Button>
          ) : null}
        </div>
        <ul className="space-y-2 text-sm">
          {locais.length === 0 ? (
            <li className="text-slate-500">Nenhum local extra cadastrado.</li>
          ) : (
            locais.map((loc) => (
              <li
                key={loc.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
              >
                <span>
                  <strong>{loc.nome}</strong>
                  {loc.endereco ? ` · ${loc.endereco}` : ''} · {loc.latitude.toFixed(5)},{' '}
                  {loc.longitude.toFixed(5)} · raio {loc.raio_metros} m
                  {!loc.ativo ? ' (desativado)' : ''}
                </span>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="secondary" onClick={() => editar(loc)}>
                    Editar
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => void toggleAtivo(loc)}>
                    {loc.ativo ? 'Desativar' : 'Ativar'}
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => void remover(loc.id)}>
                    Remover
                  </Button>
                </div>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
