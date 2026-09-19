'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const { ask, lint } = require('../lib/jev');

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
