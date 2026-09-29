'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const { spawnSync } = require('node:child_process');
const { decide } = require('../jev-trigger');

const HOOK = path.join(__dirname, '..', 'jev-trigger.js');
const opts = () => ({ env: {}, markerDir: fs.mkdtempSync(path.join(os.tmpdir(), 'jevt-')) });
const prompt = (p, s = 's') => ({ hook_event_name: 'UserPromptSubmit', session_id: s, prompt: p });
const edit = (file, text, s = 's') => ({ hook_event_name: 'PreToolUse', tool_name: 'Edit', session_id: s, tool_input: { file_path: file, new_string: text } });

test('prompt naming jev fires once per session', () => {
  const o = opts();
  assert.match(decide(prompt('can we use jev to route tickets'), o).text, /Skill tool/);
  assert.strictEqual(decide(prompt('and jev again'), o), null);
});

test('prompt without jev words stays silent', () => {
  assert.strictEqual(decide(prompt('fix the recall test'), opts()), null);
  assert.strictEqual(decide(prompt('javelin and jevons paradox'), opts()), null);
});

test('edit writing a TypeSafe call fires once per file', () => {
  const o = opts();
  const e = edit('C:/r/src/gate.ts', 'const key = process.env.TYPESAFE_API_KEY;');
  assert.match(decide(e, o).text, /Jev\/TypeSafe call in gate\.ts/);
  assert.strictEqual(decide(e, o), null);
  assert.ok(decide(edit('C:/r/src/other.ts', 'jev.ask(q)'), o));
});

test('edit adding an LLM decision call fires the replace test', () => {
  const text = 'const r = await client.messages.create({ system: "classify this ticket" })';
  assert.match(decide(edit('C:/r/route.js', text), opts()).text, /section 1 test/);
});

test('LLM call that only generates text stays silent', () => {
  const text = 'const r = await client.messages.create({ system: "write a summary" })';
  assert.strictEqual(decide(edit('C:/r/sum.js', text), opts()), null);
});

test('markdown and the skill files themselves stay silent', () => {
  assert.strictEqual(decide(edit('C:/r/README.md', 'uses jev'), opts()), null);
  assert.strictEqual(decide(edit('C:/Users/x/.claude/scripts/jev-bench.js', 'jev'), opts()), null);
});

test('env off disables it', () => {
  assert.strictEqual(decide(prompt('jev'), { ...opts(), env: { CLAUDE_JEV_TRIGGER: 'off' } }), null);
});

test('stdin end to end emits hookSpecificOutput and survives bad input', () => {
  const ok = spawnSync('node', [HOOK], { input: JSON.stringify(prompt('jev?', `e2e-${Date.now()}`)) });
  assert.strictEqual(ok.status, 0);
  assert.strictEqual(JSON.parse(ok.stdout).hookSpecificOutput.hookEventName, 'UserPromptSubmit');
  const bad = spawnSync('node', [HOOK], { input: 'not json' });
  assert.strictEqual(bad.status, 0);
  assert.strictEqual(bad.stdout.toString(), '');
});
