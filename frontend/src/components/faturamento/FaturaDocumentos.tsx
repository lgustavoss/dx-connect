import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ApiError,
  faturamento,
  fetchFaturaAnexoBlob,
  type Faturamento,
} from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Input } from '../ui/Input'
import { useToast } from '../ui/Toast'

type TipoAnexo = 'boleto' | 'nfse_pdf' | 'nfse_xml'

const TIPO_LABEL: Record<TipoAnexo, string> = {
  boleto: 'Boleto (PDF)',
  nfse_pdf: 'NFS-e (PDF)',
  nfse_xml: 'NFS-e (XML, opcional)',
}

function anexoDoTipo(fatura: Faturamento.Fatura, tipo: TipoAnexo) {
  return (fatura.anexos ?? []).find((a) => a.tipo === tipo)
}

async function baixar(faturaId: number, anexo: Faturamento.Anexo) {
  const blob = await fetchFaturaAnexoBlob(faturaId, anexo.id)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = anexo.nome_original || `documento-${anexo.id}`
  a.click()
  URL.revokeObjectURL(url)
}

export function FaturaDocumentos({
  fatura,
  podeEditar,
  onChanged,
  onClose,
}: {
  fatura: Faturamento.Fatura
  podeEditar: boolean
  onChanged: (fatura: Faturamento.Fatura) => void
  onClose: () => void
}) {
  const toast = useToast()
  const [linha, setLinha] = useState(fatura.boleto_linha_digitavel ?? '')
  const [nossoNumero, setNossoNumero] = useState(fatura.boleto_nosso_numero ?? '')
  const [nfseNumero, setNfseNumero] = useState(fatura.nfse_numero ?? '')
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState<TipoAnexo | null>(null)
  const inputs = useRef<Partial<Record<TipoAnexo, HTMLInputElement | null>>>({})

  const aprovada = fatura.status === 'aprovada'
  const edita = podeEditar && aprovada

  async function salvarDados() {
    setSaving(true)
    try {
      const atualizada = await faturamento.atualizarDocumentos(fatura.id, {
        boleto_linha_digitavel: linha,
        boleto_nosso_numero: nossoNumero,
        nfse_numero: fatura.emite_nfse ? nfseNumero : '',
      })
      onChanged(atualizada)
      toast.showSuccess('Dados do boleto e da nota salvos.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível salvar os dados.'))
    } finally {
      setSaving(false)
    }
  }

  async function enviar(tipo: TipoAnexo, file: File) {
    setUploading(tipo)
    try {
      const atualizada = await faturamento.enviarAnexo(fatura.id, file, tipo)
      onChanged(atualizada)
      toast.showSuccess('Arquivo gravado.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível enviar o arquivo.'))
    } finally {
      setUploading(null)
    }
  }

  async function baixarAnexo(anexo: Faturamento.Anexo) {
    try {
      await baixar(fatura.id, anexo)
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 404
          ? 'Arquivo não está no servidor. Envie de novo.'
          : mensagemFalhaParaToast(err, 'Não foi possível baixar o arquivo.')
      toast.showWarning(msg)
    }
  }

  async function remover(anexo: Faturamento.Anexo) {
    setUploading(anexo.tipo as TipoAnexo)
    try {
      const atualizada = await faturamento.removerAnexo(fatura.id, anexo.id)
      onChanged(atualizada)
      toast.showSuccess('Arquivo removido.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível remover o arquivo.'))
    } finally {
      setUploading(null)
    }
  }

  const tipos: TipoAnexo[] = fatura.emite_nfse ? ['boleto', 'nfse_pdf', 'nfse_xml'] : ['boleto']

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
            Documentos — {fatura.razao_social || fatura.empresa_nome || `Contrato #${fatura.contrato_id}`}
          </p>
          <p className="text-xs text-slate-500">
            Competência {fatura.competencia}
            {fatura.empresa_id ? (
              <>
                {' · '}
                <Link className="text-sky-700 hover:underline dark:text-sky-300" to={`/empresas/${fatura.empresa_id}`}>
                  Abrir empresa
                </Link>
              </>
            ) : null}
          </p>
        </div>
        <Button variant="ghost" onClick={onClose}>
          Fechar
        </Button>
      </div>

      {!aprovada ? (
        <p className="text-sm text-slate-500">Aprove a fatura para anexar boleto e nota.</p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="Linha digitável"
          value={linha}
          onChange={(e) => setLinha(e.target.value)}
          disabled={!edita}
          hint="Números do boleto (44 a 48 dígitos)"
        />
        <Input
          label="Nosso número"
          value={nossoNumero}
          onChange={(e) => setNossoNumero(e.target.value)}
          disabled={!edita}
        />
        {fatura.emite_nfse ? (
          <Input
            label="Número da NFS-e"
            value={nfseNumero}
            onChange={(e) => setNfseNumero(e.target.value)}
            disabled={!edita}
          />
        ) : (
          <p className="self-end text-xs text-slate-500">Esta empresa não emite NFS-e — só o boleto.</p>
        )}
      </div>

      {edita ? (
        <Button onClick={salvarDados} disabled={saving} loading={saving}>
          Salvar dados
        </Button>
      ) : null}

      <ul className="space-y-3">
        {tipos.map((tipo) => {
          const atual = anexoDoTipo(fatura, tipo)
          return (
            <li
              key={tipo}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700"
            >
              <div>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{TIPO_LABEL[tipo]}</p>
                <p className="text-xs text-slate-500">{atual ? atual.nome_original : 'Nenhum arquivo'}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {atual ? (
                  <Button variant="secondary" onClick={() => baixarAnexo(atual)}>
                    Baixar 2ª via
                  </Button>
                ) : null}
                {edita ? (
                  <>
                    <input
                      ref={(el) => {
                        inputs.current[tipo] = el
                      }}
                      type="file"
                      className="hidden"
                      accept={tipo === 'nfse_xml' ? '.xml,text/xml,application/xml' : 'application/pdf,.pdf'}
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        e.target.value = ''
                        if (file) void enviar(tipo, file)
                      }}
                    />
                    <Button
                      variant="ghost"
                      disabled={uploading === tipo}
                      onClick={() => inputs.current[tipo]?.click()}
                    >
                      {atual ? 'Substituir' : 'Enviar'}
                    </Button>
                    {atual ? (
                      <Button variant="ghost" disabled={uploading === tipo} onClick={() => void remover(atual)}>
                        Remover
                      </Button>
                    ) : null}
                  </>
                ) : null}
              </div>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
