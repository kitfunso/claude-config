'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const { spawnSync } = require('node:child_process');
const { decide, NOTICE } = require('../fast-browser-notice');

const HOOK = path.join(__dirname, '..', 'fast-browser-notice.js');

function withLauncher() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fbn-'));
  const launcherPath = path.join(dir, 'fast_browser.py');
  fs.writeFileSync(launcherPath, '');
  return { launcherPath, markerDir: dir, env: {} };
}

test('non-browser tool returns null', () => {
  const opts = withLauncher();
  const result = decide({ tool_name: 'Bash', session_id: 's1' }, opts);
  assert.strictEqual(result, null);
});

test('first claude-in-chrome call returns the notice with no permissionDecision key', () => {
  const opts = withLauncher();
  const result = decide({ tool_name: 'mcp__claude-in-chrome__navigate', session_id: 's2' }, opts);
  assert.strictEqual(result, NOTICE);
  const wrapped = { hookSpecificOutput: { hookEventName: 'PreToolUse', additionalContext: result } };
  assert.ok('additionalContext' in wrapped.hookSpecificOutput);
  assert.ok(!('permissionDecision' in wrapped.hookSpecificOutput));
});

test('second call same session is null, a different session gets the notice', () => {
  const opts = withLauncher();
  const first = decide({ tool_name: 'mcp__playwright__browser_click', session_id: 's3' }, opts);
  assert.strictEqual(first, NOTICE);
  const second = decide({ tool_name: 'mcp__playwright__browser_click', session_id: 's3' }, opts);
  assert.strictEqual(second, null);
  const other = decide({ tool_name: 'mcp__playwright__browser_click', session_id: 's4' }, opts);
  assert.strictEqual(other, NOTICE);
});

test('playwright browser_click also matches', () => {
  const opts = withLauncher();
  const result = decide({ tool_name: 'mcp__playwright__browser_click', session_id: 's5' }, opts);
  assert.strictEqual(result, NOTICE);
});

test('missing launcher path returns null', () => {
  const opts = withLauncher();
  opts.launcherPath = path.join(opts.markerDir, 'does-not-exist.py');
  const result = decide({ tool_name: 'mcp__claude-in-chrome__navigate', session_id: 's6' }, opts);
  assert.strictEqual(result, null);
});

test('CLAUDE_FAST_BROWSER_NOTICE=off returns null', () => {
  const opts = withLauncher();
  opts.env = { CLAUDE_FAST_BROWSER_NOTICE: 'off' };
  const result = decide({ tool_name: 'mcp__claude-in-chrome__navigate', session_id: 's7' }, opts);
  assert.strictEqual(result, null);
});

test('end to end: garbage stdin exits 0 with empty stdout', () => {
  const result = spawnSync('node', [HOOK], { input: 'not json {{{', encoding: 'utf8' });
  assert.strictEqual(result.status, 0);
  assert.strictEqual((result.stdout || '').trim(), '');
});
