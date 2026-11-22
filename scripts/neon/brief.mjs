// Writes the handoff brief that a Neon tab starts from: Keith's words, Claude's last state and each repo's git state.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const TMP = os.tmpdir().toLowerCase();

export function toWin(p) {
  const m = /^\/([a-z])\/(.*)$/i.exec(p || '');
  return m ? `${m[1].toUpperCase()}:\\${m[2].replace(/\//g, '\\')}` : p;
}

const isTemp = (p) => p.toLowerCase().startsWith(TMP);

function git(dir, args) {
  try {
    return execFileSync('git', ['-C', dir, ...args], { encoding: 'utf8', timeout: 8000, windowsHide: true, stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    return null;
  }
}

export const repoRoot = (dir) => (git(dir, ['rev-parse', '--show-toplevel']) || '').replace(/\//g, '\\') || null;

/** Newest real cwd: exists, not under %TEMP%, mapped to its git toplevel. */
export function workDir(scan, fallback) {
  for (const c of [...scan.cwds].reverse().map(toWin)) {
    if (c && !isTemp(c) && fs.existsSync(c)) return repoRoot(c) || c;
  }
  return fallback;
}

/** Every repo the session edited in or worked in, newest first, at most 6. */
export function touchedRepos(scan) {
  const dirs = [...scan.edits.map((f) => path.dirname(toWin(f))), ...scan.cwds.map(toWin)].reverse();
  const roots = [];
  for (const d of dirs) {
    if (!d || isTemp(d) || !fs.existsSync(d)) continue;
    const r = repoRoot(d);
    if (r && !roots.includes(r)) roots.push(r);
    if (roots.length === 6) break;
  }
  return roots;
}

function repoState(root) {
  const out = [`### ${root}  (branch ${git(root, ['branch', '--show-current']) || '?'})`];
  const status = (git(root, ['status', '--short']) || '(clean)').split('\n');
  const more = status.length > 40 ? [`… ${status.length - 40} more: run git status here`] : [];
  out.push('```', ...status.slice(0, 40), ...more, '```');
  const ahead = git(root, ['log', '--oneline', '@{u}..']);
  out.push(ahead === null ? 'Upstream: none set.' : `Not pushed: ${ahead || 'nothing'}`);
  const stash = git(root, ['stash', 'list']);
  if (stash) out.push(`Stash:\n${stash.split('\n').slice(0, 5).join('\n')}`);
  return out.join('\n');
}

const quote = (t) => t.split('\n').map((l) => `> ${l}`).join('\n');

export function briefText({ session, scan, transcript, cwd, repos, movedAt }) {
  const status = scan.limit.working ? 'WORKING' : 'IDLE';
  const L = [
    `# Handoff from Claude session "${session.name || '(no name)'}" (${session.sessionId.slice(0, 8)})`,
    `Moved: ${movedAt} · Limit: ${scan.limit.limitText.split('\n')[0] || 'usage limit'}`,
    `Status: ${status} (${status === 'WORKING' ? 'continue Keith\'s last request; if Claude already finished it, say so and wait' : 'Claude was idle: report, then wait for Keith'})`,
    `Work dir: ${cwd}`,
    `Transcript (full detail; grep it, never read it whole): ${transcript}`,
    '', '## Keith\'s requests, oldest first (verbatim, last 20)',
    ...scan.prompts.map((p) => `- ${p.at}\n${quote(p.text)}`),
    '', '## Claude\'s last 3 messages (verbatim)',
    ...scan.texts.map((t) => `- ${t.at}\n${quote(t.text)}`),
  ];
  if (scan.todos) L.push('', '## Task list at the stop', ...scan.todos.map((t) => `- [${t.status}] ${t.content}`));
  L.push('', '## Background jobs and sub-agents with no result yet');
  L.push(scan.jobs.length ? scan.jobs.map((j) => `- ${j.kind}: ${j.what}`).join('\n') : '- none found');
  if (scan.jobs.length) L.push(`Do not close Claude tab "${session.name}" while a job runs. That kills the job.`);
  L.push('', '## Each repo touched', ...repos.map(repoState));
  L.push('', '## Files Claude edited (newest last)', ...scan.edits.slice(-20).map((f) => `- ${f}`));
  L.push('', '## Last 15 commands', '```', ...scan.commands, '```');
  L.push('', PROTOCOL, '', '## Neon log', '');
  return L.join('\n');
}

const PROTOCOL = `## Protocol for Neon
1. Run git status and git log -5 in each repo above. Trust the repo over this brief.
2. If Status is WORKING, continue Keith's last request from where Claude stopped.
   If Status is IDLE, give Keith a 3-line status of this session, then wait.
3. Never redo a push, a publish, a deploy or a send that the transcript shows as done.
   Grep the transcript for the command before you repeat any outward action.
4. Before each step, read "## Neon log" below. If it says "Claude took back", stop.
5. After each step, add one new line at the very end of this file: time, what you did, result.
   Never edit any other line of this file.`;

export function writeBrief(dir, ctx) {
  fs.mkdirSync(dir, { recursive: true });
  const slug = (ctx.session.name || 'session').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);
  const file = path.join(dir, `${ctx.movedAt.slice(0, 10)}-${slug}-${ctx.session.sessionId.slice(0, 8)}.md`);
  fs.writeFileSync(file, briefText(ctx));
  return file;
}
