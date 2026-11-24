'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const { spawnSync } = require('node:child_process');
const { runHook, isDeny } = require('./helpers');

const HOOK = path.join(__dirname, '..', 'comment-budget-guard.js');
const PY_HOOK = path.join(__dirname, '..', 'comment_budget_guard.py');
const PY = spawnSync('python', ['--version']).status === 0 ? 'python' : null;
const NO_DB = { DEVRL_DB: path.join(os.tmpdir(), 'hook-tests-no-devrl-db', 'episodes.db') };
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cbg-test-'));
const NL = String.fromCharCode(10);

function runPy(payload, env) {
  const r = spawnSync(PY, [PY_HOOK], { input: JSON.stringify(payload), encoding: 'utf8', env: Object.assign({}, process.env, NO_DB, env || {}) });
  const out = (r.stdout || '').trim();
  return out ? JSON.parse(out) : null;
}

const RUNNERS = [['js', (p, env) => runHook(HOOK, p, env)]];
if (PY) RUNNERS.push(['py', runPy]);
function each(name, fn) {
  for (const [tag, run] of RUNNERS) test(tag + ': ' + name, () => fn(run));
}

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

function legacyFile(name) {
  const lines = [];
  for (let i = 0; i < 40; i += 1) lines.push(i % 3 === 1 ? `// legacy note ${i}` : `const l${i} = ${i};`);
  return { lines, filePath: writeTemp(name, lines.join(NL) + NL) };
}

const edit = (filePath, oldStr, newStr) => ({ tool_name: 'Edit', tool_input: { file_path: filePath, old_string: oldStr, new_string: newStr } });

each('an edit adding one plain comment line denies', (run) => {
  const base = codeLines(50, 'w');
  const filePath = writeTemp('case-b.js', base.join(NL) + NL);
  assert.ok(isDeny(run(edit(filePath, base[24], '// explains the next line' + NL + base[24]))));
});

each('an edit adding a SHORTCUT: line allows', (run) => {
  const base = codeLines(20, 'k');
  const filePath = writeTemp('case-k.js', base.join(NL) + NL);
  const line = '// SHORTCUT: global lock, per-account locks if throughput matters';
  assert.strictEqual(run(edit(filePath, base[4], line + NL + base[4])), null);
});

each('a code-only edit in a file full of old comments allows', (run) => {
  const { filePath } = legacyFile('legacy-a.js');
  assert.strictEqual(run(edit(filePath, 'const l0 = 0;', 'const l0 = 100;')), null);
});

each('an edit that deletes a comment allows', (run) => {
  const { lines, filePath } = legacyFile('legacy-b.js');
  assert.strictEqual(run(edit(filePath, lines[1] + NL + lines[2], lines[2])), null);
});

each('an edit that rewords a comment denies', (run) => {
  const { lines, filePath } = legacyFile('legacy-c.js');
  assert.ok(isDeny(run(edit(filePath, lines[1], '// legacy note, now reworded'))));
});

each('an edit that moves a commented line allows', (run) => {
  const { lines, filePath } = legacyFile('legacy-d.js');
  assert.strictEqual(run(edit(filePath, [lines[0], lines[1], lines[2]].join(NL), [lines[2], lines[0], lines[1]].join(NL))), null);
});

each('an edit whose new_string holds a literal $` is not expanded', (run) => {
  const { lines, filePath } = legacyFile('legacy-e.js');
  assert.strictEqual(run(edit(filePath, lines[30], "const s = '$`';")), null);
});

each('CLAUDE_COMMENT_BUDGET=off allows', (run) => {
  assert.strictEqual(run({ tool_name: 'Write', tool_input: { file_path: 'C:/p/src/off.js', content: '// x' + NL + 'const a = 1;' } },
    { CLAUDE_COMMENT_BUDGET: 'off' }), null);
});

