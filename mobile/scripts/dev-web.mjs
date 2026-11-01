import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
const isWin = process.platform === 'win32'

const proxy = spawn(process.execPath, [path.join(root, 'scripts', 'api-proxy.mjs')], {
  stdio: 'inherit',
  cwd: root,
})

const expo = spawn(isWin ? 'npx.cmd' : 'npx', ['expo', 'start', '--web', '--port', '8082'], {
  stdio: 'inherit',
  cwd: root,
  shell: isWin,
})

function shutdown() {
  proxy.kill()
  expo.kill()
}

process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
expo.on('exit', (code) => {
  proxy.kill()
  process.exit(code ?? 0)
})
