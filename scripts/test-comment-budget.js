const { spawnSync } = require('child_process');
const fs = require('fs');
const HOOK = 'C:/Users/skf_s/.claude/scripts/hooks/comment-budget-guard.js';

function run(payload) {
  const r = spawnSync('node', [HOOK], { input: JSON.stringify(payload), encoding: 'utf8' });
  if (r.stderr && r.stderr.trim()) return { err: r.stderr.trim() };
  if (!r.stdout.trim()) return { decision: 'allow' };
  return { decision: JSON.parse(r.stdout).hookSpecificOutput.permissionDecision };
}

const NL = String.fromCharCode(10);
const cases = [
  ['fat js block -> deny', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/a.js',
      content: ['// Cache the handle so repeated calls skip the syscall.',
        '// Measured 2026-08-30: 12ms -> 0.4ms on a warm run.',
        '// The syscall is the dominant cost because Windows revalidates',
        '// the console handle on every write, which we do 40x a frame.',
        '// See ARCHITECTURE.md for the full measurement table.',
        'let h = null;'].join(NL) } }],
  ['one-line comment -> allow', 'allow', {
    tool_name: 'Edit', tool_input: { file_path: 'C:/p/src/a.js',
      new_string: ['// Windows revalidates the handle per write, so cache it.', 'let h = null;'].join(NL) } }],
  ['3-line header -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/a.js',
      content: ['// one', '// two', '// three', 'const x = 1;'].join(NL) } }],
  ['divider, blank, 3-line jsdoc -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/a.ts',
      content: ['// ---- Section ----', '', '/**', ' * One real sentence.', ' */',
        'const a = 1;'].join(NL) } }],
  ['blank-split narration still denied by density', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/b.ts',
      content: ['// one', '// two', '// three', '', '// four', '// five', '// six',
        'const a = 1;', 'const b = 2;', 'const c = 3;', 'const d = 4;', 'const e = 5;',
        'const f = 6;', 'const g = 7;', 'const h = 8;', 'const i = 9;'].join(NL) } }],
  ['typedef block -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/c.js',
      content: ['/**', ' * @typedef {{ a: string }} Thing', ' * @typedef {Thing} Other', ' */',
        'const x = 1;'].join(NL) } }],
  ['one-line tsdoc field docs -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/types.ts',
      content: ['export interface A {', '  /** Node id. */', '  id: string;',
        '  /** Path inside the node. */', '  path: string;', '  /** New text. */',
        '  value: string;', '  /** Bytes changed. */', '  n: number;', '}',
        'export const X = 1;', 'export const Y = 2;', 'export const Z = 3;',
        'export const W = 4;', 'export const V = 5;'].join(NL) } }],
  ['multi-line untagged jsdoc still denied', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/e.ts',
      content: ['/**', ' * We tried three approaches here.', ' * The first was too slow.',
        ' * The second leaked memory.', ' */', 'const q = 1;'].join(NL) } }],
  ['python # narration -> deny', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/m.py',
      content: ['# Step 1: load the frame', '# Step 2: normalise it', '# Step 3: write it out',
        '# Step 4: log the result', 'x = 1'].join(NL) } }],
  ['python docstring -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/m.py',
      content: ['def f(x):', '    """Return x.', '', '    Args:', '        x: a number.', '',
        '    Returns:', '        The number.', '    """', '    return x'].join(NL) } }],
  ['markdown -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/README.md',
      content: ['# a', '# b', '# c', '# d', '# e'].join(NL) } }],
  ['docs/ dir -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/docs/notes.js',
      content: ['// a', '// b', '// c', '// d', '// e'].join(NL) } }],
  ['20 code lines 5 comments -> deny on density', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/b.js',
      content: Array.from({ length: 20 }, (_, i) => (i % 4 === 0 ? '// note ' + i : 'const v' + i + ' = ' + i + ';')).join(NL) } }],
  ['bash shebang only -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/go.sh',
      content: ['#!/usr/bin/env bash', 'set -euo pipefail', 'echo hi'].join(NL) } }],
  ['non-source ext -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/x.json', content: '{}' } }],
  ['jsdoc tag on line 3 -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/c.js',
      content: ['/**', ' * Add two numbers.', ' * @param {number} a', ' * @returns {number}', ' */', 'const add = (a) => a;'].join(NL) } }],
  ['narrative jsdoc no tags -> deny', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/d.js',
      content: ['/**', ' * We cache the handle here.', ' * Measured 2026-08-30, it was slow.', ' * Now it is fast.', ' */', 'let h;'].join(NL) } }],
];

let fail = 0;
for (const [name, want, payload] of cases) {
  const got = run(payload);
  const ok = got.decision === want;
  if (!ok) fail += 1;
  console.log((ok ? 'PASS' : 'FAIL') + '  ' + name + '  want=' + want + ' got=' + (got.decision || got.err));
}

const self = { tool_name: 'Write', tool_input: { file_path: HOOK, content: fs.readFileSync(HOOK, 'utf8') } };
const selfGot = run(self);
const selfOk = selfGot.decision === 'allow';
if (!selfOk) fail += 1;
console.log((selfOk ? 'PASS' : 'FAIL') + '  dogfood: hook passes its own rule  got=' + (selfGot.decision || selfGot.err));
console.log(fail === 0 ? 'ALL PASS' : fail + ' FAILED');
process.exit(fail ? 1 : 0);
