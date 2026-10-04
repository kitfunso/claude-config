import assert from 'node:assert/strict'
import { execFileSync, spawn, spawnSync } from 'node:child_process'
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { actions } from '../lib/parse.mjs'

const CLI = join(dirname(fileURLToPath(import.meta.url)), '..', 'bin', 'coord.mjs')
const home = mkdtempSync(join(tmpdir(), 'coord-home-'))
// Forward slashes, as Git Bash commands spell paths; an unquoted backslash is an escape there.
const repo = mkdtempSync(join(tmpdir(), 'coord-repo-')).replace(/\\/g, '/')
execFileSync('git', ['init', '-q', '-b', 'master', repo])
execFileSync('git', ['-C', repo, 'remote', 'add', 'origin', 'https://github.com/Kitfunso/Hippo.git'])

function coord(sid, ...args) {
  const r = spawnSync(process.execPath, [CLI, ...args], {
    cwd: repo,
    encoding: 'utf8',
    env: { ...process.env, COORD_HOME: home, CLAUDE_CODE_SESSION_ID: sid },
  })
  return { code: r.status, out: r.stdout + r.stderr }
}
const guard = (sid, command) => coord(sid, 'guard', '--cwd', repo, '--', command)

test('a live claim refuses another session and names the owner', () => {
  assert.equal(coord('sess-aaaa1111', 'claim', 'Z0', '--note', 'token eval').code, 0)
  const other = coord('sess-bbbb2222', 'claim', 'Z0')
  assert.equal(other.code, 2)
  assert.match(other.out, /held by another live session.*sess-aaa.*token eval/s)
  assert.equal(coord('sess-aaaa1111', 'claim', 'Z0').code, 0)
  assert.match(coord('sess-bbbb2222', 'list').out, /kitfunso\/hippo.*Z0: session sess-aaa/s)
})

test('release needs the owner or --force', () => {
  assert.equal(coord('sess-bbbb2222', 'release', 'Z0').code, 2)
  assert.equal(coord('sess-bbbb2222', 'release', 'Z0', '--force').code, 0)
  assert.equal(coord('sess-bbbb2222', 'claim', 'Z0').code, 0)
})

test('guard claims a new branch and refuses another session pushing it', () => {
  const made = guard('sess-aaaa1111', `git -C ${repo} checkout -b feat/x`)
  assert.equal(made.code, 0)
  assert.match(made.out, /holds branch:feat\/x in kitfunso\/hippo/)
  const push = guard('sess-cccc3333', `cd ${repo} && git push -u origin feat/x`)
  assert.equal(push.code, 3)
  assert.match(push.out, /branch:feat\/x/)
  assert.equal(guard('sess-cccc3333', 'git push origin master').code, 0)
  assert.equal(guard('sess-aaaa1111', 'git push origin feat/x').code, 0)
})

test('one release at a time across tag, npm and release branches', () => {
  assert.equal(guard('sess-aaaa1111', 'git tag -a v1.62.0 -m "release"').code, 0)
  assert.equal(guard('sess-cccc3333', 'npm publish').code, 3)
  assert.equal(guard('sess-cccc3333', 'git checkout -b chore/release-1.63.0').code, 3)
  assert.equal(guard('sess-cccc3333', 'npm publish --dry-run').code, 0)
})

test('a silent session goes stale and its claim can be taken', () => {
  const file = join(home, 'claims', 'kitfunso_hippo', 'stale-item.json')
  assert.equal(coord('sess-dddd4444', 'claim', 'stale-item').code, 0)
  const old = Date.now() - 4 * 3600_000
  writeFileSync(file, JSON.stringify({ ...JSON.parse(readFileSync(file, 'utf8')), at: old }))
  writeFileSync(join(home, 'sessions', 'sess-dddd4444.json'), JSON.stringify({ sid: 'sess-dddd4444', seen: old }))
  assert.match(coord('sess-eeee5555', 'list').out, /stale-item.*stale/)
  assert.equal(coord('sess-eeee5555', 'claim', 'stale-item').code, 0)
})

