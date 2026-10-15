export function aoIniciarWebAudio(estado: { htmlExiste: boolean }): { silenciarHtml: boolean }

export function podeIniciarHtml(estado: {
  webOk: boolean
  webTocando: boolean
  webComecando: boolean
  wanted: boolean
  muted: boolean
}): boolean

export function htmlDevePararPorqueWebAssumiu(webTocando: boolean): boolean
