import { useState } from 'react'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { linkMapaOsm } from '../lib/pontoFormat'

export type PontoLocalMapaValue = {
  latitude: number | null
  longitude: number | null
  endereco?: string
  raio_metros?: number
}

type Props = {
  value: PontoLocalMapaValue
  onChange: (next: PontoLocalMapaValue) => void
  /** Prefill de busca (ex.: endereço da empresa). */
  buscaInicial?: string
  mostrarRaio?: boolean
  raioLabel?: string
}

type NominatimHit = {
  display_name: string
  lat: string
  lon: string
}

function embedUrl(lat: number, lon: number, delta = 0.008): string {
  const bbox = `${lon - delta},${lat - delta},${lon + delta},${lat + delta}`
  return `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik&marker=${lat}%2C${lon}`
}

export function PontoLocalMapaPicker({
  value,
  onChange,
  buscaInicial = '',
  mostrarRaio = true,
  raioLabel = 'Raio (m)',
}: Props) {
  const [busca, setBusca] = useState(buscaInicial)
  const [buscando, setBuscando] = useState(false)
  const [hits, setHits] = useState<NominatimHit[]>([])
  const [erroBusca, setErroBusca] = useState<string | null>(null)

  const lat = value.latitude
  const lon = value.longitude
  const temPin = lat != null && lon != null && Number.isFinite(lat) && Number.isFinite(lon)

  async function buscarNoMapa() {
    const q = busca.trim()
    if (!q) {
      setErroBusca('Informe um endereço para buscar.')
      return
    }
    setBuscando(true)
    setErroBusca(null)
    setHits([])
    try {
      const url =
        'https://nominatim.openstreetmap.org/search?' +
        new URLSearchParams({
          q,
          format: 'json',
          limit: '5',
          addressdetails: '0',
        }).toString()
      const res = await fetch(url, {
        headers: { Accept: 'application/json' },
      })
      if (!res.ok) throw new Error('falha')
      const data = (await res.json()) as NominatimHit[]
      if (!data.length) {
        setErroBusca('Nenhum resultado. Ajuste o endereço ou informe latitude/longitude.')
        return
      }
      setHits(data)
    } catch {
      setErroBusca('Não foi possível buscar o endereço. Tente de novo ou use lat/lon.')
    } finally {
      setBuscando(false)
    }
  }

  function escolherHit(hit: NominatimHit) {
    const latitude = Number(hit.lat)
    const longitude = Number(hit.lon)
    onChange({
      ...value,
      latitude,
      longitude,
      endereco: hit.display_name,
    })
    setBusca(hit.display_name)
    setHits([])
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[12rem] flex-1">
          <Input
            label="Buscar endereço no mapa"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Rua, número, cidade…"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                void buscarNoMapa()
              }
            }}
          />
        </div>
        <Button type="button" variant="secondary" disabled={buscando} onClick={() => void buscarNoMapa()}>
          {buscando ? 'Buscando…' : 'Buscar'}
        </Button>
      </div>
      {erroBusca ? <p className="text-sm text-amber-700 dark:text-amber-300">{erroBusca}</p> : null}
      {hits.length > 0 ? (
        <ul className="max-h-40 space-y-1 overflow-auto rounded-lg border border-slate-200 text-sm dark:border-slate-700">
          {hits.map((h) => (
            <li key={`${h.lat}-${h.lon}-${h.display_name}`}>
              <button
                type="button"
                className="w-full px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800"
                onClick={() => escolherHit(h)}
              >
                {h.display_name}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <Input
          label="Latitude"
          type="number"
          step="any"
          value={lat != null ? String(lat) : ''}
          onChange={(e) =>
            onChange({
              ...value,
              latitude: e.target.value === '' ? null : Number(e.target.value),
            })
          }
        />
        <Input
          label="Longitude"
          type="number"
          step="any"
          value={lon != null ? String(lon) : ''}
          onChange={(e) =>
            onChange({
              ...value,
              longitude: e.target.value === '' ? null : Number(e.target.value),
            })
          }
        />
        {mostrarRaio ? (
          <Input
            label={raioLabel}
            type="number"
            min={20}
            max={50000}
            value={String(value.raio_metros ?? 200)}
            onChange={(e) =>
              onChange({
                ...value,
                raio_metros: Number(e.target.value) || 200,
              })
            }
          />
        ) : null}
      </div>
      {temPin ? (
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
          <iframe
            title="Mapa do local"
            className="h-56 w-full border-0"
            loading="lazy"
            src={embedUrl(lat!, lon!)}
          />
          <div className="border-t border-slate-200 px-3 py-2 text-right text-sm dark:border-slate-700">
            <a
              className="text-cyan-700 underline dark:text-cyan-300"
              href={linkMapaOsm(lat!, lon!)}
              target="_blank"
              rel="noreferrer"
            >
              Abrir no OpenStreetMap
            </a>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Busque um endereço ou informe latitude e longitude para marcar o pin.
        </p>
      )}
    </div>
  )
}