test('end drops every claim of the session', () => {
  assert.equal(coord('sess-aaaa1111', 'end').code, 0)
  assert.equal(coord('sess-cccc3333', 'claim', 'Z0').code, 2)
  assert.equal(guard('sess-cccc3333', 'git push origin feat/x').code, 0)
  assert.doesNotMatch(coord('sess-cccc3333', 'list').out, /sess-aaa/)
})

test('eight sessions racing for one item: exactly one wins', async () => {
  const race = Array.from({ length: 8 }, (_, i) => new Promise(resolve => {
    const child = spawn(process.execPath, [CLI, 'claim', 'raced'], {
      cwd: repo,
      env: { ...process.env, COORD_HOME: home, CLAUDE_CODE_SESSION_ID: `racer-${i}` },
    })
    child.on('exit', resolve)
  }))
  const codes = await Promise.all(race)
  assert.deepEqual(codes.sort(), [0, 2, 2, 2, 2, 2, 2, 2])
})

const HOOK = join(dirname(CLI), 'hook.mjs')
function hook(event, sid, extra = {}) {
  const input = JSON.stringify({ hook_event_name: event, session_id: sid, cwd: repo, ...extra })
  const r = spawnSync(process.execPath, [HOOK], { input, encoding: 'utf8', env: { ...process.env, COORD_HOME: home } })
  assert.equal(r.status, 0, r.stderr)
  return r.stdout === '' ? undefined : JSON.parse(r.stdout).hookSpecificOutput
}
const bashHook = (sid, command) => hook('PreToolUse', sid, { tool_name: 'Bash', tool_input: { command } })

test('classic hooks: board at start, deny on a held branch, claims gone at end', () => {
  assert.match(hook('SessionStart', 'hook-a').additionalContext, /kitfunso\/hippo[\s\S]*coord\.mjs claim <item>/)
  assert.equal(bashHook('hook-a', 'git switch -c feat/hooked'), undefined)
  const denied = bashHook('hook-b', 'git push origin feat/hooked')
  assert.equal(denied.permissionDecision, 'deny')
  assert.match(denied.permissionDecisionReason, /branch:feat\/hooked.*session hook-a/s)
  assert.equal(bashHook('hook-b', 'ls && npm test'), undefined)
  assert.equal(hook('PreToolUse', 'hook-b', { tool_name: 'Read', tool_input: { file_path: 'x' } }), undefined)
  assert.equal(hook('SessionEnd', 'hook-a'), undefined)
  assert.equal(bashHook('hook-b', 'git push origin feat/hooked'), undefined)
})

test('parser reads cwd, flags and what each command takes', () => {
  const pick = cmd => actions(cmd, 'C:/Users/me').map(({ cwd, repo: r, ...a }) => ({ ...a, cwd, ...(r ? { repo: r } : {}) }))
  assert.deepEqual(pick('cd /c/w && git -C sub push -u origin +HEAD:refs/heads/feat/y'), [{ mode: 'claim', branch: 'feat/y', cwd: 'c:/w/sub' }])
  assert.deepEqual(pick('gh pr merge 471 --squash -R kitfunso/hippo'), [{ mode: 'check', pr: '471', cwd: undefined, repo: 'kitfunso/hippo' }])
  assert.deepEqual(pick('git push --delete origin old'), [{ mode: 'check', branch: 'old', cwd: undefined }])
  assert.deepEqual(pick('npm --prefix ~/hippo version patch'), [{ mode: 'claim', release: true, cwd: 'C:/Users/me/hippo' }])
  assert.deepEqual(pick('git branch -D x; git tag -l; echo "git push"'), [])
  assert.deepEqual(pick('git push'), [{ mode: 'claim', current: true, cwd: undefined }])
})
