#!/usr/bin/env node
// Proves a comment cleanup changed ONLY comments: strips comment and blank lines
// from HEAD and from the working tree, then demands the remainder match exactly.
// Usage: node verify-comment-edit.js <repo> [file...]  (files default to all modified)

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const budget = require('./hooks/comment-budget-guard.js');

const repo = path.resolve(process.argv[2] || '.');
const only = process.argv.slice(3).map((f) => f.split(path.sep).join('/'));
const git = (args) => execFileSync('git', ['-C', repo, ...args], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });

const codeOnly = budget.codeOnly;

let changed;
try {
  changed = git(['diff', '--name-only', 'HEAD']).split('\n').map((s) => s.trim()).filter(Boolean);
} catch (e) {
  console.error('not a git repo or no HEAD: ' + repo);
  process.exit(2);
}

let checked = 0;
const bad = [];
const skipped = [];
for (const rel of (only.length ? only : changed)) {
  const ext = path.extname(rel).slice(1).toLowerCase();
  const token = budget.LINE_TOKENS[ext];
  if (!token) { skipped.push(rel); continue; }
  let head;
  try { head = git(['show', 'HEAD:' + rel]); } catch { skipped.push(rel + ' (new file)'); continue; }
  const abs = path.join(repo, rel);
  if (!fs.existsSync(abs)) { bad.push(rel + ' -> DELETED'); continue; }
  const now = fs.readFileSync(abs, 'utf8');
  checked += 1;
  if (codeOnly(head, token) !== codeOnly(now, token)) bad.push(rel + ' -> CODE CHANGED');
}

console.log(path.basename(repo) + ': ' + checked + ' source files checked, ' +
  skipped.length + ' skipped (non-source/new), ' + bad.length + ' with code changes');
for (const b of bad) console.log('  FAIL ' + b);
process.exit(bad.length ? 1 : 0);
