#!/usr/bin/env node
// Prints each comment block in a file with its line range and the code it precedes,
// so a cleanup pass can judge blocks without reading the whole file.
// Usage: node comment-blocks.js <file> [minBlockLines]

const fs = require('fs');
const path = require('path');
const budget = require('./hooks/comment-budget-guard.js');

const file = process.argv[2];
const min = Number(process.argv[3] || 2);
const token = budget.LINE_TOKENS[path.extname(file).slice(1).toLowerCase()];
if (!token) { console.error('unsupported file type: ' + file); process.exit(2); }

const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
const kind = budget.classify(lines, token);
let i = 0;
while (i < lines.length) {
  if (kind[i] !== 'comment') { i += 1; continue; }
  let j = i;
  while (j < lines.length && kind[j] === 'comment') j += 1;
  if (j - i >= min) {
    let nxt = j;
    while (nxt < lines.length && kind[nxt] === 'blank') nxt += 1;
    console.log('[' + (i + 1) + '-' + j + '] ' + (j - i) + ' lines | code: ' + (lines[nxt] || '<eof>').trim().slice(0, 66));
    for (let k = i; k < j; k += 1) console.log('    ' + lines[k]);
  }
  i = j;
}
