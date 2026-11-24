import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync, spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'neon-test-'));
const CLAUDE = path.join(ROOT, 'claude');
const HANDOFF = path.join(ROOT, 'handoffs');
Object.assign(process.env, { NEON_CLAUDE_DIR: CLAUDE, NEON_GEMINI_DIR: path.join(HANDOFF, 'gemini'), NEON_HANDOFF_DIR: HANDOFF, NEON_NO_TAB: '1' });
const H = await import('./handoff.mjs');
const T = await import('./transcript.mjs');

const line = (o) => JSON.stringify({ timestamp: new Date().toISOString(), cwd: 'C:/nowhere', ...o });
const prompt = (text) => line({ type: 'user', message: { role: 'user', content: text } });
const grace = () => line({ type: 'user', isMeta: true, message: { role: 'user', content: `${T.GRACE_TEXT}, then this turn is cut off]` } });
const reset = () => line({ type: 'user', isMeta: true, message: { role: 'user', content: 'Your claude.ai usage limit has reset. Continue.' } });
const limitErr = () => line({ type: 'assistant', isApiErrorMessage: true, message: { content: [{ type: 'text', text: "You've hit your session limit · resets 4pm (Europe/London)" }] } });

function session(sid, kind = 'interactive', extra = {}) {
  fs.mkdirSync(path.join(CLAUDE, 'sessions'), { recursive: true });
  fs.mkdirSync(path.join(CLAUDE, 'projects', 'k'), { recursive: true });
  fs.writeFileSync(path.join(CLAUDE, 'sessions', `${sid}.json`), JSON.stringify({ pid: process.pid, sessionId: sid, cwd: ROOT, kind, name: `s-${sid}`, ...extra }));
  fs.writeFileSync(path.join(CLAUDE, 'projects', 'k', `${sid}.jsonl`), [prompt('fix the parser'), line({ type: 'permission-mode', permissionMode: 'bypassPermissions' }), grace()].join('\n'));
}

test('reset time: under 20 minutes moves nothing', () => {
  const at = (h, m) => new Date(2026, 10, 22, h, m);
  assert.equal(H.resetMinutes('resets 4pm (Europe/London)', at(15, 50)), 10);
  assert.equal(H.resetMinutes('resets 12:30am (Europe/London)', at(23, 50)), 40);
  assert.ok(H.resetMinutes('resets Nov 28, 4am (Europe/London)', at(12, 0)) > 8000);
  const fail = (text, now) => H.shouldMoveOnFailure({ error: 'rate_limit', last_assistant_message: text }, now);
  assert.equal(fail("You've hit your session limit · resets 4pm", at(15, 50)), false);
  assert.equal(fail("You've hit your session limit · resets 4pm", at(12, 0)), true);
  assert.equal(fail("You've hit your weekly limit · resets Nov 28, 4am", at(12, 0)), true);
  assert.equal(fail('API Error: Rate limit reached', at(12, 0)), false);
  assert.equal(H.shouldMoveOnFailure({ error: 'server_error', last_assistant_message: "You've hit your limit" }), false);
});

test('limit state: working, idle and reset', () => {
  const p = (lines) => T.limitState(lines.map((l) => JSON.parse(l)));
  assert.deepEqual([p([prompt('a'), grace()]).hit, p([prompt('a'), grace()]).working], [true, true]);
  assert.equal(p([grace(), prompt('b')]).working, false);
  assert.equal(p([prompt('a'), grace(), reset()]).hit, false);
  assert.equal(p([prompt('a'), limitErr()]).working, true);
  assert.equal(T.keithPromptText(JSON.parse(prompt('<task-notification> done'))), null);
});

test('permission mode, wt args and corporate filter', () => {
  assert.deepEqual(H.permissionArgs('bypassPermissions'), ['--dangerously-skip-permissions']);
  assert.deepEqual(H.permissionArgs('auto'), ['--mode', 'auto']);
  assert.deepEqual(H.permissionArgs('default'), []);
  const a = H.tabArgs({ session: { name: 'a;b', sessionId: 'x' }, cwd: 'C:\\r\\', brief: 'C:\\b.md', mode: 'auto', repos: ['C:\\r', 'C:\\o'] });
  assert.ok(a.includes('Neon · a\\;b') && a.includes('C:\\r') && a.includes('--add-dir') && a.includes('C:\\o'));
  assert.equal(a.filter((x) => x === '--add-dir').length, 1);
  assert.ok(H.isCorporate(['C:\\Users\\skf_s\\MR3A_Report\\src']));
});

test('session filter: half-written, headless and dead sessions never move', () => {
  session('live1');
  session('print1', 'print');
  session('dead1', 'interactive', { pid: 999999 });
  fs.writeFileSync(path.join(CLAUDE, 'sessions', 'half.json'), '{"pid":12,');
  const ids = H.readSessions().filter(H.isMovable).map((s) => s.sessionId);
  assert.deepEqual(ids, ['live1']);
});

test('three workers at once: each session moves once', async () => {
  session('live2');
  const run = () => new Promise((res) => {
    const c = spawn(process.execPath, [path.join(HERE, 'handoff.mjs'), '--all'], { env: process.env });
    let out = ''; c.stdout.on('data', (d) => { out += d; }); c.on('close', () => res(out));
  });
  const outs = (await Promise.all([run(), run(), run()])).join('\n');
  assert.equal((outs.match(/\topened\t/g) || []).length, 2, outs);
  const brief = fs.readdirSync(HANDOFF).find((f) => f.includes('live1'));
  const text = fs.readFileSync(path.join(HANDOFF, brief), 'utf8');
  assert.match(text, /Status: WORKING/);
  assert.match(text, /fix the parser/);
});

test('guard blocks a moved session; reclaim unblocks it', () => {
  const g = (input) => spawnSync(process.execPath, [path.join(HERE, 'handoff.mjs'), '--guard'], { input: JSON.stringify(input), env: process.env, encoding: 'utf8' }).stdout;
  assert.match(g({ session_id: 'live1', tool_name: 'Edit', tool_input: {} }), /"permissionDecision":"deny"/);
  assert.equal(g({ session_id: 'live1', tool_name: 'Bash', tool_input: { command: 'node handoff.mjs --reclaim live1' } }), '');
  assert.equal(g({ session_id: 'other', tool_name: 'Edit', tool_input: {} }), '');
  assert.match(H.reclaim('live1'), /reclaimed/);
  assert.equal(g({ session_id: 'live1', tool_name: 'Edit', tool_input: {} }), '');
});

test.after(() => fs.rmSync(ROOT, { recursive: true, force: true }));
