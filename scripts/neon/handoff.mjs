#!/usr/bin/env node
// Moves each live Claude Code session to its own Gemini 4 Neon tab (agy) when Claude hits its usage limit.
// Modes: --on-stop | --on-failure | --guard (Claude hooks, stdin JSON) · --worker | --all [--dry] | --reclaim <id>
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { findTranscript, readTail, limitState, scanTranscript, isLimitText } from './transcript.mjs';
import { workDir, touchedRepos, writeBrief } from './brief.mjs';
import { runSync } from './sync-agy.mjs';

const HOME = os.homedir();
export const CFG = {
  claudeDir: process.env.NEON_CLAUDE_DIR || path.join(HOME, '.claude'),
  handoffDir: process.env.NEON_HANDOFF_DIR || path.join(HOME, '.gemini', 'handoffs'),
  agy: process.env.NEON_AGY || path.join(HOME, 'AppData', 'Local', 'agy', 'bin', 'agy.exe'),
  model: process.env.NEON_MODEL || 'gemini-4-neon-high',
  noTab: process.env.NEON_NO_TAB === '1',
};
const MOVE_KINDS = ['interactive', 'bg'];
const CORPORATE = ['mr3a_report'];
const RECENT_MS = 15 * 60_000;
const SELF = fileURLToPath(import.meta.url);

const markerDir = () => path.join(CFG.handoffDir, 'moved');
const markerFile = (sid) => path.join(markerDir(), `${sid}.json`);
const log = (msg) => {
  fs.mkdirSync(CFG.handoffDir, { recursive: true });
  fs.appendFileSync(path.join(CFG.handoffDir, 'handoff.log'), `${new Date().toISOString()} ${msg}\n`);
};

