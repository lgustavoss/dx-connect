import {
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from 'react'

const SCALE_MIN = 0.5
const SCALE_MAX = 5
const SCALE_STEP = 0.25

type Props = {
  src: string
  alt?: string
}

function clampScale(n: number) {
  return Math.min(SCALE_MAX, Math.max(SCALE_MIN, n))
}

/** Visualização de imagem no lightbox: zoom, rotação e arrastar. */
export function ImageLightboxViewer({ src, alt = '' }: Props) {
  const [scale, setScale] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<{ pointerId: number; startX: number; startY: number; originX: number; originY: number } | null>(
    null,
  )
  const scaleRef = useRef(scale)
  scaleRef.current = scale

  useEffect(() => {
    setScale(1)
    setRotation(0)
    setOffset({ x: 0, y: 0 })
    setDragging(false)
    dragRef.current = null
  }, [src])

  useEffect(() => {
    const el = rootRef.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      e.stopPropagation()
      const delta = e.deltaY < 0 ? SCALE_STEP : -SCALE_STEP
      setScale((s) => clampScale(Number((s + delta).toFixed(2))))
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [])

  function zoomBy(delta: number) {
    setScale((s) => clampScale(Number((s + delta).toFixed(2))))
  }

  function resetView() {
    setScale(1)
    setRotation(0)
    setOffset({ x: 0, y: 0 })
  }

  function onPointerDown(e: ReactPointerEvent<HTMLImageElement>) {
    if (e.button !== 0) return
    e.preventDefault()
    e.stopPropagation()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragRef.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      originX: offset.x,
      originY: offset.y,
    }
    setDragging(true)
  }

  function onPointerMove(e: ReactPointerEvent<HTMLImageElement>) {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== e.pointerId) return
    e.preventDefault()
    setOffset({
      x: drag.originX + (e.clientX - drag.startX),
      y: drag.originY + (e.clientY - drag.startY),
    })
  }

  function onPointerUp(e: ReactPointerEvent<HTMLImageElement>) {
    if (dragRef.current?.pointerId === e.pointerId) {
      dragRef.current = null
      setDragging(false)
      try {
        e.currentTarget.releasePointerCapture(e.pointerId)
      } catch {
        /* já libertado */
      }
    }
  }

  const btnClass =
    'flex h-10 w-10 items-center justify-center rounded-full bg-white/15 text-lg font-semibold text-white transition-colors hover:bg-white/25'

  return (
    <div
      ref={rootRef}
      className="relative flex max-h-[85vh] max-w-full flex-col items-center gap-3"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex max-h-[calc(85vh-3.5rem)] max-w-full items-center justify-center overflow-hidden">
        <img
          src={src}
          alt={alt}
          draggable={false}
          className="max-h-[calc(85vh-3.5rem)] max-w-full touch-none select-none object-contain shadow-2xl"
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale}) rotate(${rotation}deg)`,
            cursor: dragging ? 'grabbing' : scale > 1 || offset.x !== 0 || offset.y !== 0 ? 'grab' : 'zoom-in',
            transition: dragging ? undefined : 'transform 120ms ease-out',
          }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onDoubleClick={(e) => {
            e.stopPropagation()
            if (scaleRef.current > 1.01) {
              resetView()
            } else {
              setScale(2)
              setOffset({ x: 0, y: 0 })
            }
          }}
        />
      </div>
      <div
        className="flex flex-wrap items-center justify-center gap-1.5 rounded-full bg-black/50 px-2 py-1.5 backdrop-blur-md"
        role="toolbar"
        aria-label="Controles da imagem"
      >
        <button type="button" className={btnClass} onClick={() => zoomBy(-SCALE_STEP)} aria-label="Diminuir zoom" title="Diminuir zoom">
          −
        </button>
        <button type="button" className={btnClass} onClick={() => zoomBy(SCALE_STEP)} aria-label="Aumentar zoom" title="Aumentar zoom">
          +
        </button>
        <button
          type="button"
          className={btnClass}
          onClick={() => setRotation((r) => r - 90)}
          aria-label="Rodar para a esquerda"
          title="Rodar à esquerda"
        >
          ↺
        </button>
        <button
          type="button"
          className={btnClass}
          onClick={() => setRotation((r) => r + 90)}
          aria-label="Rodar para a direita"
          title="Rodar à direita"
        >
          ↻
        </button>
        <button type="button" className={btnClass} onClick={resetView} aria-label="Repor vista" title="Repor">
          ⟲
        </button>
        <span className="min-w-[3.25rem] px-1 text-center text-xs tabular-nums text-white/80">
          {Math.round(scale * 100)}%
        </span>
      </div>
    </div>
  )
}
