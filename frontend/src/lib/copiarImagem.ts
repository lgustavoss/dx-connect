/** Copia uma imagem (object URL ou URL comum) para a área de transferência como PNG. */
export async function copiarImagemParaAreaDeTransferencia(src: string): Promise<void> {
  if (typeof ClipboardItem === 'undefined' || !navigator.clipboard?.write) {
    throw new Error('Copiar imagem não é suportado neste navegador.')
  }
  const blob = await (await fetch(src)).blob()
  const png = blob.type === 'image/png' ? blob : await converterParaPng(blob)
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': png })])
}

async function converterParaPng(blob: Blob): Promise<Blob> {
  const bitmap = await createImageBitmap(blob)
  const canvas = document.createElement('canvas')
  canvas.width = bitmap.width
  canvas.height = bitmap.height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Não foi possível preparar a imagem.')
  ctx.drawImage(bitmap, 0, 0)
  bitmap.close()
  return new Promise((resolve, reject) => {
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Não foi possível preparar a imagem.'))), 'image/png')
  })
}
