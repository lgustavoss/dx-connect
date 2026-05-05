import { useEffect, useState } from 'react'
import { cadastroAux } from '../../api/client'
import { UFS_BRASIL_OPTIONS } from '../../constants/ufsBrasil'
import { SelectStringComPesquisa, type ItemStringPesquisa } from './SelectStringComPesquisa'

type Props = {
  id?: string
  label?: string
  value: string
  onChange: (sigla: string) => void
  required?: boolean
  disabled?: boolean
  triggerClassName?: string
}

export function SelectUf({
  id = 'uf',
  label = 'UF',
  value,
  onChange,
  required,
  disabled,
  triggerClassName,
}: Props) {
  const [items, setItems] = useState<ItemStringPesquisa[]>(UFS_BRASIL_OPTIONS)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const ac = new AbortController()
    let cancelled = false
    setLoading(true)
    cadastroAux
      .ufs({ signal: ac.signal })
      .then((ufs) => {
        if (cancelled) return
        setItems(ufs.map((u) => ({ value: u.sigla, label: `${u.sigla} — ${u.nome}` })))
      })
      .catch(() => {
        if (!cancelled) setItems(UFS_BRASIL_OPTIONS)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      ac.abort()
    }
  }, [])

  return (
    <SelectStringComPesquisa
      id={id}
      label={label}
      value={value.toUpperCase()}
      onChange={(v) => onChange(v.toUpperCase())}
      items={items}
      placeholder="Buscar estado…"
      emptyPlaceholder="Selecione a UF"
      required={required}
      disabled={disabled}
      loading={loading}
      hint="Lista obtida no servidor (IBGE)."
      recentCount={9}
      triggerClassName={triggerClassName}
    />
  )
}
