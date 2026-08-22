import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  comercialImplantacaoTemplates,
  setores,
  type ImplantacaoChecklist,
  type Setores,
} from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { CheckboxField } from '../components/ui/CheckboxField'
import { Input, TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'

type ItemForm = {
  titulo: string
  descricao: string
  obrigatorio: boolean
  chave: string
}

const CHAVE_PDVS = 'cadastrar_pdvs'

const itensPadrao = (): ItemForm[] => [
  {
    titulo: 'Coleta de documentos',
    descricao: 'Contrato assinado, dados fiscais e acessos necessários.',
    obrigatorio: true,
    chave: '',
  },
  {
    titulo: 'Cadastro na base WebPosto',
    descricao: 'Criar ou confirmar a base e os logins operacionais.',
    obrigatorio: true,
    chave: '',
  },
  {
    titulo: 'Cadastrar PDVs',
    descricao: 'Cadastrar os PDVs da empresa (cadastro operacional).',
    obrigatorio: true,
    chave: CHAVE_PDVS,
  },
  {
    titulo: 'Treinamento da equipe',
    descricao: 'Treinamento de operação (caixa, retaguarda, helpdesk).',
    obrigatorio: true,
    chave: '',
  },
  {
    titulo: 'Validação operacional',
    descricao: 'Conferir operação no dia a dia antes de encerrar a implantação.',
    obrigatorio: false,
    chave: '',
  },
]

const emptyItem = (): ItemForm => ({ titulo: '', descricao: '', obrigatorio: true, chave: '' })

export function ConfigImplantacaoChecklist({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [list, setList] = useState<ImplantacaoChecklist.Template[]>([])
  const [setorOpts, setSetorOpts] = useState<Setores.Setor[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [editing, setEditing] = useState<ImplantacaoChecklist.Template | 'create' | null>(null)
  const [nome, setNome] = useState('')
  const [setorId, setSetorId] = useState<number | ''>('')
  const [ativo, setAtivo] = useState(true)
  const [itens, setItens] = useState<ItemForm[]>([])
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    Promise.all([
      comercialImplantacaoTemplates.list({ incluir_inativos: true }),
      setores.list().catch(() => ({ items: [] as Setores.Setor[], total: 0 })),
    ])
      .then(([templates, sts]) => {
        setList(templates)
        setSetorOpts(sts.items || [])
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 403) setForbidden(true)
        else toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar o checklist.'))
      })
      .finally(() => setLoading(false))
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  const openCreate = () => {
    setEditing('create')
    setNome('Implantação')
    setSetorId('')
    setAtivo(true)
    setItens(itensPadrao())
  }

  const openEdit = (row: ImplantacaoChecklist.Template) => {
    setEditing(row)
    setNome(row.nome)
    setSetorId(row.setor_id ?? '')
    setAtivo(row.ativo)
    setItens(
      row.itens.map((i) => ({
        titulo: i.titulo,
        descricao: i.descricao || '',
        obrigatorio: i.obrigatorio,
        chave: i.chave || '',
      })),
    )
  }

  const save = async () => {
    if (!editing) return
    setSaving(true)
    const payload = {
      nome,
      setor_id: setorId === '' ? null : Number(setorId),
      ativo,
      itens: itens
        .filter((i) => i.titulo.trim())
        .map((i, idx) => ({
          titulo: i.titulo.trim(),
          descricao: i.descricao.trim() || null,
          ordem: idx + 1,
          obrigatorio: i.obrigatorio,
          chave: i.chave.trim() || null,
        })),
    }
    try {
      if (editing === 'create') {
        await comercialImplantacaoTemplates.create(payload)
        toast.showSuccess('Checklist criado.')
      } else {
        await comercialImplantacaoTemplates.update(editing.id, payload)
        toast.showSuccess('Checklist guardado.')
      }
      setEditing(null)
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível guardar.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={<SemPermissao title="Só administradores editam o checklist de implantação." />}
      title="Checklist de implantação"
      subtitle="Itens copiados para o ticket automático quando o contrato é marcado como assinado. Se houver vários modelos ativos, usa-se o mais antigo."
      actions={<Button onClick={openCreate}>Novo modelo</Button>}
    >
      {loading ? <p className="text-sm text-slate-500">A carregar…</p> : null}
      <div className="space-y-3">
        {list.map((row) => (
          <Card key={row.id} className="p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-medium text-slate-800 dark:text-slate-100">{row.nome}</p>
                <p className="text-xs text-slate-500">
                  Setor: {row.setor_nome || '— (Suporte / Implantação se existir)'} · {row.itens.length} itens
                  {row.ativo ? '' : ' · inativo'}
                </p>
              </div>
              <Button variant="secondary" onClick={() => openEdit(row)}>
                Editar
              </Button>
            </div>
          </Card>
        ))}
      </div>
      {editing ? (
        <div className="mt-4 space-y-3 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
            {editing === 'create' ? 'Novo modelo' : 'Editar modelo'}
          </p>
          <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} />
          <Select
            label="Setor do ticket automático"
            value={setorId}
            onChange={(v) => setSetorId(v === '' ? '' : Number(v))}
            includeEmpty
            emptyLabel="Detetar Implantação ou Suporte"
            options={setorOpts.map((s) => ({ value: s.id, label: s.nome }))}
          />
          <Switch
            checked={ativo}
            onCheckedChange={setAtivo}
            label="Modelo ativo"
            showStatusPill
          />
          <div className="space-y-3">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              No item de PDVs, a chave deve ser{' '}
              <code className="font-mono text-[11px]">cadastrar_pdvs</code> para aparecer o atalho no ticket.
              Outras chaves não têm efeito nesta versão.
            </p>
            {itens.map((item, idx) => (
              <div key={idx} className="space-y-2 rounded-lg border border-slate-100 p-3 dark:border-slate-800">
                <Input
                  label={`Item ${idx + 1}`}
                  value={item.titulo}
                  onChange={(e) =>
                    setItens((p) => p.map((it, i) => (i === idx ? { ...it, titulo: e.target.value } : it)))
                  }
                />
                <textarea
                  className={TEXTAREA_FIELD_CLASS}
                  rows={2}
                  placeholder="Descrição (opcional)"
                  value={item.descricao}
                  onChange={(e) =>
                    setItens((p) => p.map((it, i) => (i === idx ? { ...it, descricao: e.target.value } : it)))
                  }
                />
                <CheckboxField
                  checked={item.obrigatorio}
                  onChange={(e) =>
                    setItens((p) => p.map((it, i) => (i === idx ? { ...it, obrigatorio: e.target.checked } : it)))
                  }
                >
                  Obrigatório para fechar o ticket
                </CheckboxField>
                <Input
                  label="Chave (opcional)"
                  value={item.chave}
                  placeholder="cadastrar_pdvs"
                  onChange={(e) =>
                    setItens((p) => p.map((it, i) => (i === idx ? { ...it, chave: e.target.value } : it)))
                  }
                />
                <Button
                  variant="ghost"
                  onClick={() => setItens((p) => p.filter((_, i) => i !== idx))}
                >
                  Remover item
                </Button>
              </div>
            ))}
            <Button variant="secondary" onClick={() => setItens((p) => [...p, emptyItem()])}>
              Adicionar item
            </Button>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => void save()} disabled={saving}>
              Guardar
            </Button>
            <Button variant="cancel" onClick={() => setEditing(null)}>
              Cancelar
            </Button>
          </div>
        </div>
      ) : null}
    </ConfigListPageShell>
  )
}
