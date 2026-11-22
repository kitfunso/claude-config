// Runs Claude Code's own hooks from settings.json for a non-Claude caller (the agy bridge), with Claude's matching and output rules.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

const CLAUDE = process.env.NEON_CLAUDE_DIR || path.join(os.homedir(), '.claude');

/** Claude hook groups for one event, read live so agy never runs a stale copy. */
export function claudeGroups(event, settingsFile = path.join(CLAUDE, 'settings.json')) {
  try { return JSON.parse(fs.readFileSync(settingsFile, 'utf8')).hooks?.[event] || []; } catch { return []; }
}

export function matcherOk(matcher, value) {
  if (!matcher || matcher === '*') return true;
  try { return new RegExp(`^(?:${matcher})$`).test(value || ''); } catch { return matcher === value; }
}

function globRegex(glob) {
  let re = '';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*' && glob[i + 1] === '*') { re += glob[i + 2] === '/' ? '(?:.*/)?' : '.*'; i += glob[i + 2] === '/' ? 2 : 1; }
    else if (c === '*') re += '[^/]*';
    else if (c === '?') re += '[^/]';
    else re += c.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp(`${re}$`, 'i');
}

/** Claude's `if` rule, e.g. Write(//**\/memory/*.md) or Bash(git commit:*). */
export function ifOk(rule, toolName, input = {}) {
  if (!rule) return true;
  const m = /^([\w|]+)(?:\((.*)\))?$/.exec(rule.trim());
  if (!m || !m[1].split('|').includes(toolName)) return false;
  if (!m[2]) return true;
  const target = String(input.file_path ?? input.command ?? input.url ?? '').replace(/\\/g, '/');
  if (m[2].endsWith(':*')) return target.startsWith(m[2].slice(0, -2));
  return globRegex(m[2].replace(/^\/\//, '')).test(target);
}

/** Handlers to run for one event; scripts/neon handlers are Claude-session plumbing and stay out of agy. */
export function handlersFor(event, { matchValue, toolName, toolInput } = {}) {
  const out = [];
  for (const g of claudeGroups(event)) {
    if (!matcherOk(g.matcher, matchValue ?? toolName)) continue;
    for (const h of g.hooks || []) {
      const line = [h.command, ...(h.args || [])].join(' ');
      if (h.type !== 'command' || /scripts[\\/]neon[\\/]/.test(line)) continue;
      if (h.if && !ifOk(h.if, toolName, toolInput)) continue;
      out.push(h);
    }
  }
  return out;
}

/** Env for a hook: the caller's, minus the ids of the Claude session that started agy, so no hook mistakes agy for it. */
export function hookEnv(cwd) {
  const env = { ...process.env, CLAUDE_PROJECT_DIR: cwd, NEON_BRIDGE: '1' };
  for (const k of Object.keys(env)) if (/^CLAUDE_CODE_|^CLAUDECODE$|^CLAUDE_PID$/.test(k)) delete env[k];
  return env;
}

export function runHandler(h, payload, { cwd, capMs = 25_000 } = {}) {
  const opts = { cwd, env: hookEnv(cwd), windowsHide: true, detached: !!h.async };
  const child = h.args ? spawn(h.command, h.args, opts) : spawn(h.command, { ...opts, shell: true });
  child.stdin.on('error', () => {});
  child.stdin.end(JSON.stringify(payload));
  if (h.async) { child.unref(); return Promise.resolve({ code: 0, stdout: '', stderr: '' }); }
  return new Promise((resolve) => {
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => { child.kill(); resolve({ code: null, stdout, stderr: `${stderr}timed out` }); }, Math.min((h.timeout || 60) * 1000, capMs));
    child.stdout.on('data', (c) => { stdout += c; });
    child.stderr.on('data', (c) => { stderr += c; });
    child.on('error', (e) => { clearTimeout(timer); resolve({ code: null, stdout, stderr: e.message }); });
    child.on('close', (code) => { clearTimeout(timer); resolve({ code, stdout, stderr }); });
  });
}

/** Claude's output contract folded into one verdict: deny/ask/block reasons, extra context, rewritten input. */
export function merge(results, event) {
  const v = { deny: [], ask: [], block: [], context: [], updatedInput: null };
  const plainIsContext = event === 'SessionStart' || event === 'UserPromptSubmit';
  for (const r of results) {
    const out = (r.stdout || '').trim();
    if (r.code === 2) { (event === 'PreToolUse' ? v.deny : v.block).push(r.stderr.trim() || 'blocked by a Claude hook'); continue; }
    let j = null;
    if (out.startsWith('{')) { try { j = JSON.parse(out); } catch { j = null; } }
    if (!j) { if (out && plainIsContext) v.context.push(out); continue; }
    const hso = j.hookSpecificOutput || {};
    if (hso.permissionDecision === 'deny') v.deny.push(hso.permissionDecisionReason || 'denied by a Claude hook');
    if (hso.permissionDecision === 'ask') v.ask.push(hso.permissionDecisionReason || 'a Claude hook asks to confirm');
    if (j.decision === 'block') (event === 'PreToolUse' ? v.deny : v.block).push(j.reason || 'blocked by a Claude hook');
    if (j.continue === false) v.block.push(j.stopReason || 'a Claude hook stopped the turn');
    if (hso.additionalContext) v.context.push(hso.additionalContext);
    if (hso.updatedInput) v.updatedInput = { ...(v.updatedInput || {}), ...hso.updatedInput };
  }
  return v;
}

export async function runClaudeHooks(event, payload, sel, opts) {
  const hs = handlersFor(event, sel);
  if (!hs.length) return merge([], event);
  return merge(await Promise.all(hs.map((h) => runHandler(h, payload, opts))), event);
}
