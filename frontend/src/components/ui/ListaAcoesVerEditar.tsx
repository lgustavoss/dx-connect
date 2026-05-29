import { Button } from './Button'
import { IconEye } from './IconEye'
import { IconPencil } from './IconPencil'
import { IconTrash } from './IconTrash'

type Props = {
  onVer: () => void
  onEditar: () => void
  onExcluir?: () => void
  verLabel?: string
  editarLabel?: string
}

export function ListaAcoesVerEditar({
  onVer,
  onEditar,
  onExcluir,
  verLabel = 'Visualizar',
  editarLabel = 'Editar',
}: Props) {
  return (
    <div className="inline-flex gap-0.5">
      <Button variant="ghost" onClick={onVer} aria-label={verLabel}>
        <IconEye ariaHidden={false} />
      </Button>
      <Button variant="ghost" onClick={onEditar} aria-label={editarLabel}>
        <IconPencil ariaHidden={false} />
      </Button>
      {onExcluir ? (
        <Button variant="ghost" onClick={onExcluir} aria-label="Excluir">
          <IconTrash ariaHidden={false} />
        </Button>
      ) : null}
    </div>
  )
}
