import { useCallback, useEffect, useMemo, useState } from 'react'
import { kb, setores, type Kb, type Setores } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { ApiError } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input, TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { CheckboxField } from '../components/ui/CheckboxField'
import { useToast } from '../components/ui/Toast'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'

type FormState = {
  portal_titulo: string
  texto_boas_vindas: string
  cor_header: string
  cor_sidebar: string
  cor_primaria: string
  cor_texto_header: string
  cor_texto_corpo: string
  cor_fundo: string
  cor_link: string
  feedback_habilitado: boolean
  chat_habilitado: boolean
  chat_setor_id: string
  chat_texto_boas_vindas: string
}

function fromApi(data: Kb.PortalSettings): FormState {
  return {
    portal_titulo: data.portal_titulo ?? '',
    texto_boas_vindas: data.texto_boas_vindas ?? '',
    cor_header: data.cor_header,
    cor_sidebar: data.cor_sidebar || data.cor_header,
    cor_primaria: data.cor_primaria,
    cor_texto_header: data.cor_texto_header,
    cor_texto_corpo: data.cor_texto_corpo,
    cor_fundo: data.cor_fundo,
    cor_link: data.cor_link ?? data.cor_primaria,
    feedback_habilitado: data.feedback_habilitado,
    chat_habilitado: data.chat_habilitado,
    chat_setor_id: data.chat_setor_id != null ? String(data.chat_setor_id) : '',
    chat_texto_boas_vindas: data.chat_texto_boas_vindas ?? '',
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
  const [setoresOpts, setSetoresOpts] = useState<Setores.Setor[]>([])

  const publicUrl = useMemo(
    () => (typeof window !== 'undefined' ? `${window.location.origin}/kb` : '/kb'),
    [],
  )
  const portalUrl = useMemo(
    () => (typeof window !== 'undefined' ? `${window.location.origin}/portal/login` : '/portal/login'),
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
    void coletarTodasPaginas<Setores.Setor>((o, l) => setores.list({ incluir_inativos: false, offset: o, limit: l })).then(
      setSetoresOpts,
    )
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
        cor_sidebar: form.cor_sidebar,
        cor_primaria: form.cor_primaria,
        cor_texto_header: form.cor_texto_header,
        cor_texto_corpo: form.cor_texto_corpo,
        cor_fundo: form.cor_fundo,
        cor_link: form.cor_link.trim() || null,
        feedback_habilitado: form.feedback_habilitado,
        chat_habilitado: form.chat_habilitado,
        chat_setor_id: form.chat_setor_id ? Number(form.chat_setor_id) : null,
        chat_texto_boas_vindas: form.chat_texto_boas_vindas.trim() || null,
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
          voltarPara="/configuracoes/empresa/empresa"
          voltarLabel="Voltar para Sistema"
        />
      }
      title="Base de conhecimento"
      subtitle="Personalize a aparência white-label da instância — cores valem para /kb e /portal; o título abaixo é só da central de ajuda (/kb)."
      actions={
        <>
          <a href="/kb" target="_blank" rel="noreferrer">
            <Button type="button" variant="secondary">
              Abrir /kb
            </Button>
          </a>
          <a href="/portal/login" target="_blank" rel="noreferrer" className="ml-2 inline-block">
            <Button type="button" variant="secondary">
              Abrir /portal
            </Button>
          </a>
        </>
      }
    >
      {loading || !form ? (
        <p className="text-slate-500">Carregando…</p>
      ) : (
        <form onSubmit={(e) => void salvar(e)} className="space-y-6">
          <Card className="space-y-4 p-4 sm:p-5">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Portal público:{' '}
              <a href="/kb" target="_blank" rel="noreferrer" className="font-medium text-teal-700 hover:underline dark:text-teal-400">
                {publicUrl}
              </a>
              . Portal autenticado:{' '}
              <a href="/portal/login" target="_blank" rel="noreferrer" className="font-medium text-teal-700 hover:underline dark:text-teal-400">
                {portalUrl}
              </a>
              . A logo vem de Configurações → Sistema → Empresa.
            </p>

            <Input
              label="Título da central de ajuda (/kb)"
              value={form.portal_titulo}
              onChange={(e) => setForm({ ...form, portal_titulo: e.target.value })}
              placeholder="Suporte — Minha Empresa"
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
                className={TEXTAREA_FIELD_CLASS}
                placeholder="Consulte passo a passo para tirar dúvidas sobre o sistema."
              />
            </div>
          </Card>

          <Card className="p-4 sm:p-5">
            <CheckboxField
              checked={form.feedback_habilitado}
              onChange={(e) => setForm({ ...form, feedback_habilitado: e.target.checked })}
            >
              Permitir avaliação «útil / não útil» nos manuais do portal
            </CheckboxField>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Quando desligado, os visitantes não veem os botões de feedback no fim de cada artigo.
            </p>
          </Card>

          <Card className="space-y-4 p-4 sm:p-5">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Chat ao vivo no portal</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              O visual do chat (barra superior, fundo, botões e balões) usa as cores da seção «Personalização de cores»
              abaixo. A logo e o nome exibidos vêm de Configurações → Sistema → Empresa e do título do portal.
            </p>
            <CheckboxField
              checked={form.chat_habilitado}
              onChange={(e) => setForm({ ...form, chat_habilitado: e.target.checked })}
            >
              Habilitar chat ao vivo no /kb e no /portal
            </CheckboxField>
            <div>
              <label htmlFor="kb-chat-setor" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Setor de atendimento
              </label>
              <select
                id="kb-chat-setor"
                value={form.chat_setor_id}
                onChange={(e) => setForm({ ...form, chat_setor_id: e.target.value })}
                className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm dark:border-slate-600 dark:bg-slate-900"
              >
                <option value="">Selecione um setor</option>
                {setoresOpts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nome}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="kb-chat-boas-vindas" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Mensagem de boas-vindas no chat
              </label>
              <textarea
                id="kb-chat-boas-vindas"
                rows={2}
                value={form.chat_texto_boas_vindas}
                onChange={(e) => setForm({ ...form, chat_texto_boas_vindas: e.target.value })}
                className={TEXTAREA_FIELD_CLASS}
                placeholder="Olá! Como podemos ajudar?"
              />
            </div>
          </Card>

          <Card className="grid gap-4 p-4 sm:grid-cols-2 sm:p-5">
            <p className="col-span-full text-xs text-slate-500 dark:text-slate-400">
              Estas cores afetam /kb, /portal e o widget de chat. Navbar e menu lateral podem ter cores
              independentes (por padrão o menu usa a mesma cor da navbar).
            </p>
            <ColorField label="Cor da barra superior (navbar)" value={form.cor_header} onChange={(v) => setForm({ ...form, cor_header: v })} />
            <ColorField
              label="Cor do menu lateral (/portal)"
              value={form.cor_sidebar}
              onChange={(v) => setForm({ ...form, cor_sidebar: v })}
            />
            <ColorField label="Cor do texto da navbar / menu" value={form.cor_texto_header} onChange={(v) => setForm({ ...form, cor_texto_header: v })} />
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
