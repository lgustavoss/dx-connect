import { useEffect, useMemo, useState } from 'react'
import { cadastroAux } from '../../api/client'
import { SelectStringComPesquisa } from './SelectStringComPesquisa'

type Props = {
  id?: string
  label?: string
  uf: string
  value: string
  onChange: (cidade: string) => void
  required?: boolean
  disabled?: boolean
  triggerClassName?: string
}

export function SelectCidadeUf({
  id = 'cidade',
  label = 'Cidade',
  uf,
  value,
  onChange,
  required,
  disabled,
  triggerClassName,
}: Props) {
  const [nomes, setNomes] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const s = uf.trim().toUpperCase()
    if (s.length !== 2 || !/^[A-Za-z]{2}$/.test(s)) {
      setNomes([])
      setLoading(false)
      return
    }
    const ac = new AbortController()
    let cancelled = false
    setLoading(true)
    cadastroAux
      .municipiosPorUf(s, { signal: ac.signal })
      .then((res) => {
        if (!cancelled) setNomes(res.nomes ?? [])
      })
      .catch(() => {
        if (!cancelled) setNomes([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      ac.abort()
    }
  }, [uf])

  const items = useMemo(() => {
    const base = nomes.map((n) => ({ value: n, label: n }))
    const v = value.trim()
    if (v && !nomes.includes(v)) {
      return [{ value: v, label: `${v} (cadastro atual)` }, ...base]
    }
    return base
  }, [nomes, value])

  const semUf = uf.trim().length !== 2 || !/^[A-Za-z]{2}$/.test(uf.trim())

  const emptyPlaceholder = semUf
    ? 'Selecione a UF primeiro'
    : loading
      ? 'Carregando municípios…'
      : nomes.length === 0
        ? 'Não foi possível carregar. Verifique a rede ou tente outra UF.'
        : 'Selecione a cidade'

  return (
    <SelectStringComPesquisa
      id={id}
      label={label}
      value={value}
      onChange={onChange}
      items={items}
      placeholder="Buscar cidade…"
      emptyPlaceholder={emptyPlaceholder}
      required={required}
      disabled={disabled || semUf}
      loading={loading}
      hint="Lista em cache no servidor (atualização periódica IBGE)."
      recentCount={12}
      triggerClassName={triggerClassName}
    />
  )
}
