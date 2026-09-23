'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { runHook, isDeny } = require('./helpers');
const { scan } = require('../lib/devrl-episode-guard');

const HOOK = path.join(__dirname, '..', 'pre-bash-guard.js');
const DEVRL = path.join(os.homedir(), '.claude', 'dev-framework', 'scripts');
const HAS_DEVRL = fs.existsSync(path.join(DEVRL, 'devrl.py'));

test('a bare feature-repo command is unpinned', () => {
  assert.deepStrictEqual(scan('npm run build').unpinned, ['npm run build']);
});

test('an absolute cd earlier in the same call pins what follows', () => {
  assert.deepStrictEqual(scan('cd /c/Users/skf_s/hippo-wt && npm run build && git status').unpinned, []);
  assert.deepStrictEqual(scan('cd "C:/Users/skf_s/hippo" && git diff').unpinned, []);
  assert.deepStrictEqual(scan('cd ~/.claude/dev-framework && git log -1').unpinned, []);
});

test('git -C, npm --prefix and codex -C with an absolute path pin themselves', () => {
  assert.deepStrictEqual(scan('git -C /c/Users/skf_s/hippo status && npm --prefix C:/Users/skf_s/hippo run build').unpinned, []);
  assert.deepStrictEqual(scan('codex -C /c/Users/skf_s/hippo review --uncommitted').unpinned, []);
});

test('a relative cd, a variable or cd - does not pin', () => {
  assert.strictEqual(scan('cd src && git status').unpinned.length, 1);
  assert.strictEqual(scan('cd "$WT" && npm test').unpinned.length, 1);
  assert.strictEqual(scan('cd /c/x && cd - && git status').unpinned.length, 1);
});

test('a cd inside a subshell does not pin the command after it', () => {
  const cmd = '(cd ~/.claude/dev-framework && python scripts/devrl.py lock-heartbeat X) && npm run build';
  assert.deepStrictEqual(scan(cmd).unpinned, ['npm run build']);
});

test('command substitution takes the pin state of its call', () => {
  assert.strictEqual(scan('python devrl.py step-record X --commit $(git rev-parse HEAD)').unpinned.length, 1);
  assert.strictEqual(scan('cd /c/x && python devrl.py step-record X --commit $(git rev-parse HEAD)').unpinned.length, 0);
});

test('other commands and quoted text are ignored', () => {
  assert.deepStrictEqual(scan('python ~/.claude/dev-framework/scripts/devrl.py lock-heartbeat X').unpinned, []);
  assert.deepStrictEqual(scan('echo "git status; npm test"').unpinned, []);
});

test('git that throws away working-tree changes is flagged', () => {
  for (const cmd of ['git checkout -- src/db.ts', 'git checkout HEAD -- a.ts', 'git checkout .',
    'git checkout -f main', 'git restore src/db.ts', 'git restore --staged --worktree a.ts',
    'git reset --hard', 'git -C /c/x reset --hard HEAD~1', 'git clean -fd', 'git stash',
    'git stash pop', 'git stash drop stash@{0}']) {
    assert.strictEqual(scan(`cd /c/x && ${cmd}`).destructive.length, 1, cmd);
  }
});

test('reads, branch moves and index-only git are not flagged', () => {
  for (const cmd of ['git checkout main', 'git checkout -b feat/x origin/master',
    'git restore --staged a.ts', 'git reset HEAD a.ts', 'git clean -n', 'git stash list',
    'git stash show -p', 'git log -S stash', 'git commit -m "checkout -- x"']) {
    assert.strictEqual(scan(`cd /c/x && ${cmd}`).destructive.length, 0, cmd);
  }
});

// One temp episodes.db built by the real migrations and CLI, so a schema or
// lock-acquire change breaks these tests instead of silently disarming the guard.
let episode;
function heldEpisode() {
  if (episode) return episode;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'devrl-guard-'));
  const db = path.join(dir, 'episodes.db');
  const py = (...args) => {
    const r = spawnSync('python', args, { encoding: 'utf8', env: { ...process.env, DEVRL_TEST_MODE: '1' } });
    assert.strictEqual(r.status, 0, r.stderr);
    return r.stdout.trim();
  };
  py(path.join(DEVRL, 'migrate.py'), db);
  const devrl = (...args) => py(path.join(DEVRL, 'devrl.py'), '--db', db, ...args);
  const eid = devrl('episode-init', 'guard test', '--wallclock-budget-sec', '600');
  devrl('lock-acquire', eid, '--session', 's-held');
  episode = { db, eid, devrl };
  return episode;
}

const bash = (session, command) => ({ session_id: session, tool_name: 'Bash', tool_input: { command } });
const run = (session, command) => runHook(HOOK, bash(session, command), { DEVRL_DB: heldEpisode().db });

test('the session holding an episode is denied a bare feature-repo command', { skip: !HAS_DEVRL }, () => {
  const out = run('s-held', 'npm run build');
  assert.ok(isDeny(out));
  const reason = out.hookSpecificOutput.permissionDecisionReason;
  assert.match(reason, new RegExp(heldEpisode().eid));
  assert.match(reason, /cd <absolute/);
});

test('the holding session may run a pinned command', { skip: !HAS_DEVRL }, () => {
  assert.strictEqual(run('s-held', 'cd /c/Users/skf_s/hippo && npm run build'), null);
});

test('a session without an episode is left alone', { skip: !HAS_DEVRL }, () => {
  assert.strictEqual(run('s-other', 'npm run build'), null);
  assert.strictEqual(run('s-other', 'cd /c/x && git stash pop'), null);
});

test('work-destroying git is denied until the command opts in', { skip: !HAS_DEVRL }, () => {
  const out = run('s-held', 'cd /c/x && git stash pop');
  assert.ok(isDeny(out));
  assert.match(out.hookSpecificOutput.permissionDecisionReason, /DEVRL_ALLOW_DESTRUCTIVE=1/);
  assert.strictEqual(run('s-held', 'cd /c/x && DEVRL_ALLOW_DESTRUCTIVE=1 git stash pop'), null);
});

test('the guard lifts once the episode is finalized', { skip: !HAS_DEVRL }, () => {
  heldEpisode().devrl('episode-finalize', heldEpisode().eid, '--status', 'aborted');
  assert.strictEqual(run('s-held', 'npm run build'), null);
});
