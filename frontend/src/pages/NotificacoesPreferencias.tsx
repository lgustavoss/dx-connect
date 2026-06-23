import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { notificacoes, type Notificacoes } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'

export function NotificacoesPreferencias() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [prefs, setPrefs] = useState<Notificacoes.Preferencias>({
    email_habilitado: true,
    email_ticket_atribuido: true,
    email_nova_mensagem: true,
    email_sla_em_risco: true,
    email_sla_violado: true,
  })

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    notificacoes
      .preferenciasGet()
      .then((p) => {
        if (!cancelled) setPrefs(p)
      })
      .catch((err) => {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as preferências.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [toast])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const updated = await notificacoes.preferenciasUpdate(prefs)
      setPrefs(updated)
      toast.showSuccess('Preferências salvas.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="h-48 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 pb-10">
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <span aria-hidden>←</span> Voltar
        </Link>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          Notificações por e-mail
        </h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Escolha quando deseja receber e-mails sobre atividade nos seus chamados. Os alertas in-app (sino no topo)
          continuam independentes — fila, mensagens não lidas e WhatsApp.
        </p>
      </div>

      <div className="rounded-xl border border-sky-200/80 bg-sky-50/80 px-4 py-3 text-sm text-sky-950 dark:border-sky-900/50 dark:bg-sky-950/30 dark:text-sky-100">
        <p className="font-medium">Como funciona</p>
        <ul className="mt-2 list-inside list-disc space-y-1 text-xs leading-relaxed text-sky-900/90 dark:text-sky-200/90">
          <li>
            <strong>Atribuído a mim</strong> — quando outro atendente ou admin atribui o chamado a você (não dispara se
            você mesmo usar «Atribuir a mim»).
          </li>
          <li>
            <strong>Nova mensagem</strong> — e-mail do cliente ou mensagem pública de colega; agrupamos avisos do mesmo
            chamado em intervalos de alguns minutos.
          </li>
          <li>
            <strong>SLA em risco / violado</strong> — quando um chamado sob sua responsabilidade (ou do seu setor)
            atinge 80% do prazo ou estoura a meta de primeira resposta ou resolução.
          </li>
          <li>
            Em desenvolvimento, sem SMTP configurado, o sistema simula o envio e registra no log do backend.
          </li>
        </ul>
      </div>

      <Card title="Preferências">
        <form onSubmit={handleSave} className="space-y-5">
          <Switch
            checked={prefs.email_habilitado}
            onCheckedChange={(v) => setPrefs((p) => ({ ...p, email_habilitado: v }))}
            label="Receber notificações por e-mail"
            description="Desliga todos os e-mails abaixo."
            showStatusPill
            statusOnText="Ativo"
            statusOffText="Inativo"
          />

          <div className="space-y-4 border-t border-slate-200 pt-4 dark:border-slate-700">
            <Switch
              checked={prefs.email_ticket_atribuido}
              onCheckedChange={(v) => setPrefs((p) => ({ ...p, email_ticket_atribuido: v }))}
              label="Chamado atribuído a mim"
              disabled={!prefs.email_habilitado}
              showStatusPill
              statusOnText="Sim"
              statusOffText="Não"
            />
            <Switch
              checked={prefs.email_nova_mensagem}
              onCheckedChange={(v) => setPrefs((p) => ({ ...p, email_nova_mensagem: v }))}
              label="Nova mensagem em chamado sob minha responsabilidade"
              description="Mensagens do cliente ou de colegas (agrupadas em intervalos de alguns minutos)."
              disabled={!prefs.email_habilitado}
              showStatusPill
              statusOnText="Sim"
              statusOffText="Não"
            />
            <Switch
              checked={prefs.email_sla_em_risco}
              onCheckedChange={(v) => setPrefs((p) => ({ ...p, email_sla_em_risco: v }))}
              label="SLA em risco (80% do prazo)"
              description="Primeira resposta ou resolução próximas do limite."
              disabled={!prefs.email_habilitado}
              showStatusPill
              statusOnText="Sim"
              statusOffText="Não"
            />
            <Switch
              checked={prefs.email_sla_violado}
              onCheckedChange={(v) => setPrefs((p) => ({ ...p, email_sla_violado: v }))}
              label="SLA violado"
              description="Meta de primeira resposta ou resolução estourada."
              disabled={!prefs.email_habilitado}
              showStatusPill
              statusOnText="Sim"
              statusOffText="Não"
            />
          </div>

          <div className="flex justify-end border-t border-slate-200 pt-4 dark:border-slate-700">
            <Button type="submit" disabled={saving}>
              {saving ? 'Salvando…' : 'Salvar preferências'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
