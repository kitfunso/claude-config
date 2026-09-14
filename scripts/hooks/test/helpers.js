'use strict';
const { spawnSync } = require('child_process');

// Strip TMUX by default so "no tmux" tests are deterministic on any host shell.
function runHook(hookPath, payload, envOverrides) {
  const env = Object.assign({}, process.env, envOverrides || {});
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
