#!/usr/bin/env node
// Applies comment-block replacements and refuses any result that breaks the budget.
// Bash edits skip the Edit|Write hook, so the check has to live in the writer itself.
// Usage: node trim-comments.js <spec.json>   spec: { "<file>": [[start, end, ["line", ...]], ...] }

const fs = require('fs');
const path = require('path');
const budget = require('./hooks/comment-budget-guard.js');

function grade(lines, token) {
  const comments = budget.countComments(lines, token);
  const run = budget.longestRun(lines, token);
  const density = lines.length ? comments / lines.length : 0;
  const overRun = run > budget.MAX_RUN;
  const overDensity = lines.length >= budget.DENSITY_FLOOR && density > budget.MAX_DENSITY;
  return { comments, run, density, ok: !overRun && !overDensity };
}

const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const staged = [];
const rejected = [];

for (const [file, edits] of Object.entries(spec)) {
  const token = budget.LINE_TOKENS[path.extname(file).slice(1).toLowerCase()];
  if (!token) { rejected.push(file + ' -> unsupported file type'); continue; }
  const before = fs.readFileSync(file, 'utf8');
  const lines = before.split(/\r?\n/);
  for (const [start, end] of edits) {
    const kinds = budget.classify(lines, token);
    for (let i = start - 1; i < end; i += 1) {
      if (kinds[i] !== 'comment' && kinds[i] !== 'doc' && kinds[i] !== 'blank') {
        rejected.push(file + ' -> line ' + (i + 1) + ' is code, not a comment');
      }
    }
  }
  const out = lines.slice();
  for (const [start, end, repl] of [...edits].sort((a, b) => b[0] - a[0])) {
    out.splice(start - 1, end - start + 1, ...repl);
  }
  const g = grade(out, token);
  if (!g.ok) {
    rejected.push(file + ' -> result still over budget: run=' + g.run +
      ' ' + g.comments + '/' + out.length + ' (' + (g.density * 100).toFixed(1) + '%)');
    continue;
  }
  staged.push([file, out.join('\n'), lines.length - out.length, g]);
}

if (rejected.length) {
  console.error('REFUSED, nothing written:');
  for (const r of rejected) console.error('  ' + r);
  process.exit(1);
}

let total = 0;
for (const [file, text, removed, g] of staged) {
  fs.writeFileSync(file, text);
  total += removed;
  console.log('-' + String(removed).padStart(3) + '  run=' + g.run +
    ' dens=' + (g.density * 100).toFixed(1) + '%  ' + file);
}
console.log('removed ' + total + ' lines across ' + staged.length + ' files, all within budget');
