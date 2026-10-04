#!/usr/bin/env node
// Claims board so parallel Claude Code sessions on one repo see and respect each other's work.
import { parseArgs } from 'node:util'

import { CLI, board, guard, heldBy, quoted } from '../lib/core.mjs'
import { repoOf } from '../lib/repo.mjs'
import { claim, endSession, isLive, list, release, touch } from '../lib/store.mjs'

const USAGE = `usage: coord claim <item> [--note text] [--force] | release <item>|--all [--force] | list [--json] [--all-repos]
options: --session <id> (default $CLAUDE_CODE_SESSION_ID), --cwd <dir>, --repo <owner/name>
internal: touch | end | guard -- <bash command>  (exit 2 = held by another session, 3 = guard denied)
`
const OPTIONS = {
  session: { type: 'string' },
  cwd: { type: 'string' },
  repo: { type: 'string' },
  note: { type: 'string' },
  force: { type: 'boolean' },
  all: { type: 'boolean' },
  json: { type: 'boolean' },
  'all-repos': { type: 'boolean' },
}

class UsageError extends Error {}
const say = text => process.stdout.write(`${text}\n`)

const needSession = ctx => {
  if (!ctx.sid) throw new UsageError('coord: no session id; run inside Claude Code or pass --session')
}

function needRepo(ctx) {
  const repo = repoOf(ctx.cwd, ctx.repo)
  if (repo === undefined) throw new UsageError(`coord: ${ctx.cwd} is not in a git repo; pass --repo owner/name`)
  return repo
}

function claimCmd(ctx, [item]) {
  needSession(ctx)
  if (!item) throw new UsageError(USAGE)
  const repo = needRepo(ctx)
  touch(ctx.sid, ctx.cwd)
  const r = claim(repo, item, ctx.sid, { cwd: ctx.cwd, note: ctx.note }, { force: ctx.force })
  if (!r.ok) return say(heldBy(r.claim)), 2
  say(`coord: this session holds ${item} in ${repo}. Release it with \`${CLI} release ${quoted(item)}\` when done.`)
  return 0
}

function releaseCmd(ctx, [item]) {
  needSession(ctx)
  if (ctx.all) {
    const mine = list().filter(c => c.session === ctx.sid)
    for (const c of mine) release(c.repo, c.key, ctx.sid)
    return say(`coord: released ${mine.length} claim(s).`), 0
  }
  if (!item) throw new UsageError(USAGE)
  const repo = needRepo(ctx)
  const r = release(repo, item, ctx.sid, { force: ctx.force })
  if (!r.ok) return say(`${heldBy(r.claim)}\nAdd --force only if you are sure.`), 2
  say(r.claim === undefined ? `coord: nobody held ${item} in ${repo}.` : `coord: released ${item} in ${repo}.`)
  return 0
}

function listCmd(ctx) {
  const repo = ctx['all-repos'] ? undefined : needRepo(ctx)
  const claims = list(repo)
  say(ctx.json ? JSON.stringify(claims.map(c => ({ ...c, live: isLive(c) })), null, 2) : board(claims, ctx.sid, repo))
  return 0
}

function guardCmd(ctx, _rest, command) {
  if (!ctx.sid || !command) return 0
  const verdict = guard(command, ctx.sid, ctx.cwd)
  if (verdict.text) say(verdict.text)
  return verdict.allow ? 0 : 3
}

const COMMANDS = {
  claim: claimCmd,
  release: releaseCmd,
  list: listCmd,
  touch: ctx => (ctx.sid && touch(ctx.sid, ctx.cwd), 0),
  end: ctx => (ctx.sid && endSession(ctx.sid), 0),
  guard: guardCmd,
}

function main(argv) {
  const dash = argv.indexOf('--')
  const parsed = parseArgs({ args: dash === -1 ? argv : argv.slice(0, dash), options: OPTIONS, allowPositionals: true })
  const [cmd, ...rest] = parsed.positionals
  const ctx = { ...parsed.values, sid: parsed.values.session ?? process.env.CLAUDE_CODE_SESSION_ID, cwd: parsed.values.cwd ?? process.cwd() }
  const handler = COMMANDS[cmd]
  if (handler === undefined) throw new UsageError(USAGE)
  return handler(ctx, rest, dash === -1 ? '' : argv.slice(dash + 1).join(' '))
}

try {
  process.exitCode = main(process.argv.slice(2))
} catch (err) {
  if (!(err instanceof UsageError) && !String(err.code).startsWith('ERR_PARSE_ARGS')) throw err
  process.stderr.write(`${err.message}\n`)
  process.exitCode = 1
}
