#!/usr/bin/env node

const fs = require('fs');
const API_DOC = /@param|@returns|@return|@type(?![a-zA-Z])|@typedef|@property|@callback|@example|@throws/;
const MARK = /\b(SHORTCUT|SAFETY):/;
const LICENSE = /copyright|licen[cs]e\b|spdx-|all rights reserved|@license|@preserve/i;
const KEEP = new RegExp([
  'https?://\\S', '\\brfc\\s?-?\\d{3,}',
  '@(vitest|jest)-environment', 'swift-tools-version', 'webpack(Prefetch|Preload|Mode|Exclude|Include|Exports|ChunkName|Ignore)',
  '@deno-types', 'tslint:', 'oxlint-', 'stylelint-', 'yamllint', 'cspell', 'codespell', 'NOSONAR',
  'eslint-', '^\\W*eslint\\s', '^\\W*global\\s+\\w', 'jshint', '@ts-(ignore|expect-error|nocheck|check)',
  'prettier-ignore', 'biome-ignore', 'deno-lint', '(istanbul|c8|v8)\\s+ignore',
  '\\bnoqa\\b', '^\\W*type:\\s', 'pyright:', 'mypy:', 'pylint:', 'ruff:', 'isort:', '^\\W*fmt:\\s*(on|off|skip)',
  '\\bpragma\\b', '\\bnosec\\b', 'noinspection', '@jsx', '@refresh\\b', '@vite-ignore', 'sourceMappingURL', '@flow\\b',
  '-\\*-\\s*coding', 'coding[:=]\\s*utf', 'vim:', 'shellcheck', '@generated', '^\\W*go:\\w', '\\+build', 'nolint',
  '__PURE__', '__NO_SIDE_EFFECTS__', '^\\W*/\\s*<reference', '^\\W*#requires',
].join('|'), 'i');

const LINE_TOKENS = {
  js: '//', jsx: '//', ts: '//', tsx: '//', mjs: '//', cjs: '//',
  go: '//', rs: '//', java: '//', c: '//', h: '//', cpp: '//', hpp: '//',
  cs: '//', swift: '//', kt: '//', scala: '//', php: '//', dart: '//',
  py: '#', sh: '#', bash: '#', zsh: '#', ps1: '#', rb: '#', pl: '#', r: '#',
  sql: '--', lua: '--',
};

