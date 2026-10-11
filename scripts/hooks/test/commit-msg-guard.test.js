'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const { runHook, isDeny } = require('./helpers');

const HOOK = path.join(__dirname, '..', 'commit-msg-guard.js');
const run = (command, tool_name = 'Bash') => runHook(HOOK, { tool_name, tool_input: { command } });

test('an em dash in an inline commit message is denied', () => {
  assert.ok(isDeny(run('git commit -m "fix: a \u2014 b"')));
});

test('git options before the subcommand do not hide the commit', () => {
  assert.ok(isDeny(run('git -C "C:/work tree/repo" commit -m "fix: a \u2014 b"')));
  assert.ok(isDeny(run('git -c user.name=x --no-pager commit -m "fix: a \u2014 b"')));
  assert.ok(isDeny(run("git --git-dir='C:/r/.git' -C C:/r commit -m 'fix: a \u2014 b'")));
});

test('a clean commit and a non-commit command pass in silence', () => {
  assert.strictEqual(run('git -C C:/repo commit -F C:/tmp/msg.txt'), null);
  assert.strictEqual(run('git -C C:/repo status; echo "commit \u2014 x"'), null);
  assert.strictEqual(run('echo "a \u2014 b"'), null);
});

test('a PowerShell pipe into git commit is denied, with or without git options', () => {
  assert.ok(isDeny(run('"msg" | git commit -F -', 'PowerShell')));
  assert.ok(isDeny(run('"msg" | git -C C:/repo commit -F -', 'PowerShell')));
  assert.strictEqual(run('"msg" | git -C C:/repo commit -F -', 'Bash'), null);
});
