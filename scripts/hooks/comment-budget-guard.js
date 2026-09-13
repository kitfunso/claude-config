#!/usr/bin/env node
// Denies an Edit/Write whose comments exceed the budget in rules/coding-standards.md.
// Source files only. Set CLAUDE_COMMENT_BUDGET=off to disable.

const fs = require('fs');
const MAX_RUN = 3;
const MAX_DENSITY = 0.2;
const DENSITY_FLOOR = 15;
// @type must not match "@types/x" or "@typescript". @typedef and friends are API docs too.
const API_DOC = /@param|@returns|@return|@type(?![a-zA-Z])|@typedef|@property|@callback|@example|@throws/;

const LINE_TOKENS = {
  js: '//', jsx: '//', ts: '//', tsx: '//', mjs: '//', cjs: '//',
  go: '//', rs: '//', java: '//', c: '//', h: '//', cpp: '//', hpp: '//',
  cs: '//', swift: '//', kt: '//', scala: '//', php: '//', dart: '//',
  py: '#', sh: '#', bash: '#', zsh: '#', ps1: '#', rb: '#', pl: '#', r: '#',
  sql: '--', lua: '--',
};

const isDocQuote = (s) => s.startsWith('"""') || s.startsWith("'''");

// One pass labels every line, so run and density can never disagree.
// A block is 'doc' if any line in it carries an API tag, not just the opener.
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
      // A one-line /** */ is a field's doc comment, the TSDoc editors show on hover.
      // Narrative bloat is the multi-line untagged block, which still counts.
      const isApi = (j === i && line.startsWith('/**')) ||
        lines.slice(i, Math.min(j + 1, lines.length)).some((l) => API_DOC.test(l));
      for (let k = i; k <= Math.min(j, lines.length - 1); k += 1) kind[k] = isApi ? 'doc' : 'comment';
      i = j + 1; continue;
    }
    if (line.startsWith(token) && !line.startsWith('#!')) { kind[i] = 'comment'; i += 1; continue; }
    i += 1;
  }
  return kind;
}

// A run survives blank lines so a block split by whitespace still counts as one.
function longestRun(lines, token) {
  const kind = classify(lines, token);
  let best = 0;
  let run = 0;
  for (const k of kind) {
    if (k === 'comment') { run += 1; best = Math.max(best, run); continue; }
    if (k === 'blank') continue;
    run = 0;
  }
  return best;
}

function countComments(lines, token) {
  return classify(lines, token).filter((k) => k === 'comment').length;
}

// The single place that decides what is code, so no consumer can drift from the classifier.
function codeOnly(text, token) {
  const lines = text.split(/\r?\n/);
  const kind = classify(lines, token);
  return lines.filter((l, i) => kind[i] === 'code').map((l) => l.trimEnd()).join('\n');
}

// Exported so scan-comments.js grades files with this exact logic, never a copy.
module.exports = { LINE_TOKENS, MAX_RUN, MAX_DENSITY, DENSITY_FLOOR, classify, longestRun, countComments, codeOnly };
if (require.main !== module) return;

let record = () => {};
try { ({ record } = require('./lib/record-component')); } catch (e) { /* recorder missing: keep denying */ }

// Manual slicing, never String#replace(old, new_string): new_string may contain "$&"/"$1".
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

// Shebang/blank/comment header lines are boilerplate, not the body the density budget grades.
function headerEnd(lines, token) {
  const kind = classify(lines, token);
  let i = 0;
  while (i < lines.length) {
    const trimmed = lines[i].trim();
    if (trimmed === '' || trimmed.startsWith('#!') || kind[i] === 'comment') { i += 1; continue; }
    break;
  }
  return i;
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
  const lines = text.split(/\r?\n/);
  const run = longestRun(lines, token);

  // Density is judged on the file the edit produces, not the snippet alone, so a
  // short why-comment dropped into a big file can't read as 100% comments.
  let fileText = input.tool_name === 'Write' ? text : null;
  if (input.tool_name === 'Edit') {
    try {
      const current = fs.readFileSync(ti.file_path, 'utf8');
      fileText = applyEdit(current, String(ti.old_string || ''), String(ti.new_string || ''), ti.replace_all === true);
    } catch (e) {
      fileText = null;
    }
  }

  let why = null;
  if (run > MAX_RUN) {
    why = run + ' comment lines in a row (budget: ' + MAX_RUN + ')';
  } else if (fileText != null) {
    const fileLines = fileText.split(/\r?\n/);
    const body = fileLines.slice(headerEnd(fileLines, token));
    const comments = countComments(body, token);
    const density = body.length ? comments / body.length : 0;
    if (body.length >= DENSITY_FLOOR && density > MAX_DENSITY) {
      why = comments + ' comment lines out of ' + body.length + ' in the resulting file (' +
        Math.round(density * 100) + '%, budget: ' + Math.round(MAX_DENSITY * 100) + '%)';
    }
  }
  if (!why) process.exit(0);

  const reason =
    'comment-budget-guard: ' + filePath + ' has ' + why + '. Comments are one line, two at most. ' +
    'Say WHY a non-obvious choice was made, never WHAT the code does. Measurement notes, dates and ' +
    'incident history go in docs/ARCHITECTURE.md or CLAUDE.md, never in source. Cut the block, then retry.';
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