const isDocQuote = (s) => s.startsWith('"""') || s.startsWith("'''");
const API_TARGET = /^(export\b|declare\b|\s+((readonly|static|public|async|get|set)\s+)*[\w$#]+[?!]?\s*[:(<=])/;

function nextCode(lines, from) {
  for (let k = from; k < lines.length; k += 1) if (lines[k].trim()) return lines[k];
  return '';
}

function classify(lines, token) {
  const kind = new Array(lines.length).fill('code');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();
    if (line === '') { kind[i] = 'blank'; i += 1; continue; }
    if (token === '#' && isDocQuote(line)) {
      const q = line.slice(0, 3);
      let j = i;
      if (!line.slice(3).includes(q)) { j += 1; while (j < lines.length && !lines[j].includes(q)) j += 1; }
      for (let k = i; k <= Math.min(j, lines.length - 1); k += 1) kind[k] = 'doc';
      i = j + 1; continue;
    }
    if (line.startsWith('/*')) {
      let j = i;
      while (j < lines.length && !lines[j].includes('*/')) j += 1;
      const isApi = (line.startsWith('/**') && (j === i || API_TARGET.test(nextCode(lines, j + 1)))) ||
        lines.slice(i, Math.min(j + 1, lines.length)).some((l) => API_DOC.test(l));
      for (let k = i; k <= Math.min(j, lines.length - 1); k += 1) kind[k] = isApi ? 'doc' : 'comment';
      i = j + 1; continue;
    }
    if (line.startsWith(token) && !line.startsWith('#!')) { kind[i] = 'comment'; i += 1; continue; }
    i += 1;
  }
  return kind;
}

const isKept = (line) => MARK.test(line) || KEEP.test(line);

function strayComments(lines, token) {
  const kind = classify(lines, token);
  const stray = [];
  let i = 0;
  while (i < lines.length) {
    if (kind[i] !== 'comment') { i += 1; continue; }
    let j = i;
    while (j < lines.length && kind[j] === 'comment') j += 1;
    const block = lines.slice(i, j);
    if (!block.some((l) => LICENSE.test(l))) {
      for (let k = i; k < j; k += 1) if (lines[k].trim() && !isKept(lines[k])) stray.push(lines[k].trim());
    }
    i = j;
  }
  return stray;
}

function addedStray(beforeText, afterText, token) {
  const seen = new Map();
  for (const l of strayComments(beforeText.split(/\r?\n/), token)) seen.set(l, (seen.get(l) || 0) + 1);
  const added = [];
  for (const l of strayComments(afterText.split(/\r?\n/), token)) {
    const n = seen.get(l) || 0;
    if (n > 0) seen.set(l, n - 1); else added.push(l);
  }
  return added;
}

function codeOnly(text, token) {
  const lines = text.split(/\r?\n/);
  const kind = classify(lines, token);
  return lines.filter((l, i) => kind[i] === 'code').map((l) => l.trimEnd()).join('\n');
}

module.exports = { LINE_TOKENS, classify, isKept, strayComments, addedStray, codeOnly };
if (require.main !== module) return;

let record = () => {};
try { ({ record } = require('./lib/record-component')); } catch (e) { /* recorder missing: keep denying */ }

function applyEdit(content, oldStr, newStr, replaceAll) {
  if (!oldStr || content.indexOf(oldStr) === -1) return null;
  if (!replaceAll) {
    const idx = content.indexOf(oldStr);
    return content.slice(0, idx) + newStr + content.slice(idx + oldStr.length);
  }
  let result = '';
  let rest = content;
  let pos;
  while ((pos = rest.indexOf(oldStr)) !== -1) {
    result += rest.slice(0, pos) + newStr;
    rest = rest.slice(pos + oldStr.length);
  }
  return result + rest;
}

let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  if (process.env.CLAUDE_COMMENT_BUDGET === 'off') process.exit(0);
  let input;
  try { input = JSON.parse(raw); } catch { process.exit(0); }
  if (input.tool_name !== 'Edit' && input.tool_name !== 'Write') process.exit(0);

  const ti = input.tool_input || {};
  const filePath = String(ti.file_path || '').split('\\').join('/');
  const ext = (filePath.split('.').pop() || '').toLowerCase();
  const token = LINE_TOKENS[ext];
  if (!token) process.exit(0);
  if (/\/(docs|node_modules|dist|build|vendor|\.venv)\//i.test(filePath)) process.exit(0);

  const text = String(ti.content != null ? ti.content : ti.new_string || '');
  if (!text) process.exit(0);

  let before = '';
  try { before = fs.readFileSync(ti.file_path, 'utf8'); } catch (e) { before = ''; }
  let after = input.tool_name === 'Write' ? text : null;
  if (input.tool_name === 'Edit') {
    after = applyEdit(before, String(ti.old_string || ''), text, ti.replace_all === true);
    if (after == null) { before = String(ti.old_string || ''); after = text; }
  }
  const added = addedStray(before, after, token);
  if (!added.length) process.exit(0);

  const reason =
    'comment-budget-guard: ' + filePath + ' gains ' + added.length + ' comment line(s) outside the keep list, first: "' +
    added[0].slice(0, 100) + '". Code carries no comments (rules/coding-standards.md): delete it, or put the reason ' +
    'in a name, a type or a test. Kept: license blocks, lint/type/tool directives, SHORTCUT: and SAFETY: lines, ' +
    'a link to the issue, RFC or vendor doc behind a limit, and API doc blocks. A stale comment gets deleted, never reworded.';
  record({
    kind: 'hook',
    name: 'comment-budget-guard.js',
    sessionId: input.session_id,
    cwd: input.cwd,
    blocked: 1,
    notes: reason,
  });
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  }));
  process.exit(0);
});
