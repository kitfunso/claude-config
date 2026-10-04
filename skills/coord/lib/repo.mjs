import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'

const PROTECTED = new Set(['master', 'main', 'HEAD'])
const RELEASE_BRANCH = /^(release\/|chore\/release-)/

// Undefined when the tool exits non-zero (not a repo, no such PR); a missing binary or a hang still throws.
export function run(cmd, args, cwd) {
  try {
    const out = execFileSync(cmd, args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 15000, windowsHide: true })
    return out.trim() || undefined
  } catch (err) {
    if (typeof err.status === 'number') return undefined
    throw err
  }
}

// owner/name from the origin URL, so every worktree and clone of one GitHub repo shares a board.
export function repoOf(cwd, hint) {
  if (hint === undefined && cwd !== undefined && !existsSync(cwd)) return undefined
  const url = hint ?? run('git', ['remote', 'get-url', 'origin'], cwd)
  const m = url?.replace(/\.git$/, '').replace(/\/+$/, '').match(/([^/:]+)[/:]([^/:]+)$/)
  if (m) return `${m[1]}/${m[2]}`.toLowerCase()
  const common = run('git', ['rev-parse', '--path-format=absolute', '--git-common-dir'], cwd)
  return common?.replace(/[\\/]\.git$/, '').toLowerCase()
}

function branchOf(action, cwd) {
  if (action.branch !== undefined) return action.branch
  if (action.current) return run('git', ['rev-parse', '--abbrev-ref', 'HEAD'], cwd)
  const repoFlag = action.repo === undefined ? [] : ['-R', action.repo]
  return run('gh', ['pr', 'view', action.pr, ...repoFlag, '--json', 'headRefName', '-q', '.headRefName'], cwd)
}

export function keysFor(action, cwd) {
  if (action.release) return ['release']
  const branch = branchOf(action, cwd)
  if (branch === undefined || PROTECTED.has(branch)) return []
  return RELEASE_BRANCH.test(branch) ? [`branch:${branch}`, 'release'] : [`branch:${branch}`]
}
