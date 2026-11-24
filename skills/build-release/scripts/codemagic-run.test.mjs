import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import assert from 'node:assert/strict';

const SCRIPT = new URL('./codemagic-run.mjs', import.meta.url).pathname.replace(/^\/(\w:)/, '$1');
const IDS = ['a'.repeat(24), 'b'.repeat(24)];
const step = (name, status, log) => ({ name, status, type: null, logUrl: null,
  subactions: [{ command: '#!/usr/bin/env bash\n', status, logUrl: `http://HOST${log}` }] });
const builtIn = (name, status, log) => ({ name, status, type: 'publishing', logUrl: `http://HOST${log}`, subactions: [] });

async function release(states, logs, extra = []) {
  const started = [];
  const hits = [];
  const server = createServer((req, res) => {
    if (req.headers['x-auth-token'] !== 'test-token') return res.writeHead(401).end('bad token');
    if (req.method === 'POST' && req.url === '/builds') {
      started.push(IDS[started.length]);
      return res.end(JSON.stringify({ buildId: started.at(-1) }));
    }
    const id = req.url.match(/^\/builds\/(\w{24})$/)?.[1];
    if (!id) {
      hits.push(req.url);
      return res.end(logs[req.url] ?? '');
    }
    const build = states[id].length > 1 ? states[id].shift() : states[id][0];
    res.end(JSON.stringify({ build }).replaceAll('HOST', req.headers.host));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const env = { ...process.env, CODEMAGIC_API: `http://127.0.0.1:${server.address().port}`, CODEMAGIC_AUTH_TOKEN: 'test-token' };
  const child = spawn(process.execPath, [SCRIPT, '--app', 'x', '--workflow', 'ios-release', '--branch', 'main', ...extra], { env });
  let out = '';
  child.stdout.on('data', (chunk) => { out += chunk; });
  const code = await new Promise((resolve) => child.on('close', resolve));
  server.close();
  return { code, out, started, hits };
}

async function wait(text) {
  const dir = mkdtempSync(join(tmpdir(), 'codemagic-run-test-'));
  try {
    const file = join(dir, 'run.log');
    writeFileSync(file, text);
    const child = spawn(process.execPath, [SCRIPT, '--wait', file, '--seconds', '1']);
    return await new Promise((resolve) => child.on('close', resolve));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test('reruns a font flake, waits through building, reports the submit step', { timeout: 90000 }, async () => {
  const { code, out, started } = await release({
    [IDS[0]]: [{ status: 'failed', buildActions: [step('Build web', 'failed', '/log/font')] }],
    [IDS[1]]: [
      { status: 'building', buildActions: [step('Build web', 'success', '/log/web')] },
      { status: 'finished', buildActions: [step('Build web', 'success', '/log/web'),
        step('Submit for review', 'success', '/log/submit'), builtIn('Publishing', 'success', '/log/publish')] },
    ],
  }, {
    '/log/font': 'Error: next/font/google queries have exactly one entry',
    '/log/submit': 'Version: 1.2.8\nState: WAITING_FOR_REVIEW\n',
  }, ['--report-step', 'Submit for review']);
  assert.match(out, /rerunning: Google Fonts fetch at build time/);
  assert.match(out, /building, 1 steps done/);
  assert.match(out, /State: WAITING_FOR_REVIEW/);
  assert.match(out, new RegExp(`RESULT success ${IDS[1]}`));
  assert.equal(code, 0);
  assert.deepEqual(started, IDS);
});

test('stops on a failure a rerun would not fix', async () => {
  const { code, out, started } = await release({
    [IDS[0]]: [{ status: 'failed', buildActions: [step('Upload the IPA', 'failed', '/log/upload')] }],
  }, { '/log/upload': 'Version code 118 has already been used' });
  assert.match(out, new RegExp(`RESULT failed ${IDS[0]} at "Upload the IPA", log `));
  assert.equal(code, 1);
  assert.deepEqual(started, IDS.slice(0, 1));
});

const READ = 'Read the App Store numbers';
const READ_ARGS = ['--report-step', READ, '--report-lines', '^(WEEK|RESULT) '];
const readLog = (result) => ['Fetching reports for app 123...', '  WEEK 2026-11-02 downloads 14\r', 'WEEKLY digest skipped',
  'WEEK 2026-11-02 sessions 90', 'Done in 2.1s', result].join('\n');
const failedRead = { [IDS[0]]: [{ status: 'failed', buildActions: [step('Build web', 'success', '/log/web'),
  step(READ, 'failed', '/log/read')] }] };
const lastLine = (out) => out.trim().split('\n').at(-1);

test('--report-lines prints only the matching lines, indented, ahead of the script RESULT', async () => {
  const { code, out } = await release({
    [IDS[0]]: [{ status: 'finished', buildActions: [step('Build web', 'success', '/log/web'), step(READ, 'success', '/log/read')] }],
  }, { '/log/read': readLog('RESULT ok 2 weeks') }, READ_ARGS);
  assert.match(out, new RegExp(`${READ}:\\n  WEEK 2026-11-02 downloads 14\\n  WEEK 2026-11-02 sessions 90\\n  RESULT ok 2 weeks\\n`));
  assert.doesNotMatch(out, /Fetching reports|WEEKLY|Done in/);
  assert.equal(out.match(/^RESULT /gm).length, 1);
  assert.equal(lastLine(out), `RESULT success ${IDS[0]}`);
  assert.equal(code, 0);
});

test('--report-lines prints the failed report step lines once, and the script still ends RESULT failed', async () => {
  const { code, out, hits } = await release(failedRead, { '/log/read': readLog('RESULT needs-role app 123') }, READ_ARGS);
  assert.match(out, new RegExp(`${READ}:\\n  WEEK 2026-11-02 downloads 14\\n  WEEK 2026-11-02 sessions 90\\n  RESULT needs-role app 123\\n`));
  assert.match(lastLine(out), new RegExp(`^RESULT failed ${IDS[0]} at "${READ}", log `));
  assert.equal(hits.filter((url) => url === '/log/read').length, 1);
  assert.equal(code, 1);
});

test('--report-lines with another step failed and the report step never run: no crash, a no-log line', async () => {
  const { code, out } = await release({
    [IDS[0]]: [{ status: 'failed', buildActions: [step('Build web', 'failed', '/log/web'),
      { name: READ, status: 'skipped', type: null, logUrl: null, subactions: [] }] }],
  }, { '/log/web': 'Error: the web build broke' }, READ_ARGS);
  assert.match(out, new RegExp(`no log for step "${READ}" in ${IDS[0]}`));
  assert.doesNotMatch(out, /RESULT error|TypeError/);
  assert.match(lastLine(out), new RegExp(`^RESULT failed ${IDS[0]} at "Build web", log `));
  assert.equal(code, 1);
});

test('--report-lines after a watch timeout: no step list to read, still RESULT failed', async () => {
  const { code, out } = await release(failedRead, {}, [...READ_ARGS, '--max-minutes', '0']);
  assert.match(out, new RegExp(`no step named "${READ}" in ${IDS[0]}`));
  assert.match(lastLine(out), new RegExp(`^RESULT failed ${IDS[0]} at "watch timed out", log$`));
  assert.equal(code, 1);
});

test('without --report-lines a failed build prints no step lines', async () => {
  const { code, out } = await release(failedRead, { '/log/read': readLog('RESULT needs-role app 123') }, ['--report-step', READ]);
  assert.doesNotMatch(out, /WEEK|needs-role|Fetching reports/);
  assert.doesNotMatch(out, new RegExp(`${READ}:`));
  assert.match(lastLine(out), new RegExp(`^RESULT failed ${IDS[0]} at "${READ}", log `));
  assert.equal(code, 1);
});

test('--wait on the log of a --report-lines run returns the script RESULT, not the passed-through one', async () => {
  const { out } = await release(failedRead, { '/log/read': readLog('RESULT success 2 weeks') }, READ_ARGS);
  assert.match(out, /^ {2}RESULT success 2 weeks$/m);
  assert.equal(await wait(out), 1);
});
