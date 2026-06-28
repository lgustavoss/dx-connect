/**
 * Gera mark PNG (alpha), tamanhos de favicon e favicon.ico a partir da logo v2.
 * Fonte: deskrudder-logo-ref-v2-black.png (brand sheet, fundo preto).
 */
import sharp from 'sharp'
import path from 'path'
import { fileURLToPath } from 'url'
import { writeFileSync, unlinkSync } from 'fs'
import toIco from 'to-ico'

const root = path.dirname(fileURLToPath(import.meta.url))
const pub = path.join(root, '..', 'public')
const sourcePath = path.join(pub, 'deskrudder-logo-ref-v2-black.png')
const outAlpha = path.join(pub, 'deskrudder-mark-alpha.png')
const outMark = path.join(pub, 'deskrudder-mark.png')
const outFavicon = path.join(pub, 'favicon.ico')
const TARGET = 512
const sizes = [16, 24, 32, 48, 128, 256]

/** Icone D grande no topo do brand sheet (sem wordmark). */
const ICON_CROP = { left: 176, top: 96, width: 324, height: 288 }
const FLOOD_TOL = 48

function distToDark(r, g, b) {
  return Math.max(r, g, b)
}

async function extractMarkIcon() {
  const { data, info } = await sharp(sourcePath)
    .extract(ICON_CROP)
    .extend({ top: 16, bottom: 24, left: 16, right: 16, background: '#000000' })
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true })

  return { data, width: info.width, height: info.height, channels: info.channels }
}

function floodFillBg(data, w, h, ch) {
  const n = w * h
  const bg = new Uint8Array(n)
  const q = []
  const push = (x, y) => {
    if (x < 0 || y < 0 || x >= w || y >= h) return
    const i = y * w + x
    if (bg[i]) return
    const p = i * ch
    if (distToDark(data[p], data[p + 1], data[p + 2]) <= FLOOD_TOL) {
      bg[i] = 1
      q.push(i)
    }
  }
  for (let x = 0; x < w; x++) {
    push(x, 0)
    push(x, h - 1)
  }
  for (let y = 0; y < h; y++) {
    push(0, y)
    push(w - 1, y)
  }
  while (q.length) {
    const i = q.pop()
    push((i % w) - 1, (i / w) | 0)
    push((i % w) + 1, (i / w) | 0)
    push(i % w, ((i / w) | 0) - 1)
    push(i % w, ((i / w) | 0) + 1)
  }
  return bg
}

function hardMatte(data, w, h, ch, bgMask) {
  const n = w * h
  const out = Buffer.alloc(n * 4)
  for (let i = 0; i < n; i++) {
    const p = i * ch
    const o = i * 4
    if (bgMask[i]) {
      out[o + 3] = 0
      continue
    }
    out[o] = data[p]
    out[o + 1] = data[p + 1]
    out[o + 2] = data[p + 2]
    out[o + 3] = 255
  }
  return out
}

async function upscale(rgba, w, h, target) {
  const scale = target / Math.max(w, h)
  const nw = Math.round(w * scale)
  const nh = Math.round(h * scale)
  const { data, info } = await sharp(rgba, { raw: { width: w, height: h, channels: 4 } })
    .resize(nw, nh, { kernel: sharp.kernel.lanczos3 })
    .raw()
    .toBuffer({ resolveWithObject: true })
  return { rgba: data, width: info.width, height: info.height }
}

async function savePng(rgba, w, h, dest) {
  await sharp(rgba, { raw: { width: w, height: h, channels: 4 } })
    .png({ compressionLevel: 9, adaptiveFiltering: true })
    .toFile(dest)
}

