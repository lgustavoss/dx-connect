/**
 * Migra classes Tailwind slate (dark) para tokens navy dr-*.
 * Uso: node scripts/migrate-dark-theme.mjs
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'src')

const replacements = [
  ['dark:focus:ring-offset-slate-950', 'dark:focus:ring-offset-dr-deep'],
  ['dark:from-slate-950', 'dark:from-dr-deep'],
  ['dark:to-slate-900', 'dark:to-dr-panel'],
  ['dark:bg-slate-950/', 'dark:bg-dr-deep/'],
  ['dark:bg-slate-950', 'dark:bg-dr-deep'],
  ['dark:bg-slate-900/', 'dark:bg-dr-surface/'],
  ['dark:bg-slate-900', 'dark:bg-dr-surface'],
  ['dark:bg-slate-800/', 'dark:bg-dr-surface-elevated/'],
  ['dark:bg-slate-800', 'dark:bg-dr-surface-elevated'],
  ['dark:border-slate-800/', 'dark:border-dr-border/'],
  ['dark:border-slate-800', 'dark:border-dr-border'],
  ['dark:border-slate-700/', 'dark:border-dr-border/'],
  ['dark:border-slate-700', 'dark:border-dr-border'],
  ['dark:hover:bg-slate-800/', 'dark:hover:bg-white/'],
  ['dark:hover:bg-slate-800', 'dark:hover:bg-white/8'],
  ['dark:active:bg-slate-800', 'dark:active:bg-white/12'],
  ['dark:hover:bg-slate-700', 'dark:hover:bg-white/10'],
  ['dark:active:bg-slate-700', 'dark:active:bg-white/12'],
]

function walk(dir) {
  let count = 0
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name)
    if (ent.isDirectory() && ent.name !== 'node_modules') count += walk(p)
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
console.log(`migrate-dark-theme: ${n} arquivo(s) atualizado(s)`)
