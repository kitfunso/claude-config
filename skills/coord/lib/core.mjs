import { actions } from './parse.mjs'
import { keysFor, repoOf } from './repo.mjs'
import { claim, isLive, lastActive, owner, sessionInfo } from './store.mjs'

export const CLI = 'node ~/.claude/skills/coord/bin/coord.mjs'
// A release claim lapses on its own, so a long session that shipped once does not block the next release.
const RELEASE_HOLD_MS = 2 * 3600_000
export const HOW =
  `Parallel sessions share this board. Before starting a named work item (roadmap item, PR, release), run \`${CLI} claim <item> --note "<what>"\`; ` +
  'exit 2 means another live session owns it: coordinate through ListAgents and SendMessage, or take other work. ' +
  'Branch creation, pushes, tags, releases and PR merges are claimed and checked automatically; claims drop when the session ends.'

export const quoted = key => (/^[\w:./@-]+$/.test(key) ? key : `'${key.replace(/'/g, "'\\''")}'`)

function ago(ms) {
  const min = Math.max(0, Math.round(ms / 60000))
  return min < 90 ? `${min} min` : `${(min / 60).toFixed(1)} h`
}

function describe(c, sid, now = Date.now()) {
  const who = c.session === sid ? 'this session' : `session ${c.session.slice(0, 8)}`
  const where = sessionInfo(c.session)?.cwd ?? c.cwd
  const idle = ago(now - lastActive(c))
  const state = isLive(c, now) ? `active ${idle} ago` : `stale (${idle} idle), free to take`
  const what = c.note ?? c.cmd
  return `${c.key}: ${who}${where ? ` in ${where}` : ''}, ${state}${what ? `; ${what}` : ''}`
}

export const heldBy = c =>
  `coord: ${c.key} in ${c.repo} is held by another live session. ${describe(c)}.\n` +
  'Coordinate before acting: find that session with ListAgents and SendMessage it, or take other work. ' +
  `If its work is finished or abandoned, free it with \`${CLI} release ${quoted(c.key)} --repo ${c.repo} --force\` and retry.`

export function board(claims, sid, repo) {
  if (claims.length === 0) return `coord: no claims${repo ? ` in ${repo}` : ''}.`
  const head = `coord board${repo ? ` for ${repo}` : ''} (${claims.length} claim${claims.length === 1 ? '' : 's'}):`
  return [head, ...claims.map(c => `- ${repo ? '' : `${c.repo} `}${describe(c, sid)}`)].join('\n')
}

function plan(command, cwd) {
  const steps = []
  for (const a of actions(command, process.env.HOME ?? process.env.USERPROFILE)) {
    const dir = a.cwd ?? cwd
    const repo = repoOf(dir, a.repo)
    if (repo !== undefined) for (const key of keysFor(a, dir)) steps.push({ repo, key, mode: a.mode, cwd: dir })
  }
  return steps
}

// allow:false carries the refusal; allow:true carries the claims this call just took, if any.
export function guard(command, sid, cwd) {
  const steps = plan(command, cwd)
  const now = Date.now()
  const blocked = steps.map(s => owner(s.repo, s.key)).filter(o => o && o.session !== sid && isLive(o, now))
  if (blocked.length > 0) return { allow: false, text: blocked.map(heldBy).join('\n') }
  const taken = []
  for (const s of steps.filter(s => s.mode === 'claim')) {
    const until = s.key === 'release' ? now + RELEASE_HOLD_MS : undefined
    const r = claim(s.repo, s.key, sid, { cwd: s.cwd, cmd: command.slice(0, 80), until }, { now })
    if (!r.ok) return { allow: false, text: heldBy(r.claim) }
    if (r.fresh) taken.push(`${s.key} in ${s.repo}`)
  }
  const text = taken.length > 0 ? `coord: this session now holds ${taken.join(', ')}; other sessions are refused it until this one ends or idles 3 h.` : ''
  return { allow: true, text }
}