each('a Write over an existing file that keeps its comments allows', (run) => {
  const { lines, filePath } = legacyFile('legacy-f.js');
  assert.strictEqual(run({ tool_name: 'Write', tool_input: { file_path: filePath, content: lines.concat(['const z = 1;']).join(NL) } }), null);
});

each('a Write over an existing file that adds a comment denies', (run) => {
  const { lines, filePath } = legacyFile('legacy-g.js');
  assert.ok(isDeny(run({ tool_name: 'Write', tool_input: { file_path: filePath, content: lines.concat(['// fresh note', 'const z = 1;']).join(NL) } })));
});

const portedCases = [
  ['plain one-line comment -> deny', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/a.js',
      content: ['// Windows revalidates the handle per write, so cache it.', 'let h = null;'].join(NL) } }],
  ['fat js block -> deny', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/a.js',
      content: ['// Cache the handle so repeated calls skip the syscall.',
        '// Measured 2026-08-30: 12ms -> 0.4ms on a warm run.',
        '// The syscall is the dominant cost because Windows revalidates',
        '// the console handle on every write, which we do 40x a frame.',
        '// See ARCHITECTURE.md for the full measurement table.',
        'let h = null;'].join(NL) } }],
  ['SAFETY: line -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/r.ts',
      content: ['// SAFETY: the SELECT names every key Row reads', 'const r = row as Row;'].join(NL) } }],
  ['lint and type directives -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/l.ts',
      content: ['// eslint-disable-next-line no-console', '// @ts-expect-error vendor type is wrong', '/* istanbul ignore next */',
        'console.log(1);'].join(NL) } }],
  ['python directives -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/d.py',
      content: ['# -*- coding: utf-8 -*-', '# pylint: disable=invalid-name', '# type: ignore', 'import x  # noqa: F401'].join(NL) } }],
  ['license block -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/lic.js',
      content: ['// Copyright 2026 Example Ltd', '// Licensed under the Apache License, Version 2.0.',
        '// Unless required by applicable law or agreed to in writing,', '// software is distributed on an AS IS BASIS.',
        'const x = 1;'].join(NL) } }],
  ['issue link -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/i.ts',
      content: ['// Vendor bug: https://github.com/vercel/next.js/issues/12345', 'const x = 1;'].join(NL) } }],
  ['test-runner directive -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/t.test.ts',
      content: ['// @vitest-environment jsdom', 'import { test } from "vitest";'].join(NL) } }],
  ['shellcheck directive -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/run.sh',
      content: ['#!/usr/bin/env bash', '# shellcheck disable=SC2086', 'echo $x'].join(NL) } }],
  ['sql -- note -> deny', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/q.sql',
      content: ['-- pick the newest row', 'SELECT 1;'].join(NL) } }],
  ['comment, code, comment -> deny', 'deny', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/f.ts',
      content: ['// one', 'const a = 1;', '// two', 'const b = 2;'].join(NL) } }],
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
  ['multi-line jsdoc on an export -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/api.ts',
      content: ['/** Opens the store at a path.', ' * Throws when the schema is newer than this build. */',
        'export function open(p: string): Store { return load(p); }'].join(NL) } }],
  ['multi-line jsdoc on an interface member -> allow', 'allow', {
    tool_name: 'Write', tool_input: { file_path: 'C:/p/src/types.ts',
      content: ['export interface Bearer {', '  /** Role the resolver vouches for.', '   * Any other value reads as viewer. */',
        '  role?: Role;', '}'].join(NL) } }],
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
  each(name, (run) => {
    const out = run(payload);
    if (want === 'deny') assert.ok(isDeny(out));
    else assert.strictEqual(out, null);
  });
}

each('dogfood: both hook sources carry no stray comments', (run) => {
  for (const [src, ext] of [[HOOK, 'js'], [PY_HOOK, 'py']]) {
    const content = fs.readFileSync(src, 'utf8');
    assert.strictEqual(run({ tool_name: 'Write', tool_input: { file_path: path.join(tmpDir, 'dogfood-new.' + ext), content } }), null, src);
  }
});

after(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});
