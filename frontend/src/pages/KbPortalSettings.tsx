import { useCallback, useEffect, useMemo, useState } from 'react'
import { kb, type Kb } from '../api/client'
import { ApiError } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { useToast } from '../components/ui/Toast'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'

type FormState = {
  portal_titulo: string
  texto_boas_vindas: string
  cor_header: string
  cor_primaria: string
  cor_texto_header: string
  cor_texto_corpo: string
  cor_fundo: string
  cor_link: string
}

function fromApi(data: Kb.PortalSettings): FormState {
  return {
    portal_titulo: data.portal_titulo ?? '',
    texto_boas_vindas: data.texto_boas_vindas ?? '',
    cor_header: data.cor_header,
    cor_primaria: data.cor_primaria,
    cor_texto_header: data.cor_texto_header,
    cor_texto_corpo: data.cor_texto_corpo,
    cor_fundo: data.cor_fundo,
    cor_link: data.cor_link ?? data.cor_primaria,
  }
}

function ColorField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">{label}</label>
      <div className="flex items-center gap-3">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="size-10 cursor-pointer rounded-lg border border-slate-300 bg-white p-0.5 dark:border-slate-600"
        />
        <Input value={value} onChange={(e) => onChange(e.target.value)} className="font-mono text-sm" />
      </div>
    </div>
  )
}

export function KbPortalSettingsPage({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [form, setForm] = useState<FormState | null>(null)

  const publicUrl = useMemo(
    () => (typeof window !== 'undefined' ? `${window.location.origin}/kb` : '/kb'),
    [],
  )

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    kb.getPortalSettings()
      .then((data) => setForm(fromApi(data)))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as configurações.'))
      })
      .finally(() => setLoading(false))
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    if (!form) return
    setSaving(true)
    try {
      const data = await kb.updatePortalSettings({
        portal_titulo: form.portal_titulo.trim() || null,
        texto_boas_vindas: form.texto_boas_vindas.trim() || null,
        cor_header: form.cor_header,
        cor_primaria: form.cor_primaria,
        cor_texto_header: form.cor_texto_header,
        cor_texto_corpo: form.cor_texto_corpo,
        cor_fundo: form.cor_fundo,
        cor_link: form.cor_link.trim() || null,
      })
      setForm(fromApi(data))
      toast.showSuccess('Configurações do portal salvas.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={
        <SemPermissao
          title="Você não tem permissão para personalizar o portal público."
          voltarPara="/configuracoes/sistema/empresa"
          voltarLabel="Voltar para Sistema"
        />
      }
      title="Base de conhecimento"
      subtitle="Personalize o portal público /kb — cores, textos e aparência (estilo TomTicket)."
      actions={
        <a href="/kb" target="_blank" rel="noreferrer">
          <Button type="button" variant="secondary">
            Abrir preview
          </Button>
        </a>
      }
    >
      {loading || !form ? (
        <p className="text-slate-500">Carregando…</p>
      ) : (
        <form onSubmit={(e) => void salvar(e)} className="space-y-6">
          <Card className="space-y-4 p-4 sm:p-5">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              URL pública:{' '}
              <a href="/kb" target="_blank" rel="noreferrer" className="font-medium text-teal-700 hover:underline dark:text-teal-400">
                {publicUrl}
              </a>
              . A logo vem de Configurações → Sistema → Empresa.
            </p>

            <Input
              label="Título do portal"
              value={form.portal_titulo}
              onChange={(e) => setForm({ ...form, portal_titulo: e.target.value })}
              placeholder="Central de ajuda — Minha Empresa"
            />

            <div>
              <label htmlFor="kb-portal-boas-vindas" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Texto de boas-vindas
              </label>
              <textarea
                id="kb-portal-boas-vindas"
                rows={3}
                value={form.texto_boas_vindas}
                onChange={(e) => setForm({ ...form, texto_boas_vindas: e.target.value })}
                placeholder="Consulte passo a passo para tirar dúvidas sobre o sistema."
                className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm dark:border-slate-600 dark:bg-slate-900"
              />
            </div>
          </Card>

          <Card className="grid gap-4 p-4 sm:grid-cols-2 sm:p-5">
            <ColorField label="Cor da barra superior (navbar)" value={form.cor_header} onChange={(v) => setForm({ ...form, cor_header: v })} />
            <ColorField label="Cor do texto da navbar" value={form.cor_texto_header} onChange={(v) => setForm({ ...form, cor_texto_header: v })} />
            <ColorField label="Cor de destaque (botões / seleção)" value={form.cor_primaria} onChange={(v) => setForm({ ...form, cor_primaria: v })} />
            <ColorField label="Cor dos links" value={form.cor_link} onChange={(v) => setForm({ ...form, cor_link: v })} />
            <ColorField label="Cor do texto principal" value={form.cor_texto_corpo} onChange={(v) => setForm({ ...form, cor_texto_corpo: v })} />
            <ColorField label="Cor de fundo da página" value={form.cor_fundo} onChange={(v) => setForm({ ...form, cor_fundo: v })} />
          </Card>

          <div className="flex flex-wrap gap-3">
            <Button type="submit" loading={saving}>
              Salvar personalização
            </Button>
            <a href="/kb" target="_blank" rel="noreferrer">
              <Button type="button" variant="secondary">
                Ver portal público
              </Button>
            </a>
          </div>
        </form>
      )}
    </ConfigListPageShell>
  )
}
