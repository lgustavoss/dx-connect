/**
 * Reverte tokens navy dr-* para o esquema slate original do app.
 * Uso: node scripts/revert-dark-theme.mjs
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'src')

const replacements = [
  ['dark:focus:ring-offset-dr-deep', 'dark:focus:ring-offset-slate-950'],
  ['dark:from-dr-deep', 'dark:from-slate-950'],
  ['dark:to-dr-panel', 'dark:to-slate-900/95'],
  ['dark:bg-dr-deep/', 'dark:bg-slate-950/'],
  ['dark:bg-dr-deep', 'dark:bg-slate-950'],
  ['dark:bg-dr-surface-elevated/', 'dark:bg-slate-800/'],
  ['dark:bg-dr-surface-elevated', 'dark:bg-slate-800'],
  ['dark:bg-dr-surface/', 'dark:bg-slate-900/'],
  ['dark:bg-dr-surface', 'dark:bg-slate-900'],
  ['dark:bg-dr-navy/', 'dark:bg-slate-950/'],
  ['dark:bg-dr-navy', 'dark:bg-slate-950'],
  ['dark:border-dr-navy-mid/', 'dark:border-slate-800/'],
  ['dark:border-dr-navy-mid', 'dark:border-slate-800'],
  ['dark:border-dr-border/', 'dark:border-slate-800/'],
  ['dark:border-dr-border', 'dark:border-slate-800'],
  ['dark:hover:bg-white/12', 'dark:active:bg-slate-700'],
  ['dark:hover:bg-white/10', 'dark:hover:bg-slate-700'],
  ['dark:hover:bg-white/8', 'dark:hover:bg-slate-800'],
  ['dark:active:bg-white/12', 'dark:active:bg-slate-800'],
  ['dark:hover:bg-white/6', 'dark:hover:bg-slate-800/80'],
  ['focus-visible:ring-offset-dr-deep', 'focus-visible:ring-offset-slate-950'],
  ['focus:ring-offset-dr-deep', 'focus:ring-offset-slate-950'],
  ['bg-dr-deep', 'bg-[#050810]'],
]

function walk(dir) {
  let count = 0
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name)
    if (ent.isDirectory() && ent.name !== 'node_modules' && ent.name !== 'brand') count += walk(p)
    else if (/\.(tsx|ts|css)$/.test(ent.name)) {
      let s = fs.readFileSync(p, 'utf8')
      const orig = s
      for (const [from, to] of replacements) s = s.split(from).join(to)
      if (s !== orig) {
        fs.writeFileSync(p, s)
        count++
      }
    }
  }
  return count
}

const n = walk(root)
console.log(`revert-dark-theme: ${n} arquivo(s) atualizado(s)`)
