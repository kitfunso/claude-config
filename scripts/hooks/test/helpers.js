'use strict';
const { spawnSync } = require('child_process');
const os = require('os');
const path = require('path');

// record-component skips a missing file, so test denials never land in the live devrl db.
const NO_DEVRL_DB = path.join(os.tmpdir(), 'hook-tests-no-devrl-db', 'episodes.db');

// Strip TMUX by default so "no tmux" tests are deterministic on any host shell.
function runHook(hookPath, payload, envOverrides) {
  const env = Object.assign({}, process.env, { DEVRL_DB: NO_DEVRL_DB }, envOverrides || {});
  if (!envOverrides || envOverrides.TMUX === undefined) delete env.TMUX;
  const result = spawnSync('node', [hookPath], { input: JSON.stringify(payload), encoding: 'utf8', env });
  const out = (result.stdout || '').trim();
  if (!out) return null;
  try { return JSON.parse(out); } catch (e) { return null; }
}

function isDeny(output) {
  return !!(output && output.hookSpecificOutput && output.hookSpecificOutput.permissionDecision === 'deny');
}

module.exports = { runHook, isDeny };
