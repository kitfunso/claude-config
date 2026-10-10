// One file per claim, created with link() so two sessions racing for one key cannot both win.
import { linkSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'

// A session silent this long has its claims shown as stale and free to take.
export const TTL_MS = 3 * 3600_000

export const stateHome = () => process.env.COORD_HOME ?? join(homedir(), '.claude', 'coord-state')
const slug = s => s.replace(/[^A-Za-z0-9._-]+/g, '_').slice(0, 120)
const sessionFile = sid => join(stateHome(), 'sessions', `${slug(sid)}.json`)
const claimsRoot = () => join(stateHome(), 'claims')
const claimFile = (repo, key) => join(claimsRoot(), slug(repo), `${slug(key)}.json`)

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  } catch (err) {
    if (err.code === 'ENOENT') return undefined
    throw err
  }
}

function tmpFor(path, value) {
  mkdirSync(dirname(path), { recursive: true })
  const tmp = `${path}.${process.pid}.${Math.random().toString(36).slice(2)}.tmp`
  writeFileSync(tmp, JSON.stringify(value))
  return tmp
}

const writeAtomic = (path, value) => renameSync(tmpFor(path, value), path)

export function touch(sid, cwd, transcript, now = Date.now()) {
  const prev = readJson(sessionFile(sid))
  writeAtomic(sessionFile(sid), { sid, cwd: cwd ?? prev?.cwd, transcript: transcript ?? prev?.transcript, seen: now })
}

function mtime(path) {
  try {
    return statSync(path).mtimeMs
  } catch (err) {
    if (err.code === 'ENOENT') return 0
    throw err
  }
}

export const sessionInfo = sid => readJson(sessionFile(sid))
// Claude Code writes the transcript on every message and tool call, so no per-prompt hook is needed to prove a session alive.
export function lastActive(claim) {
  const s = sessionInfo(claim.session)
  return Math.max(s?.seen ?? 0, s?.transcript ? mtime(s.transcript) : 0, claim.at)
}
export const isLive = (claim, now = Date.now()) =>
  (claim.until === undefined || now < claim.until) && now - lastActive(claim) < TTL_MS

export const owner = (repo, key) => readJson(claimFile(repo, key))

// ok:false carries the live owner's claim; fresh says the session did not hold it before.
export function claim(repo, key, sid, fields = {}, { force = false, now = Date.now() } = {}) {
  const path = claimFile(repo, key)
  const given = Object.entries({ repo, key, session: sid, at: now, ...fields }).filter(([, v]) => v !== undefined)
  const mine = Object.fromEntries(given)
  const tmp = tmpFor(path, mine)
  try {
    linkSync(tmp, path)
    return { ok: true, fresh: true, claim: mine }
  } catch (err) {
    if (err.code !== 'EEXIST') throw err
    const held = readJson(path)
    if (held !== undefined && held.session !== sid && isLive(held, now) && !force) return { ok: false, claim: held }
    // SHORTCUT: two sessions taking the same stale claim at once can both see ok; add a lock file if that ever bites.
    const isMine = held?.session === sid
    const kept = isMine ? { ...held, ...mine } : mine
    writeAtomic(path, kept)
    return { ok: true, fresh: !isMine, claim: kept }
  } finally {
    rmSync(tmp, { force: true })
  }
}

export function release(repo, key, sid, { force = false, now = Date.now() } = {}) {
  const path = claimFile(repo, key)
  const owner = readJson(path)
  if (owner === undefined) return { ok: true, claim: undefined }
  if (owner.session !== sid && isLive(owner, now) && !force) return { ok: false, claim: owner }
  rmSync(path, { force: true })
  return { ok: true, claim: owner }
}

export function list(repo) {
  let repos
  try {
    repos = readdirSync(claimsRoot())
  } catch (err) {
    if (err.code === 'ENOENT') return []
    throw err
  }
  const out = []
  for (const dir of repo === undefined ? repos : repos.filter(d => d === slug(repo))) {
    for (const name of readdirSync(join(claimsRoot(), dir)).filter(n => n.endsWith('.json'))) {
      const c = readJson(join(claimsRoot(), dir, name))
      if (c !== undefined) out.push(c)
    }
  }
  return out.sort((a, b) => a.at - b.at)
}

export function endSession(sid) {
  const mine = list().filter(c => c.session === sid)
  for (const c of mine) rmSync(claimFile(c.repo, c.key), { force: true })
  rmSync(sessionFile(sid), { force: true })
  return mine
}
