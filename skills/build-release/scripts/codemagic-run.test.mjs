// node --test codemagic-run.test.mjs: runs the script against a stand-in Codemagic API.
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { test } from 'node:test';
import assert from 'node:assert/strict';

const SCRIPT = new URL('./codemagic-run.mjs', import.meta.url).pathname.replace(/^\/(\w:)/, '$1');
const IDS = ['a'.repeat(24), 'b'.repeat(24)];
const step = (name, status, log) => ({ name, status, logUrl: `http://HOST${log}` });

// Each build id answers its states in turn, then repeats the last one.
async function release(states, logs, extra = []) {
  const started = [];
  const server = createServer((req, res) => {
    if (req.headers['x-auth-token'] !== 'test-token') return res.writeHead(401).end('bad token');
    if (req.method === 'POST' && req.url === '/builds') {
      started.push(IDS[started.length]);
      return res.end(JSON.stringify({ buildId: started.at(-1) }));
    }
    const id = req.url.match(/^\/builds\/(\w{24})$/)?.[1];
    if (!id) return res.end(logs[req.url] ?? '');
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
  return { code, out, started };
}

test('reruns a font flake, waits through building, reports the submit step', { timeout: 90000 }, async () => {
  const { code, out, started } = await release({
    [IDS[0]]: [{ status: 'failed', buildActions: [step('Build web', 'failed', '/log/font')] }],
    [IDS[1]]: [
      { status: 'building', buildActions: [step('Build web', 'success', '/log/web')] },
      { status: 'finished', buildActions: [{ name: 'Publish', subactions: [step('Submit for review', 'success', '/log/submit')] }] },
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
