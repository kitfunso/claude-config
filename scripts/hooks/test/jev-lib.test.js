'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const os = require('os');
const fs = require('fs');
const path = require('path');

// Pin the paid-Jev path and a temp counter so tests never touch the live Clef budget.
process.env.JEV_PROVIDER = 'jev';
process.env.CLEF_STATE_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'clef-test-'));
const { ask, lint, provider, neuronsUsed } = require('../lib/jev');

const GOOD = {
  risky: {
    type: 'noul',
    instructions: { question: 'Is `command` risky?' },
    criteria: { true: { what: 'deletes data' }, false: { what: 'reads only' } },
  },
  kind: { type: 'choice', instructions: 'Which kind?', criteria: { read: 'reads', write: 'writes', none: 'neither' } },
  level: { type: 'score', instructions: 'How bad?', criteria: ['fine', 'bad'] },
};

const okResponse = (answers) => ({ ok: true, status: 200, json: async () => ({ answers, usage: { input_tokens: 7 } }) });

test('lint passes a well-formed set', () => {
  assert.deepStrictEqual(lint({ command: 'ls' }, GOOD), []);
});

test('lint catches the criteria shapes that 422', () => {
  const problems = lint({ command: 'ls' }, {
    a: { type: 'choice', instructions: 'x', criteria: ['read', 'write'] },
    b: { type: 'score', instructions: 'x', criteria: { low: 'l', high: 'h' } },
    c: { type: 'noul', instructions: 'x', criteria: { yes: 'y' } },
  });
  assert.strictEqual(problems.filter((p) => !p.startsWith('warn:')).length, 3);
});

test('lint flags a backticked path that is not in state', () => {
  const problems = lint({ command: 'ls' }, { a: { ...GOOD.risky, instructions: 'Is `comand` risky?' } });
  assert.ok(problems.some((p) => p.includes('`comand`')));
});

test('lint warns on a choice with no no-match option', () => {
  const problems = lint('text', { a: { type: 'choice', instructions: 'x', criteria: { read: 'r', write: 'w' } } });
  assert.ok(problems.some((p) => p.startsWith('warn:') && p.includes('no-match')));
});

test('ask without a key makes no HTTP call', async () => {
  const saved = process.env.TYPESAFE_API_KEY;
  delete process.env.TYPESAFE_API_KEY;
  let called = false;
  const out = await ask('s', GOOD, { fetcher: async () => { called = true; } });
  if (saved !== undefined) process.env.TYPESAFE_API_KEY = saved;
  assert.deepStrictEqual(out, { error: 'no key' });
  assert.strictEqual(called, false);
});

test('ask returns an error instead of throwing when fetch rejects', async () => {
  const out = await ask('s', GOOD, { apiKey: 'test', fetcher: async () => { throw new TypeError('network'); } });
  assert.strictEqual(out.error, 'fetch: TypeError');
});

test('ask retries once on 429 then returns answers', async () => {
  let calls = 0;
  const fetcher = async () => (++calls === 1 ? { ok: false, status: 429 } : okResponse({ risky: { noul: 0.9 } }));
  const out = await ask('s', GOOD, { apiKey: 'test', fetcher });
  assert.strictEqual(calls, 2);
  assert.strictEqual(out.answers.risky.noul, 0.9);
  assert.strictEqual(out.usage.input_tokens, 7);
});

test('ask surfaces a 422 body so a bad question shape is debuggable', async () => {
  const fetcher = async () => ({ ok: false, status: 422, text: async () => 'criteria: expected map' });
  const out = await ask('s', GOOD, { apiKey: 'test', fetcher });
  assert.match(out.error, /^http 422: criteria/);
});

test('provider defaults to clef-flash once a Cloudflare account is set, jev otherwise', () => {
  const clef = provider({ CLOUDFLARE_ACCOUNT_ID: 'acct', CLOUDFLARE_API_TOKEN: 'cf' });
  assert.strictEqual(clef.model, 'clef-flash');
  assert.match(clef.endpoint, /accounts\/acct\/ai\/run\/@cf\/cloudflare\/clef-flash$/);
  assert.strictEqual(clef.key, 'cf');
  assert.strictEqual(provider({ TYPESAFE_API_KEY: 'ts' }).key, 'ts');
  assert.strictEqual(provider({ CLOUDFLARE_ACCOUNT_ID: 'acct', JEV_PROVIDER: 'jev', TYPESAFE_API_KEY: 'ts' }).model, 'jev-1.13.0');
  assert.strictEqual(provider({ CLOUDFLARE_ACCOUNT_ID: 'acct', JEV_PROVIDER: 'clef', CLOUDFLARE_API_TOKEN: 'cf' }).model, 'clef');
});

test('clef-local posts to the local server with no key and never touches the neuron budget', async () => {
  const local = provider({ JEV_PROVIDER: 'clef-local' });
  assert.strictEqual(local.endpoint, 'http://127.0.0.1:8787/ai/run/clef-flash');
  assert.strictEqual(provider({ JEV_PROVIDER: 'clef-local', CLEF_LOCAL_URL: 'http://127.0.0.1:9/x' }).endpoint, 'http://127.0.0.1:9/x');
  Object.assign(process.env, { JEV_PROVIDER: 'clef-local', CLEF_DAILY_NEURONS: '0' });
  let url;
  const fetcher = async (u) => { url = u; return { ok: true, status: 200, json: async () => ({ result: { answers: { risky: { noul: 0.7 } }, usage: { input_tokens: 1000000 } } }) }; };
  const before = neuronsUsed();
  const out = await ask('s', GOOD, { fetcher });
  Object.assign(process.env, { JEV_PROVIDER: 'jev' });
  delete process.env.CLEF_DAILY_NEURONS;
  assert.strictEqual(url, local.endpoint);
  assert.strictEqual(out.answers.risky.noul, 0.7);
  assert.strictEqual(neuronsUsed(), before);
});

test('clef calls unwrap the result envelope and count neurons; a spent allocation blocks the call', async () => {
  Object.assign(process.env, { JEV_PROVIDER: 'clef-flash', CLOUDFLARE_ACCOUNT_ID: 'acct', CLEF_DAILY_NEURONS: '10' });
  const fetcher = async () => ({ ok: true, status: 200, json: async () => ({ result: { answers: { risky: { noul: 0.2 } }, usage: { input_tokens: 1000000 } } }) });
  const first = await ask('s', GOOD, { apiKey: 'test', fetcher });
  assert.strictEqual(first.answers.risky.noul, 0.2);
  assert.ok(Math.abs(neuronsUsed() - 8182) < 1);
  let called = false;
  const second = await ask('s', GOOD, { apiKey: 'test', fetcher: async () => { called = true; } });
  Object.assign(process.env, { JEV_PROVIDER: 'jev' });
  delete process.env.CLEF_DAILY_NEURONS;
  assert.deepStrictEqual(second, { error: 'free allocation used' });
  assert.strictEqual(called, false);
});
