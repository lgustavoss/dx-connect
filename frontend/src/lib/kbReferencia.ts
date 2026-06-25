/** Texto para citar um manual na mensagem ao cliente ou ao colega de equipe. */
export function textoReferenciaKb(artigo: {
  titulo: string
  slug: string
  interno_only?: boolean
}): string {
  if (artigo.interno_only) {
    return `Consulte o manual «${artigo.titulo}» no menu Ajuda (disponível apenas para a equipe).`
  }
  return `Consulte o manual «${artigo.titulo}» na central de ajuda.`
}
