import { useCallback, useEffect, useState } from 'react'
import { ApiError, pdvRotulos, pdvTiposAcessoRemoto, type PdvCatalogo } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

function CatalogoSection({
  titulo,
  items,
  loading,
  onReload,
  onCreate,
  onUpdate,
}: {
  titulo: string
  items: PdvCatalogo.Item[]
  loading: boolean
  onReload: () => void
  onCreate: (data: PdvCatalogo.Create) => Promise<void>
  onUpdate: (id: number, data: PdvCatalogo.Update) => Promise<void>
}) {
  const [nome, setNome] = useState('')
  const [ordem, setOrdem] = useState('0')
  const [saving, setSaving] = useState(false)

  async function adicionar() {
    if (!nome.trim()) return
    setSaving(true)
    try {
      await onCreate({ nome: nome.trim(), ordem_exibicao: Number(ordem) || 0, ativo: true })
      setNome('')
      setOrdem('0')
      onReload()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title={titulo}>
      <div className="mb-4 flex flex-wrap items-end gap-2">
        <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} className="min-w-[12rem] flex-1" />
        <Input label="Ordem" type="number" value={ordem} onChange={(e) => setOrdem(e.target.value)} className="w-24" />
        <Button type="button" loading={saving} onClick={() => void adicionar()}>
          Adicionar
        </Button>
      </div>
      {loading ? (
        <p className="text-sm text-slate-500">Carregando…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-500">Nenhum item cadastrado.</p>
      ) : (
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <div>
                <span className="font-medium text-slate-800 dark:text-slate-100">{item.nome}</span>
                <span className="ml-2 text-xs text-slate-500">ordem {item.ordem_exibicao}</span>
              </div>
              <Switch
                bare
                checked={item.ativo}
                onCheckedChange={(ativo) => void onUpdate(item.id, { ativo })}
                label="Ativo"
                showStatusPill
              />
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

export function ConfigPdvCatalogos() {
  const toast = useToast()
  const [forbidden, setForbidden] = useState(false)
  const [rotulos, setRotulos] = useState<PdvCatalogo.Item[]>([])
  const [tipos, setTipos] = useState<PdvCatalogo.Item[]>([])
  const [loadingR, setLoadingR] = useState(true)
  const [loadingT, setLoadingT] = useState(true)

  const loadRotulos = useCallback(() => {
    setLoadingR(true)
    pdvRotulos
      .list({ incluir_inativos: true, limit: 100 })
      .then((r) => setRotulos(r.items))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) setForbidden(true)
        else toast.showWarning(mensagemFalhaParaToast(err, 'Erro ao carregar rótulos.'))
      })
      .finally(() => setLoadingR(false))
  }, [toast])

  const loadTipos = useCallback(() => {
    setLoadingT(true)
    pdvTiposAcessoRemoto
      .list({ incluir_inativos: true, limit: 100 })
      .then((r) => setTipos(r.items))
      .catch((err) => toast.showWarning(mensagemFalhaParaToast(err, 'Erro ao carregar tipos.')))
      .finally(() => setLoadingT(false))
  }, [toast])

  useEffect(() => {
    loadRotulos()
    loadTipos()
  }, [loadRotulos, loadTipos])

  if (forbidden) {
    return (
      <SemPermissao
        title="Apenas administradores podem gerir os catálogos de PDV."
        voltarPara="/"
        voltarLabel="Voltar"
      />
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-10">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">Catálogos de PDV</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Padrões globais usados no cadastro de terminais por empresa (rótulos e tipos de acesso remoto).
        </p>
      </header>
      <CatalogoSection
        titulo="Rótulos de dispositivo"
        items={rotulos}
        loading={loadingR}
        onReload={loadRotulos}
        onCreate={(d) => pdvRotulos.create(d).then(() => toast.showSuccess('Rótulo criado.'))}
        onUpdate={(id, d) => pdvRotulos.update(id, d).then(() => loadRotulos())}
      />
      <CatalogoSection
        titulo="Tipos de acesso remoto"
        items={tipos}
        loading={loadingT}
        onReload={loadTipos}
        onCreate={(d) => pdvTiposAcessoRemoto.create(d).then(() => toast.showSuccess('Tipo criado.'))}
        onUpdate={(id, d) => pdvTiposAcessoRemoto.update(id, d).then(() => loadTipos())}
      />
    </div>
  )
}