async function buildSquareMaster(input) {
  const trimmed = await sharp(input).trim().toBuffer({ resolveWithObject: true })
  const cw = trimmed.info.width
  const ch = trimmed.info.height
  const padX = Math.round(cw * 0.1)
  const padTop = Math.round(ch * 0.08)
  const padBottom = Math.round(ch * 0.14)
  const innerW = cw + padX * 2
  const innerH = ch + padTop + padBottom
  const side = Math.max(innerW, innerH)
  const left = Math.floor((side - cw) / 2)
  const right = side - cw - left
  const top = padTop + Math.floor((side - innerH) / 2)
  const bottom = side - ch - top

  return sharp(trimmed.data)
    .extend({
      top,
      bottom,
      left,
      right,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    })
    .png()
    .toBuffer()
}

async function buildUiMark(input) {
  const trimmed = await sharp(input).trim().toBuffer({ resolveWithObject: true })
  const cw = trimmed.info.width
  const ch = trimmed.info.height
  return sharp(trimmed.data)
    .extend({
      top: Math.round(ch * 0.05),
      bottom: Math.round(ch * 0.1),
      left: Math.round(cw * 0.05),
      right: Math.round(cw * 0.05),
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    })
    .png()
    .toBuffer()
}

async function saveSizes(squareMasterPath) {
  const pngBuffers = {}
  for (const size of sizes) {
    const bottomExtra = Math.max(2, Math.round(size * 0.06))
    const maxH = size - bottomExtra

    const scaled = await sharp(squareMasterPath)
      .resize(size, maxH, {
        fit: 'inside',
        background: { r: 0, g: 0, b: 0, alpha: 0 },
        kernel: sharp.kernel.lanczos3,
      })
      .png()
      .toBuffer({ resolveWithObject: true })

    const left = Math.floor((size - scaled.info.width) / 2)
    const top = Math.floor((size - bottomExtra - scaled.info.height) / 2)

    const outPath = path.join(pub, `deskrudder-mark-${size}.png`)
    await sharp({
      create: {
        width: size,
        height: size,
        channels: 4,
        background: { r: 0, g: 0, b: 0, alpha: 0 },
      },
    })
      .composite([{ input: scaled.data, left, top }])
      .png({ compressionLevel: 9 })
      .toFile(outPath)

    pngBuffers[size] = await sharp(outPath).png().toBuffer()
    console.log(`  deskrudder-mark-${size}.png`)
  }
  return pngBuffers
}

async function writeFavicon(pngBuffers) {
  const ico = await toIco([pngBuffers[16], pngBuffers[32], pngBuffers[48]])
  writeFileSync(outFavicon, ico)
  console.log(`  ${path.basename(outFavicon)}`)
}

async function main() {
  console.log('Recorte brand sheet v2 + matte fundo escuro...')
  let { data, width, height, channels } = await extractMarkIcon()
  console.log(`  ${width}x${height}`)

  const bg = floodFillBg(data, width, height, channels)
  let rgba = hardMatte(data, width, height, channels, bg)

  console.log(`Upscale ${TARGET}px...`)
  ;({ rgba, width, height } = await upscale(rgba, width, height, TARGET))

  const tmpMatte = path.join(pub, '_mark-matte-tmp.png')
  await savePng(rgba, width, height, tmpMatte)

  console.log('PNG UI + favicons...')
  const uiBuf = await buildUiMark(tmpMatte)
  await sharp(uiBuf).toFile(outAlpha)
  const uiMeta = await sharp(outAlpha).metadata()
  console.log(`  ${path.basename(outAlpha)} (${uiMeta.width}x${uiMeta.height})`)

  const squareBuf = await buildSquareMaster(tmpMatte)
  const squarePath = path.join(pub, '_mark-square-tmp.png')
  await sharp(squareBuf).toFile(squarePath)

  await sharp(outAlpha).png().toFile(outMark)
  console.log(`  ${path.basename(outMark)}`)

  console.log('Tamanhos:')
  const pngBuffers = await saveSizes(squarePath)

  console.log('Favicon:')
  await writeFavicon(pngBuffers)

  for (const f of [tmpMatte, squarePath]) {
    try {
      unlinkSync(f)
    } catch {
      /* ignore */
    }
  }
  console.log('OK')
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