export function readSessions(dir = path.join(CFG.claudeDir, 'sessions')) {
  const out = [];
  for (const f of fs.existsSync(dir) ? fs.readdirSync(dir) : []) {
    if (!f.endsWith('.json')) continue;
    try { out.push(JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'))); } catch { /* half-written by Claude Code */ }
  }
  return out;
}

export function isAlive(pid) {
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}

export const isMovable = (s) => MOVE_KINDS.includes(s?.kind) && Number.isInteger(s.pid) && isAlive(s.pid);
export const isCorporate = (paths) => paths.some((p) => CORPORATE.some((c) => String(p).toLowerCase().includes(c)));

/** Minutes until a "resets 4pm" / "resets Nov 28, 4am" time, in local time; null if no time is in the text. */
export function resetMinutes(text, now = new Date()) {
  const m = /resets (?:([A-Z][a-z]{2}) (\d{1,2}), )?(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i.exec(text || '');
  if (!m) return null;
  let h = Number(m[3]) % 12;
  if (m[5].toLowerCase() === 'pm') h += 12;
  const t = new Date(now);
  t.setHours(h, Number(m[4] || 0), 0, 0);
  if (m[1]) {
    t.setMonth(new Date(`${m[1]} 1, 2000`).getMonth(), Number(m[2]));
    if (t < now - 864e5) t.setFullYear(t.getFullYear() + 1);
  } else if (t <= now) t.setDate(t.getDate() + 1);
  return Math.round((t - now) / 60_000);
}

export function permissionArgs(mode) {
  return {
    bypassPermissions: ['--dangerously-skip-permissions'],
    auto: ['--mode', 'auto'],
    acceptEdits: ['--mode', 'accept-edits'],
    plan: ['--mode', 'plan'],
  }[mode] || [];
}

export const wtSafe = (s) => String(s).replace(/;/g, '\\;');

const bare = (p) => String(p).replace(/[\\/]+$/, '') || String(p);

export function tabArgs({ session, cwd, brief, mode, repos }) {
  const dir = bare(cwd);
  const extra = repos.filter((r) => bare(r).toLowerCase() !== dir.toLowerCase()).flatMap((r) => ['--add-dir', wtSafe(r)]);
  return ['-w', 'neon', 'new-tab', '--suppressApplicationTitle', '--title', wtSafe(`Neon · ${session.name || session.sessionId.slice(0, 8)}`),
    '-d', dir, CFG.agy, '--model', CFG.model, ...permissionArgs(mode), ...extra,
    '--prompt-interactive', wtSafe(`Read the handoff brief at ${brief} and follow it.`)];
}

/** One worker at a time. A second worker waits, then sees the first one's markers. Returns a release function. */
export function acquireLock(waitMs = 90_000) {
  fs.mkdirSync(CFG.handoffDir, { recursive: true });
  const lock = path.join(CFG.handoffDir, '.lock');
  const until = Date.now() + waitMs;
  for (;;) {
    try { fs.writeFileSync(lock, String(process.pid), { flag: 'wx' }); break; } catch (e) {
      if (e.code !== 'EEXIST') throw e;
      try { if (Date.now() - fs.statSync(lock).mtimeMs > 5 * 60_000) fs.unlinkSync(lock); } catch { /* gone already */ }
      if (Date.now() > until) throw new Error(`lock busy: ${lock}`);
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 250);
    }
  }
  const beat = setInterval(() => { try { fs.utimesSync(lock, new Date(), new Date()); } catch { /* released */ } }, 60_000);
  beat.unref();
  return () => { clearInterval(beat); fs.rmSync(lock, { force: true }); };
}

export function claimMarker(sid, data) {
  fs.mkdirSync(markerDir(), { recursive: true });
  try { fs.writeFileSync(markerFile(sid), JSON.stringify(data), { flag: 'wx' }); return true; } catch (e) {
    if (e.code === 'EEXIST') return false;
    throw e;
  }
}

async function moveOne(s, { dry, manual }) {
  const transcript = findTranscript(CFG.claudeDir, s.sessionId);
  if (!transcript) return `${s.name}\tskipped: no transcript`;
  const scan = await scanTranscript(transcript);
  if (manual) scan.limit = { ...scan.limit, working: true, limitText: 'none: Keith handed this session over by hand' };
  const repos = touchedRepos(scan);
  if (isCorporate([s.cwd, ...repos, ...scan.cwds])) return `${s.name}\tskipped: corporate`;
  const cwd = workDir(scan, s.cwd);
  const movedAt = new Date().toISOString();
  const state = `${scan.permissionMode || 'default'}\t${scan.limit.working ? 'WORKING' : 'IDLE'}`;
  if (dry) return `${s.name}\t${cwd}\t${state}\twould open`;
  if (!claimMarker(s.sessionId, { movedAt })) return `${s.name}\tskipped: already moved`;
  const brief = writeBrief(CFG.handoffDir, { session: s, scan, transcript, cwd, repos, movedAt });
  fs.writeFileSync(markerFile(s.sessionId), JSON.stringify({ movedAt, brief, name: s.name }));
  if (!CFG.noTab) spawn('wt.exe', tabArgs({ session: s, cwd, brief, mode: scan.permissionMode, repos }), { detached: true, stdio: 'ignore' }).unref();
  return `${s.name}\t${cwd}\t${state}\topened\t${brief}`;
}

export async function worker({ dry = false, only = null, manual = false } = {}) {
  const run = async () => {
    const lines = [];
    for (const s of readSessions().filter(isMovable)) {
      if (only && s.sessionId !== only) continue;
      if (fs.existsSync(markerFile(s.sessionId))) { lines.push(`${s.name}\tskipped: already moved`); continue; }
      try { lines.push(await moveOne(s, { dry, manual })); } catch (e) { lines.push(`${s.name}\terror: ${e.message}`); }
    }
    return lines;
  };
  if (dry) return run();
  const release = acquireLock();
  try {
    try { runSync().forEach((n) => log(`sync: ${n}`)); } catch (e) { log(`sync failed: ${e.message}`); }
    return await run();
  } finally { release(); }
}

function spawnWorker(reason) {
  log(`trigger: ${reason}`);
  const child = spawn(process.execPath, [SELF, '--worker'], { detached: true, stdio: 'ignore', windowsHide: true });
  child.unref();
}

const readStdin = () => { try { return JSON.parse(fs.readFileSync(0, 'utf8') || '{}'); } catch { return {}; } };
const registryEntry = (sid) => readSessions().find((s) => s.sessionId === sid);

export function shouldMoveOnStop(p, now = Date.now()) {
  if (!p.transcript_path || !fs.existsSync(p.transcript_path)) return false;
  const lines = readTail(p.transcript_path);
  const st = limitState(lines);
  const last = [...lines].reverse().find((o) => o.timestamp && (o.isApiErrorMessage || JSON.stringify(o.message || '').includes('[Usage limit reached')));
  return st.hit && last && now - Date.parse(last.timestamp) < RECENT_MS;
}

export function shouldMoveOnFailure(p, now = new Date()) {
  const text = `${p.last_assistant_message || ''} ${p.error_details || ''}`;
  if (p.error !== 'rate_limit' || !isLimitText(text)) return false;
  const mins = resetMinutes(text, now);
  return mins === null || mins >= 20;
}

function hookEntry(mode) {
  const p = readStdin();
  if (!p.session_id || fs.existsSync(markerFile(p.session_id))) return;
  if (!MOVE_KINDS.includes(registryEntry(p.session_id)?.kind)) return;   // headless runs (Z0, claude -p) never move
  const go = mode === 'stop' ? shouldMoveOnStop(p) : shouldMoveOnFailure(p);
  if (go) spawnWorker(`${mode} in ${p.session_id}`);
}

function guard() {
  const p = readStdin();
  const marker = p.session_id && markerFile(p.session_id);
  if (!marker || !fs.existsSync(marker)) return;
  const cmd = String(p.tool_input?.command || '');
  if (cmd.includes('handoff.mjs') && cmd.includes('--reclaim')) return;
  const m = JSON.parse(fs.readFileSync(marker, 'utf8'));
  const reason = `Handed to Neon at ${m.movedAt}. Read the "## Neon log" in ${m.brief}, run git status and git log, then ask Keith. `
    + `To take the session back: node "${SELF}" --reclaim ${p.session_id}`;
  process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny', permissionDecisionReason: reason } }));
}

export function reclaim(sid) {
  const marker = markerFile(sid);
  if (!fs.existsSync(marker)) return `not moved: ${sid}`;
  const m = JSON.parse(fs.readFileSync(marker, 'utf8'));
  if (m.brief && fs.existsSync(m.brief)) fs.appendFileSync(m.brief, `\n- ${new Date().toISOString()} Claude took back this session. Neon: stop now.\n`);
  fs.rmSync(marker);
  log(`reclaim ${sid}`);
  return `reclaimed: ${sid} (Neon log told to stop: ${m.brief})`;
}

async function main(argv) {
  const has = (f) => argv.includes(f);
  try {
    if (has('--on-stop')) return hookEntry('stop');
    if (has('--on-failure')) return hookEntry('failure');
    if (has('--guard')) return guard();
    if (has('--reclaim')) return console.log(reclaim(argv[argv.indexOf('--reclaim') + 1]));
    if (has('--worker') || has('--all') || has('--session') || has('--here')) {
      const here = has('--here') ? process.env.CLAUDE_CODE_SESSION_ID : null;
      if (has('--here') && !here) throw new Error('--here needs CLAUDE_CODE_SESSION_ID: run it inside Claude Code (! prefix or the /neon command)');
      const only = here || (has('--session') ? argv[argv.indexOf('--session') + 1] : null);
      const lines = await worker({ dry: has('--dry'), only, manual: Boolean(only) });
      if (!has('--dry')) log(`worker: ${lines.join(' | ')}`);
      return console.log(lines.length ? lines.join('\n') : 'no live sessions to move');
    }
    console.log('usage: handoff.mjs --here | --all [--dry] | --session <id> | --reclaim <id> | --on-stop | --on-failure | --guard');
  } catch (e) {
    log(`error: ${e.stack || e.message}`);
    if (!has('--on-stop') && !has('--on-failure') && !has('--guard')) { console.error(`handoff failed: ${e.message}`); process.exitCode = 1; }
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === SELF) main(process.argv.slice(2));
