#!/usr/bin/env node
/**
 * Gera .dsh/skills a partir de .cursor/ (fonte única).
 *
 * - .cursor/commands/*.md      -> .dsh/skills/<nome>.md          (skill = /nome no chat do DSH)
 * - .cursor/skills/<nome>/SKILL.md -> .dsh/skills/<nome>/SKILL.md
 *
 * Rode depois de mexer nos arquivos do Cursor:  node .dsh/sync-skills.mjs
 * O watcher do DSH recarrega o catálogo sozinho; não precisa reiniciar.
 */
import { readFile, readdir, writeFile, mkdir, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const raiz = path.dirname(here)
const commandsDir = path.join(raiz, '.cursor', 'commands')
const skillsDir = path.join(raiz, '.cursor', 'skills')
const outDir = path.join(raiz, '.dsh', 'skills')

// Fluxos com merge/PR/release: só o humano dispara (/nome), o modelo não escolhe sozinho.
const HUMANO_APENAS = new Set(['criar-pr', 'release-staging'])

/** Primeiro parágrafo do corpo (depois de títulos/comentários) vira a `description` do catálogo. */
function descricaoDoCorpo(texto) {
  const linhas = texto.split(/\r?\n/)
  let i = linhas.findIndex((linha) => {
    const t = linha.trim()
    return t !== '' && !t.startsWith('#') && !t.startsWith('<!--')
  })
  if (i === -1) return ''
  const paragrafo = []
  for (; i < linhas.length; i += 1) {
    const t = linhas[i].trim()
    if (t === '' || t.startsWith('<!--')) break
    paragrafo.push(t)
  }
  return paragrafo.join(' ').replace(/[*`]/g, '').replace(/\s+/g, ' ').trim().slice(0, 300)
}

async function principal() {
  await mkdir(outDir, { recursive: true })

  const comandos = (await readdir(commandsDir)).filter((f) => f.endsWith('.md')).sort()
  const nomesComandos = new Set()

  for (const arquivo of comandos) {
    const nome = path.basename(arquivo, '.md')
    const corpo = (await readFile(path.join(commandsDir, arquivo), 'utf8')).replace(/^\uFEFF/, '').trim()
    const descricao = descricaoDoCorpo(corpo)
    if (!descricao) {
      console.warn(`AVISO: ${arquivo} sem parágrafo de descrição — pulando`)
      continue
    }
    const front = ['---', `name: ${nome}`, `description: ${JSON.stringify(descricao)}`]
    if (HUMANO_APENAS.has(nome)) front.push('disable-model-invocation: true')
    front.push(
      '---',
      `<!-- Gerado de .cursor/commands/${arquivo} por .dsh/sync-skills.mjs. NÃO editar à mão. -->`,
      '',
    )
    await writeFile(path.join(outDir, `${nome}.md`), `${front.join('\n')}\n${corpo}\n`, 'utf8')
    nomesComandos.add(`${nome}.md`)
  }

  const skills = (await readdir(skillsDir, { withFileTypes: true })).filter((e) => e.isDirectory())
  const nomesSkills = new Set()

  for (const dir of skills) {
    const origem = path.join(skillsDir, dir.name, 'SKILL.md')
    let texto
    try {
      texto = await readFile(origem, 'utf8')
    } catch {
      continue // diretório sem SKILL.md
    }
    const destinoDir = path.join(outDir, dir.name)
    await mkdir(destinoDir, { recursive: true })
    await writeFile(path.join(destinoDir, 'SKILL.md'), texto.replace(/^\uFEFF/, ''), 'utf8')
    nomesSkills.add(dir.name)
  }

  // Limpa o que não existe mais na fonte.
  for (const entrada of await readdir(outDir, { withFileTypes: true })) {
    if (entrada.isFile() && entrada.name.endsWith('.md') && !nomesComandos.has(entrada.name)) {
      await rm(path.join(outDir, entrada.name))
    }
    if (entrada.isDirectory() && !nomesSkills.has(entrada.name)) {
      await rm(path.join(outDir, entrada.name), { recursive: true, force: true })
    }
  }

  console.log(`OK: ${nomesComandos.size} comandos -> .dsh/skills/*.md`)
  console.log(`OK: ${nomesSkills.size} skills   -> .dsh/skills/*/SKILL.md`)
  const humano = [...HUMANO_APENAS].filter((n) => nomesComandos.has(`${n}.md`))
  console.log(`Só humano (disable-model-invocation): ${humano.join(', ') || '(nenhum)'}`)
}

await principal()
