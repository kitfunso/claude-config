#!/usr/bin/env node
// agy cuts one injected message near 48 KB, so the text goes out as 16 KB parts (tested 22 Nov: all parts arrive).
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HOME = os.homedir();
const CLAUDE = process.env.NEON_CLAUDE_DIR || path.join(HOME, '.claude');
const AGY_CUT = 24_000;
const PART = 16_000;
const NATIVE = new Set(['agents.md', 'gemini.md']);
const read = (f) => { try { return fs.readFileSync(f, 'utf8'); } catch { return null; } };
const file = (f, body) => `# FILE ${f}\n${body.trim()}`;

export function stripSection(md, heading) {
  const i = md.indexOf(`\n${heading}`);
  if (i === -1) return md;
  const j = md.indexOf('\n## ', i + heading.length + 1);
  return md.slice(0, i) + (j === -1 ? '' : md.slice(j));
}

function globalRules() {
  const out = [];
  const g = read(path.join(CLAUDE, 'CLAUDE.md'));
  if (g) out.push(file('~/.claude/CLAUDE.md', stripSection(g, '## Model Routing')));
  const dir = path.join(CLAUDE, 'rules');
  for (const f of fs.existsSync(dir) ? fs.readdirSync(dir).sort() : []) {
    if (f.endsWith('.md')) out.push(file(`~/.claude/rules/${f}`, read(path.join(dir, f)) || ''));
  }
  return out;
}

/** Folders from the drive root down to cwd, the order Claude Code loads CLAUDE.md in. */
export function chain(cwd) {
  const dirs = [];
  for (let d = path.resolve(cwd); ; d = path.dirname(d)) {
    dirs.unshift(d);
    if (path.dirname(d) === d) return dirs;
  }
}

function repoRootOf(cwd) {
  for (let d = path.resolve(cwd); ; d = path.dirname(d)) {
    if (fs.existsSync(path.join(d, '.git'))) return d;
    if (path.dirname(d) === d) return null;
  }
}

/** agy itself loads AGENTS.md / GEMINI.md from cwd up to the repo root. */
function agyLoads(f, cwd) {
  if (!NATIVE.has(path.basename(f).toLowerCase())) return false;
  const root = repoRootOf(cwd) || path.resolve(cwd);
  const dir = path.dirname(path.resolve(f)).toLowerCase();
  return chain(cwd).some((d) => d.toLowerCase() === dir && d.toLowerCase().startsWith(root.toLowerCase()));
}

/** Claude Code's `@path` import: expand a .md/.txt file that exists; leave emails and handles alone. */
export function expandImports(text, baseDir, cwd, depth = 0) {
  if (depth > 3) return text;
  return text.replace(/(^|\s)@((?:~[\\/]|\.{1,2}[\\/])?[\w.\-\\/]+\.(?:md|txt))\b/g, (all, pre, ref) => {
    const f = ref.startsWith('~') ? path.join(HOME, ref.slice(2)) : path.resolve(baseDir, ref);
    const body = read(f);
    if (body === null) return all;
    if (agyLoads(f, cwd)) {
      const cut = Buffer.byteLength(body) > AGY_CUT ? ` It is ${Buffer.byteLength(body)} B; agy cut it at 24 KB, so read the full file before work.` : '';
      return `${pre}@${ref} (agy loads this file itself.${cut})`;
    }
    return `${pre}\n${expandImports(body, path.dirname(f), cwd, depth + 1)}\n`;
  });
}

function claudeMdChain(cwd) {
  const out = [];
  for (const d of chain(cwd)) {
    const f = path.join(d, 'CLAUDE.md');
    if (path.resolve(f).toLowerCase() === path.join(CLAUDE, 'CLAUDE.md').toLowerCase()) continue;
    const body = read(f);
    if (body) out.push(file(f, expandImports(body, d, cwd)));
  }
  return out;
}

/** An AGENTS.md agy loads but cuts at 24 KB gets a note, so Neon reads the rest. */
function cutNotes(cwd) {
  const notes = [];
  for (const d of chain(cwd)) {
    for (const n of ['AGENTS.md', 'GEMINI.md']) {
      const f = path.join(d, n);
      if (!fs.existsSync(f) || !agyLoads(f, cwd)) continue;
      const size = fs.statSync(f).size;
      if (size > AGY_CUT) notes.push(`NOTE: ${f} is ${size} B. agy cut it at 24 KB. Read the full file before you start work.`);
    }
  }
  return notes.join('\n');
}

/** Claude keys its memory folder by path with each non-alphanumeric character as "-". */
export const memoryKey = (dir) => path.resolve(dir).replace(/[^A-Za-z0-9]/g, '-');

function memoryIndexes(cwd) {
  const out = [];
  for (const d of chain(cwd)) {
    const f = path.join(CLAUDE, 'projects', memoryKey(d), 'memory', 'MEMORY.md');
    const body = read(f);
    if (body) out.push(file(f, `Memory index for ${d}. Open a linked file in this folder before any claim about it.\n\n${body}`));
  }
  return out;
}

export function chunk(text, size = PART) {
  const parts = [];
  let rest = text;
  while (rest.length > size) {
    const cut = rest.lastIndexOf('\n', size) > size / 2 ? rest.lastIndexOf('\n', size) : size;
    parts.push(rest.slice(0, cut));
    rest = rest.slice(cut);
  }
  if (rest) parts.push(rest);
  return parts;
}

export function buildRules(cwd) {
  const pieces = [];
  for (const fn of [globalRules, () => claudeMdChain(cwd), () => cutNotes(cwd), () => memoryIndexes(cwd)]) {
    try { pieces.push(...[].concat(fn() || [])); } catch {}
  }
  return pieces.filter(Boolean).join('\n\n');
}

function main() {
  let cwd = process.cwd();
  try {
    const p = JSON.parse(fs.readFileSync(0, 'utf8') || '{}');
    cwd = p.cwd || p.workspacePaths?.[0] || cwd;
  } catch {}
  const parts = chunk(buildRules(cwd));
  process.stdout.write(JSON.stringify({
    injectSteps: parts.map((p, i) => ({ systemMessage: { systemMessage: `[claude rules part ${i + 1}/${parts.length}]\n${p}` } })),
  }));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch { process.stdout.write('{}'); }
}
