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

const bash = (command) => runHook(HOOK, { tool_name: 'Bash', tool_input: { command, run_in_background: true } });

test('a sleep poll with no deadline is denied', () => {
  assert.ok(isDeny(bash('until grep -q "Test Files" C:/tmp/full-test.log; do sleep 5; done; tail C:/tmp/full-test.log')));
  assert.ok(isDeny(bash('until [ -f C:/z0-runs/setn/all.log ]; do sleep 20; done; echo done')));
  assert.ok(isDeny(bash('while ! grep -q done log.txt; do\n  sleep 3\ndone')));
});

test('a bounded poll, a read loop and a for loop are allowed', () => {
  assert.strictEqual(bash("timeout 3600 bash -c 'until grep -q done log.txt; do sleep 5; done'"), null);
  assert.strictEqual(bash('until grep -q done log.txt || [ $SECONDS -gt 3600 ]; do sleep 5; done'), null);
  assert.strictEqual(bash('n=0; while [ $n -lt 60 ]; do sleep 5; n=$((n+1)); done'), null);
  assert.strictEqual(bash('while IFS= read -r line; do echo "$line"; sleep 1; done < list.txt'), null);
  assert.strictEqual(bash('for i in 1 2 3; do sleep 1; done'), null);
});
