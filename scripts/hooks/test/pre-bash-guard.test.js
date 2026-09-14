'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const { runHook, isDeny } = require('./helpers');

const HOOK = path.join(__dirname, '..', 'pre-bash-guard.js');

test('npm run dev in the foreground with no TMUX is denied', () => {
  const out = runHook(HOOK, { tool_name: 'Bash', tool_input: { command: 'npm run dev' } });
  assert.ok(isDeny(out));
});

test('npm run dev with run_in_background true is allowed', () => {
  const out = runHook(HOOK, { tool_name: 'Bash', tool_input: { command: 'npm run dev', run_in_background: true } });
  assert.strictEqual(out, null);
});

test('git push --force origin main is denied', () => {
  const out = runHook(HOOK, { tool_name: 'Bash', tool_input: { command: 'git push --force origin main' } });
  assert.ok(isDeny(out));
});
