import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, saasClientes, saasPlanos, type SaasCatalogo } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { DetailRow } from '../../components/ui/DetailRow'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { SemPermissao } from '../SemPermissao'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import { VoltarButton } from '../../components/ui/VoltarButton'
import {
  badgeClassAprovacao,
  badgeClassStatusClienteSaaS,
  hrefAcessoCliente,
  labelAprovacao,
  labelProvisionamento,
  labelStatusClienteSaaS,
  renovacaoAlerta,
  saasBaseDomain,
  urlInstanciaFromSlug,
} from '../../lib/saasControlPlane'

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = iso.slice(0, 10)
  const [y, m, day] = d.split('-')
  if (!y || !m || !day) return iso
  return `${day}/${m}/${y}`
}

function addDaysIso(days: number): string {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function SaasLicencaDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/saas/licencas')
  const clienteId = id ? parseInt(id, 10) : NaN

  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [item, setItem] = useState<Awaited<ReturnType<typeof saasClientes.get>> | null>(null)
  const [diasRenovacao, setDiasRenovacao] = useState('30')
  const [novaDataRenovacao, setNovaDataRenovacao] = useState(addDaysIso(30))
  const [baseDomain, setBaseDomain] = useState(saasBaseDomain())
  const [planos, setPlanos] = useState<SaasCatalogo.Plano[]>([])
  const [planoAprovarId, setPlanoAprovarId] = useState<number | ''>('')
  const [timeline, setTimeline] = useState<
    Awaited<ReturnType<typeof saasClientes.timeline>>
  >([])

  function carregar() {
    if (!id || Number.isNaN(clienteId)) {
      setFalha({ titulo: 'Licença não encontrada.', detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    setFalha(null)
    Promise.all([
      saasClientes.get(clienteId),
      saasClientes.resumo().catch(() => null),
      saasClientes.timeline(clienteId).catch(() => []),
    ])
      .then(([c, resumo, events]) => {
        setItem(c)
        setTimeline(events)
        if (resumo?.base_dominio_provisionamento) {
          setBaseDomain(saasBaseDomain(resumo.base_dominio_provisionamento))
        }
        setPlanoAprovarId(c.plano_id ?? '')
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          const detail =
            typeof err.body === 'object' && err.body && 'detail' in err.body
              ? String((err.body as { detail?: unknown }).detail ?? '')
              : ''
          if (detail.toLowerCase().includes('não disponível')) {
            setIndisponivel(true)
          } else {
            setFalha(interpretarFalhaCarregamento(err, 'Licença não encontrada.'))
          }
          return
        }
        setFalha(interpretarFalhaCarregamento(err, 'Licença não encontrada.'))
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recarrega só quando muda o id
  }, [id, clienteId])

  useEffect(() => {
    saasPlanos
      .list()
      .then((list) => {
        setPlanos(list)
        setPlanoAprovarId((cur) => {
          if (cur !== '') return cur
          const trial = list.find((p) => p.codigo === 'trial' && p.ativo)
          const pro = list.find((p) => p.codigo === 'profissional' && p.ativo)
          return trial?.id ?? pro?.id ?? list.find((p) => p.ativo)?.id ?? ''
        })
      })
      .catch(() => setPlanos([]))
  }, [])

  async function runAction(
    action: () => Promise<Awaited<ReturnType<typeof saasClientes.get>>>,
    okMsg: string,
  ) {
    setActing(true)
    try {
      const updated = await action()
      setItem(updated)
      toast.showSuccess(okMsg)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível concluir a ação.'))
    } finally {
      setActing(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <div className="h-40 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel de licenças não disponível nesta instância."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para acessar esta licença."
        voltarPara="/saas/licencas"
        voltarLabel="Voltar para Licenças"
      />
    )
  }

  if (falha) {
    return <CarregamentoFalhou titulo={falha.titulo} detalhe={falha.detalhe} onVoltar={voltarAnterior} />
  }

  if (!item) return null

  const urlPublica =
    item.instancia_url || urlInstanciaFromSlug(item.slug, baseDomain) || ''
  const acesso = hrefAcessoCliente({
    instanciaUrl: urlPublica,
    slug: item.slug,
    apiPort: item.api_port,
    baseDomain,
  })

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <VoltarButton onClick={voltarAnterior} />

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
            {item.nome}
          </h1>
          <div className="flex flex-wrap gap-2">
            <span
              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClassStatusClienteSaaS(item.status)}`}
            >
              {labelStatusClienteSaaS(item.status)}
            </span>
            <span
              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClassAprovacao(item.aprovacao_status)}`}
            >
              Aprovação: {labelAprovacao(item.aprovacao_status)}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" disabled={acting} onClick={() => navigate(`/saas/licencas/${item.id}/editar`)}>
            Editar
          </Button>
          {item.aprovacao_status === 'pendente' ? (
            <>
              <div className="min-w-[12rem]">
                <Select
                  label="Plano no go-live"
                  value={planoAprovarId}
                  onChange={(v) => setPlanoAprovarId(v === '' ? '' : Number(v))}
                  options={planos
                    .filter((p) => p.ativo || p.id === planoAprovarId)
                    .map((p) => ({
                      value: p.id,
                      label: p.ativo ? p.nome : `${p.nome} (inactivo)`,
                    }))}
                  includeEmpty
                  emptyLabel="Manter actual"
                  disabled={acting}
                />
              </div>
              <Button
                disabled={acting}
                onClick={() =>
                  runAction(
                    () =>
                      saasClientes.aprovar(item.id, {
                        ativar: true,
                        provisionar: true,
                        plano_id: planoAprovarId === '' ? null : Number(planoAprovarId),
                      }),
                    'Licença aprovada — criação da base enfileirada.',
                  )
                }
              >
                Aprovar e criar base
              </Button>
              <Button
                variant="secondary"
                disabled={acting}
                onClick={() => {
                  const notas = window.prompt('Motivo da rejeição (opcional):') ?? undefined
                  void runAction(
                    () => saasClientes.rejeitar(item.id, { notas: notas || null }),
                    'Licença rejeitada.',
                  )
                }}
              >
                Rejeitar
              </Button>
            </>
          ) : null}
          {item.status !== 'suspenso' && item.status !== 'churn' ? (
            <Button
              variant="secondary"
              disabled={acting}
              onClick={() => runAction(() => saasClientes.suspender(item.id), 'Cliente suspenso.')}
            >
              Suspender
            </Button>
          ) : item.status === 'suspenso' ? (
            <Button
              variant="secondary"
              disabled={acting}
              onClick={() => runAction(() => saasClientes.reativar(item.id), 'Cliente reativado.')}
            >
              Reativar
            </Button>
          ) : null}
          {item.provisionamento_status !== 'sucesso' && item.provisionamento_status !== 'em_progresso' ? (
            <Button
              variant="secondary"
              disabled={acting}
              onClick={() =>
                runAction(
                  () => saasClientes.solicitarProvisionamento(item.id),
                  'Provisionamento enfileirado.',
                )
              }
            >
              {item.provisionamento_solicitado ? 'Reenviar à fila' : 'Solicitar provisionamento'}
            </Button>
          ) : null}
        </div>
      </header>

      {(() => {
        const alerta = renovacaoAlerta(item.dias_para_renovacao)
        if (!alerta || alerta === 'ok') return null
        return (
          <div
            className={`rounded-2xl border px-4 py-3 text-sm ${
              alerta === 'vencido'
                ? 'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700/50 dark:bg-amber-950/40 dark:text-amber-100'
                : 'border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-700/50 dark:bg-sky-950/40 dark:text-sky-100'
            }`}
          >
            {alerta === 'vencido'
              ? `Licença vencida há ${Math.abs(item.dias_para_renovacao ?? 0)} dia(s). Renove ou mantenha suspensa.`
              : `Renovação em ${item.dias_para_renovacao} dia(s) (${formatDate(item.data_renovacao)}).`}
          </div>
        )
      })()}

      <Card title="Dados da licença">
        <dl>
          <DetailRow label="ID" value={String(item.id)} mono />
          <DetailRow label="Slug" value={item.slug} mono />
          <DetailRow label="Plano" value={item.plano || '—'} />
          {item.plano_modulos && item.plano_modulos.length > 0 ? (
            <DetailRow
              label="Módulos do plano"
              value={item.plano_modulos.map((m) => m.nome).join(', ')}
            />
          ) : null}
          {item.modulos_snapshot && item.modulos_snapshot.length > 0 ? (
            <DetailRow label="Snapshot módulos" value={item.modulos_snapshot.join(', ')} mono />
          ) : null}
          <DetailRow
            label="Limites"
            value={
              item.max_postos != null || item.max_usuarios != null
                ? [
                    item.max_postos != null ? `${item.max_postos} postos` : null,
                    item.max_usuarios != null ? `${item.max_usuarios} utilizadores` : null,
                  ]
                    .filter(Boolean)
                    .join(' · ')
                : '—'
            }
          />
          <DetailRow label="Contacto" value={item.contato_nome || '—'} />
          <DetailRow label="E-mail" value={item.contato_email || '—'} />
          <DetailRow label="Início" value={formatDate(item.data_inicio)} />
          <DetailRow
            label="Renovação"
            value={
              item.data_renovacao
                ? `${formatDate(item.data_renovacao)}${
                    item.dias_para_renovacao != null ? ` (${item.dias_para_renovacao} dia(s))` : ''
                  }`
                : '—'
            }
          />
          <DetailRow label="Instância" value={urlPublica || '—'} />
          <DetailRow label="Porta API" value={item.api_port != null ? String(item.api_port) : '—'} mono />
          <DetailRow label="Provisionamento" value={labelProvisionamento(item.provisionamento_status)} />
          <DetailRow label="Detalhe da fila" value={item.provisionamento_mensagem || '—'} />
          <DetailRow label="Aprovação" value={labelAprovacao(item.aprovacao_status)} />
          <DetailRow label="Notas de aprovação" value={item.aprovacao_notas || '—'} />
          <DetailRow
            label="Stack"
            value={
              item.stack_status
                ? `${item.stack_status}${item.stack_ops_pendente ? ` · pendente: ${item.stack_ops_pendente}` : ''}`
                : item.stack_ops_pendente
                  ? `pendente: ${item.stack_ops_pendente}`
                  : '—'
            }
          />
          <DetailRow
            label="Lead de origem"
            value={item.lead_comercial_id != null ? `#${item.lead_comercial_id}` : '—'}
          />
          <DetailRow
            label="Entrega ao contacto"
            value={item.entrega_notificada_em ? formatDate(item.entrega_notificada_em) : 'Não enviada'}
          />
          <DetailRow label="Notas" value={item.notas || '—'} />
        </dl>
      </Card>

      {item.lead_comercial_id != null ? (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-200">
          Convertido do lead{' '}
          <button
            type="button"
            className="font-medium text-sky-600 hover:underline dark:text-sky-400"
            onClick={() => navigate(`/saas/leads/${item.lead_comercial_id}`)}
          >
            #{item.lead_comercial_id}
          </button>
          .
        </div>
      ) : null}

      {item.aprovacao_status === 'pendente' ? (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700/50 dark:bg-amber-950/40 dark:text-amber-100">
          Aprovação comercial pendente. Use <strong>Aprovar e criar base</strong> para activar a licença e
          enfileirar a criação da base, ou <strong>Rejeitar</strong> para cancelar. Em local (Windows), se ficar
          em «aguardando ops», corra no host{' '}
          <code className="text-xs">./deploy/scripts/saas-drain-queue.sh</code>.
        </div>
      ) : null}

      {item.provisionamento_status === 'sucesso' && item.contato_email ? (
        <Card title="Entrega ao contacto">
          <p className="mb-4 text-sm text-slate-600 dark:text-slate-300">
            {item.entrega_notificada_em
              ? `Último e-mail de acesso enviado em ${formatDate(item.entrega_notificada_em)} para ${item.contato_email}.`
              : `Instância pronta. Ainda não há registo de e-mail de entrega para ${item.contato_email}.`}
          </p>
          <Button
            variant="secondary"
            disabled={acting}
            onClick={() =>
              runAction(() => saasClientes.reenviarEntrega(item.id), 'E-mail de entrega enviado.')
            }
          >
            {item.entrega_notificada_em ? 'Reenviar entrega' : 'Enviar entrega'}
          </Button>
        </Card>
      ) : null}

      {item.stack_ops_pendente ? (
        <Card title="Stack Docker (ops)">
          <p className="mb-4 text-sm text-slate-600 dark:text-slate-300">
            {item.stack_ops_mensagem ||
              (item.stack_ops_pendente === 'down'
                ? 'Pare a stack no host e confirme.'
                : 'Suba a stack no host e confirme.')}
          </p>
          {item.comandos_stack ? (
            <div className="mb-4 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Comandos</p>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={acting}
                  onClick={() => {
                    void navigator.clipboard.writeText(item.comandos_stack || '').then(
                      () => toast.showSuccess('Comandos copiados.'),
                      () => toast.showError('Não foi possível copiar.'),
                    )
                  }}
                >
                  Copiar
                </Button>
              </div>
              <pre className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-950 p-3 text-xs leading-relaxed text-slate-100 dark:border-slate-700">
                {item.comandos_stack}
              </pre>
            </div>
          ) : null}
          <Button
            variant="secondary"
            disabled={acting}
            onClick={() =>
              runAction(() => saasClientes.confirmarStack(item.id), 'Operação de stack confirmada.')
            }
          >
            Confirmar stack
          </Button>
        </Card>
      ) : null}

      {item.provisionamento_status === 'falha' || item.provisionamento_status === 'aguardando_ops' ? (
        <Card title="Provisionamento (ops)">
          {item.provisionamento_status === 'falha' ? (
            <div className="mb-4 rounded-2xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-700/50 dark:bg-red-950/40 dark:text-red-100">
              {item.provisionamento_mensagem || 'Falha no provisionamento. Reenvie à fila ou corrija e confirme.'}
            </div>
          ) : (
            <p className="mb-4 text-sm text-slate-600 dark:text-slate-300">
              Execução automática desligada. Corra os scripts no host de deploy e, com health OK, confirme abaixo.
            </p>
          )}
          {item.comandos_ops ? (
            <div className="mb-4 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Comandos</p>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={acting}
                  onClick={() => {
                    void navigator.clipboard.writeText(item.comandos_ops || '').then(
                      () => toast.showSuccess('Comandos copiados.'),
                      () => toast.showError('Não foi possível copiar.'),
                    )
                  }}
                >
                  Copiar
                </Button>
              </div>
              <pre className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-950 p-3 text-xs leading-relaxed text-slate-100 dark:border-slate-700">
                {item.comandos_ops}
              </pre>
            </div>
          ) : null}
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <Button
              variant="secondary"
              disabled={acting}
              onClick={() =>
                runAction(
                  () => saasClientes.confirmarProvisionamento(item.id),
                  'Provisionamento confirmado.',
                )
              }
            >
              Confirmar provisionamento
            </Button>
            {item.provisionamento_status === 'falha' ? (
              <Button
                variant="secondary"
                disabled={acting}
                onClick={() =>
                  runAction(
                    () => saasClientes.solicitarProvisionamento(item.id),
                    'Provisionamento reenviado à fila.',
                  )
                }
              >
                Reenviar à fila
              </Button>
            ) : null}
          </div>
        </Card>
      ) : null}

      <Card title="Renovar licença">
        <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="w-full sm:w-36">
            <Input
              label="Dias"
              type="number"
              min={1}
              max={3650}
              value={diasRenovacao}
              onChange={(e) => setDiasRenovacao(e.target.value)}
            />
          </div>
          <Button
            variant="secondary"
            disabled={acting}
            onClick={() => {
              const dias = parseInt(diasRenovacao, 10)
              if (!Number.isFinite(dias) || dias < 1) {
                toast.showError('Informe um número de dias válido.')
                return
              }
              void runAction(
                () => saasClientes.renovar(item.id, { dias }),
                `Licença renovada por ${dias} dia(s).`,
              )
            }}
          >
            Renovar por dias
          </Button>
          <div className="w-full sm:w-48">
            <Input
              label="Nova data"
              type="date"
              value={novaDataRenovacao}
              onChange={(e) => setNovaDataRenovacao(e.target.value)}
            />
          </div>
          <Button
            variant="secondary"
            disabled={acting}
            onClick={() => {
              if (!novaDataRenovacao.trim()) {
                toast.showError('Informe a nova data de renovação.')
                return
              }
              void runAction(
                () => saasClientes.renovar(item.id, { nova_data: novaDataRenovacao }),
                'Data de renovação atualizada.',
              )
            }}
          >
            Definir data
          </Button>
        </div>
      </Card>

      <Card title="URL da instância">
        <p className="mb-1 font-mono text-sm text-slate-800 dark:text-slate-100">
          {urlPublica || '—'}
        </p>
        <p className="mb-4 text-sm text-slate-600 dark:text-slate-300">
          Derivada do nome da base (<code className="text-xs">{item.slug}</code>
          .{baseDomain}). Em ambiente local o DNS público não resolve — use o acesso pela porta API.
        </p>
        <Button
          variant="secondary"
          disabled={acting}
          onClick={() => {
            const url = urlInstanciaFromSlug(item.slug, baseDomain)
            if (!url) {
              toast.showError('Não foi possível montar a URL a partir do slug.')
              return
            }
            void runAction(
              () => saasClientes.registrarInstancia(item.id, { instancia_url: url }),
              'URL sincronizada a partir do slug.',
            )
          }}
        >
          Sincronizar URL do slug
        </Button>
      </Card>

      {acesso ? (
        <Card title="Acesso à instância">
          {acesso.modo === 'local' ? (
            <p className="mb-3 text-sm text-amber-800 dark:text-amber-200">
              Ambiente local: <code className="text-xs">*.{baseDomain}</code> não tem DNS. Abrindo health
              na porta API. Em Windows, pode mapear no ficheiro hosts se precisar do domínio público.
            </p>
          ) : null}
          <a
            href={acesso.href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-sky-600 hover:underline dark:text-sky-400"
          >
            Abrir {acesso.label}
          </a>
        </Card>
      ) : null}

      <Card title="Histórico">
        {timeline.length === 0 ? (
          <p className="text-sm text-slate-500">Sem eventos de auditoria para esta licença.</p>
        ) : (
          <ul className="space-y-3">
            {timeline.map((ev) => (
              <li key={ev.id} className="border-l-2 border-sky-300 pl-3 dark:border-sky-700">
                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{ev.label}</p>
                <p className="text-xs text-slate-500">
                  {ev.created_at
                    ? new Date(ev.created_at).toLocaleString('pt-BR')
                    : '—'}
                  {ev.atendente_id != null ? ` · atendente #${ev.atendente_id}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
