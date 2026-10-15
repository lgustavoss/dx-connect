/**
 * Um canal por vez no alerta da fila.
 * O Web Audio assume o loop e o HTML para; o HTML só entra se o Web Audio não assumiu.
 */

/**
 * @param {{ htmlExiste: boolean }} estado
 * O elemento pode já estar tocando ou com play() ainda pendente.
 */
export function aoIniciarWebAudio(estado) {
  return { silenciarHtml: estado.htmlExiste }
}

/**
 * @param {{
 *   webOk: boolean,
 *   webTocando: boolean,
 *   webComecando: boolean,
 *   wanted: boolean,
 *   muted: boolean,
 * }} estado
 */
export function podeIniciarHtml(estado) {
  if (!estado.wanted || estado.muted) return false
  if (estado.webOk || estado.webTocando || estado.webComecando) return false
  return true
}

/** O play() do HTML pode resolver depois do Web Audio já ter começado. */
export function htmlDevePararPorqueWebAssumiu(webTocando) {
  return webTocando
}
