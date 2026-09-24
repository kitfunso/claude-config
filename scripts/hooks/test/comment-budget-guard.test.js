'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const { runHook, isDeny } = require('./helpers');

const HOOK = path.join(__dirname, '..', 'comment-budget-guard.js');
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cbg-test-'));

function writeTemp(name, content) {
  const p = path.join(tmpDir, name);
  fs.writeFileSync(p, content);
  return p;
}

function codeLines(n, prefix) {
  const out = [];
  for (let i = 1; i <= n; i += 1) out.push(`const ${prefix}${i} = ${i};`);
  return out;
}

test('editing in a 2-line comment on a 100-line file with 4 existing comments allows', () => {
  const base = codeLines(100, 'v');
  [9, 29, 49, 69].forEach((i) => { base[i] = '// existing note'; });
  const filePath = writeTemp('case-a.js', base.join('\n') + '\n');
  const oldStr = base[89];
  const newStr = '// added context\n// second line\n' + oldStr;
  const out = runHook(HOOK, { tool_name: 'Edit', tool_input: { file_path: filePath, old_string: oldStr, new_string: newStr } });
  assert.strictEqual(out, null);
});

test('an edit inserting a 4-comment-line run denies', () => {
  const base = codeLines(50, 'w');
  const filePath = writeTemp('case-b.js', base.join('\n') + '\n');
  const oldStr = base[24];
  const newStr = '// one\n// two\n// three\n// four\n' + oldStr;
  const out = runHook(HOOK, { tool_name: 'Edit', tool_input: { file_path: filePath, old_string: oldStr, new_string: newStr } });
  assert.ok(isDeny(out));
});

test('a 20-line write with a 3-line header and 1 body comment allows', () => {
  const lines = ['#!/usr/bin/env node', '// header note one', '// header note two'];
  for (let i = 1; i <= 17; i += 1) lines.push(i === 8 ? '// body note' : `const b${i} = ${i};`);
  const out = runHook(HOOK, { tool_name: 'Write', tool_input: { file_path: path.join(tmpDir, 'case-c.js'), content: lines.join('\n') + '\n' } });
  assert.strictEqual(out, null);
});

test('a 20-line write with 8 comment lines denies', () => {
  const lines = [];
  for (let i = 1; i <= 20; i += 1) lines.push(i % 2 === 0 && i <= 16 ? `// note ${i}` : `const c${i} = ${i};`);
  const out = runHook(HOOK, { tool_name: 'Write', tool_input: { file_path: path.join(tmpDir, 'case-d.js'), content: lines.join('\n') + '\n' } });
  assert.ok(isDeny(out));
});

test('an edit whose new_string holds a literal $& does not corrupt the density check', () => {
  const base = codeLines(30, 'x');
  const filePath = writeTemp('case-e.js', base.join('\n') + '\n');
  const oldStr = base[14];
  const newStr = '// note about x15\n// second note\nconst escaped = "literal $& stays literal";\n' + oldStr;
  const out = runHook(HOOK, { tool_name: 'Edit', tool_input: { file_path: filePath, old_string: oldStr, new_string: newStr } });
  assert.strictEqual(out, null);
});

const NL = String.fromCharCode(10);
const portedCases = [
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
  // Dropped 'divider, blank, 3-line jsdoc -> allow': the blank-continuation fix below denies it now (4-line run).
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

for (const [name, want, payload] of portedCases) {
  test(name, () => {
    const out = runHook(HOOK, payload);
    if (want === 'deny') assert.ok(isDeny(out));
    else assert.strictEqual(out, null);
  });
}

test('dogfood: hook passes its own rule', () => {
  const out = runHook(HOOK, { tool_name: 'Write', tool_input: { file_path: HOOK, content: fs.readFileSync(HOOK, 'utf8') } });
  assert.strictEqual(out, null);
});

test('blank-split narration still denied by density', () => {
  const out = runHook(HOOK, { tool_name: 'Write', tool_input: { file_path: 'C:/p/src/b.ts',
    content: ['// one', '// two', '// three', '', '// four', '// five', '// six',
      'const a = 1;', 'const b = 2;', 'const c = 3;', 'const d = 4;', 'const e = 5;',
      'const f = 6;', 'const g = 7;', 'const h = 8;', 'const i = 9;'].join(NL) } });
  assert.ok(isDeny(out));
});

test('comment, code, comment, code, comment, code is allowed', () => {
  const out = runHook(HOOK, { tool_name: 'Write', tool_input: { file_path: 'C:/p/src/f.ts',
    content: ['// one', 'const a = 1;', '// two', 'const b = 2;', '// three', 'const c = 3;'].join(NL) } });
  assert.strictEqual(out, null);
});

function legacyFile(name) {
  const lines = [];
  for (let i = 0; i < 40; i += 1) lines.push(i % 3 === 1 ? `// legacy note ${i}` : `const l${i} = ${i};`);
  return { lines, filePath: writeTemp(name, lines.join(NL) + NL) };
}

function editOut(filePath, oldStr, newStr) {
  return runHook(HOOK, { tool_name: 'Edit', tool_input: { file_path: filePath, old_string: oldStr, new_string: newStr } });
}

test('over-budget file: a code-only edit allows', () => {
  const { filePath } = legacyFile('legacy-a.js');
  assert.strictEqual(editOut(filePath, 'const l0 = 0;', 'const l0 = 100;'), null);
});

test('over-budget file: an edit that removes a comment allows', () => {
  const { lines, filePath } = legacyFile('legacy-b.js');
  assert.strictEqual(editOut(filePath, lines[1] + NL + lines[2], lines[2]), null);
});

test('over-budget file: one new comment with one new code line denies', () => {
  const { lines, filePath } = legacyFile('legacy-c.js');
  assert.ok(isDeny(editOut(filePath, lines[0], lines[0] + NL + '// fresh note' + NL + 'const fresh = 1;')));
});

test('over-budget file: one new comment with four new code lines allows', () => {
  const { lines, filePath } = legacyFile('legacy-d.js');
  const added = [lines[0], '// fresh note'].concat(codeLines(4, 'n'));
  assert.strictEqual(editOut(filePath, lines[0], added.join(NL)), null);
});

test('over-budget file: a code line swapped for a comment denies', () => {
  const { lines, filePath } = legacyFile('legacy-e.js');
  assert.ok(isDeny(editOut(filePath, lines[6], '// swapped in for the code')));
});

test('healthy file pushed over budget by an edit still denies', () => {
  const base = codeLines(20, 'h');
  [3, 9, 15].forEach((i) => { base[i] = '// existing note'; });
  const filePath = writeTemp('healthy.js', base.join(NL) + NL);
  assert.ok(isDeny(editOut(filePath, base[18], '// extra one' + NL + '// extra two' + NL + base[18])));
});

after(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});
