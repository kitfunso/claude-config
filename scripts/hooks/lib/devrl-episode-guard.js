// Bash checks for a session that holds a /dev-framework-rl episode lock. The Bash
// tool keeps its cwd between calls, and an orchestrator interleaving repos loses it.

const fs = require('fs');
const os = require('os');
const path = require('path');

const DEFAULT_DB = path.join(os.homedir(), '.claude', 'dev-framework', 'episodes.db');
const REPO_TOOLS = new Set(['git', 'npm', 'npx', 'vitest', 'codex']);
const ABSOLUTE = /^["']?(?:\/|~|[A-Za-z]:[\\/])/;
const SELF_PINNED = /\s(?:-C|--cd|--prefix)[\s=]+["']?(?:\/|~|[A-Za-z]:[\\/])/;
const ESCAPE = 'DEVRL_ALLOW_DESTRUCTIVE=1';

function words(segment) {
  const w = segment.split(/\s+/).filter(Boolean);
  while (w.length && /^[A-Za-z_]\w*=/.test(w[0])) w.shift();
  return w;
}

function dropsWork(w) {
  let i = 1;
  while (i < w.length && w[i].startsWith('-')) i += w[i] === '-C' || w[i] === '-c' ? 2 : 1;
  const rest = w.slice(i + 1);
  const has = (...flags) => rest.some(t => flags.includes(t));
  switch (w[i]) {
    case 'checkout': return has('--', '.', '-f', '--force');
    case 'restore': return !has('--staged', '-S') || has('--worktree', '-W');
    case 'reset': return has('--hard');
    case 'clean': return rest.some(t => t === '--force' || /^-[a-z]*f/.test(t));
    case 'stash': return !['list', 'show', 'create', 'store'].includes(rest[0]);
    default: return false;
  }
}

// SHORTCUT: quote-aware split, not a shell parser; heredoc bodies and \" escapes can mis-scan.
function scan(command) {
  const unpinned = [];
  const destructive = [];
  const pinned = [false];
  let cur = '';
  let quote = null;
  const flush = () => {
    const segment = cur.trim();
    cur = '';
    const w = words(segment);
    const top = pinned.length - 1;
    if (w[0] === 'cd' || w[0] === 'pushd') {
      if (ABSOLUTE.test(w[1] || '')) pinned[top] = true;
      else if (!w[1] || w[1] === '-') pinned[top] = false;
    } else if (REPO_TOOLS.has(w[0])) {
      if (!pinned[top] && !SELF_PINNED.test(` ${segment}`)) unpinned.push(segment);
      if (w[0] === 'git' && dropsWork(w)) destructive.push(segment);
    }
  };
  for (const c of command) {
    if (quote) {
      cur += c;
      if (c === quote) quote = null;
    } else if (c === '"' || c === "'") {
      quote = c;
      cur += c;
    } else if (c === '(') {
      cur = cur.replace(/\$$/, '');
      flush();
      pinned.push(pinned[pinned.length - 1]);
    } else if (c === ')') {
      flush();
      if (pinned.length > 1) pinned.pop();
    } else if (';&|\n'.includes(c)) {
      flush();
    } else {
      cur += c;
    }
  }
  flush();
  return { unpinned, destructive };
}

function episodeHeldBy(sessionId, dbPath) {
  if (!sessionId || !fs.existsSync(dbPath)) return null;
  process.removeAllListeners('warning');
  process.on('warning', () => {});
  const { DatabaseSync } = require('node:sqlite');
  const db = new DatabaseSync(dbPath, { readOnly: true });
  try {
    const row = db.prepare(
      'SELECT l.episode_id FROM host_lock l JOIN episodes e ON e.id = l.episode_id ' +
        "WHERE l.host_session_id = ? AND e.status = 'running'"
    ).get(sessionId);
    return row ? row.episode_id : null;
  } finally {
    db.close();
  }
}

function devrlDenial(command, sessionId, dbPath = process.env.DEVRL_DB || DEFAULT_DB) {
  const { unpinned, destructive } = scan(command);
  const risky = command.includes(ESCAPE) ? [] : destructive;
  if (!unpinned.length && !risky.length) return null;
  const eid = episodeHeldBy(sessionId, dbPath);
  if (!eid) return null;
  const reasons = [`devrl episode ${eid} is held by this session.`];
  if (unpinned.length) {
    reasons.push(
      `\`${unpinned[0]}\` would run wherever an earlier call left the shell, because the cwd ` +
        'persists between calls. Name the folder in this same call: `cd <absolute repo path> && ...`, ' +
        'or git -C / npm --prefix / codex -C with an absolute path.'
    );
  }
  if (risky.length) {
    reasons.push(
      `\`${risky[0]}\` throws away uncommitted work in a tree other sessions and sub-agents share. ` +
        'Save it first (git diff > <scratch>/backup.diff) or change a copy. If nothing unsaved ' +
        `can be lost, prefix the command with ${ESCAPE}.`
    );
  }
  return reasons.join(' ');
}

module.exports = { scan, devrlDenial };
