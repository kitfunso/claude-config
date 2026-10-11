'use strict';
// settings.json is per box and untracked, so these check whatever wiring the box has.
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HOOKS = path.join(__dirname, '..');
const SETTINGS = path.join(process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude'), 'settings.json');
const skip = !fs.existsSync(SETTINGS);

function wired() {
  const groups = Object.values(JSON.parse(fs.readFileSync(SETTINGS, 'utf8')).hooks || {}).flat();
  return groups.flatMap((group) => group.hooks || []).filter((hook) => hook.type === 'command');
}

test('every hook script wired in settings.json exists', { skip }, () => {
  const lines = wired().map((h) => [h.command, ...(h.args || [])].join(' ').replace(/\\/g, '/'));
  const scripts = lines.flatMap((line) => line.match(/scripts\/hooks\/[\w./-]+\.(?:js|py)\b/g) || []);
  assert.ok(scripts.length > 0, 'no hook scripts found');
  for (const s of scripts) assert.ok(fs.existsSync(path.join(HOOKS, s.slice('scripts/hooks/'.length))), `${s} is wired but missing`);
});

// Shell form on Windows is Git Bash's wrapper, then bash, then the program: three launches where exec form is one.
test('a node or python hook is wired in exec form', { skip: skip || process.platform !== 'win32' }, () => {
  const viaShell = wired().filter((h) => !h.args && /^\s*(node|python)\s/.test(h.command)).map((h) => h.command);
  assert.deepStrictEqual(viaShell, [], 'move the script path into "args" and leave "command" as the program name');
  const badExec = wired().filter((h) => h.args && /[\s"']/.test(h.command)).map((h) => h.command);
  assert.deepStrictEqual(badExec, [], 'with "args", "command" is the program name alone');
});

// `hippo init` re-adds its raw prompt hook: it looks for its marker in `command` and cannot see the wrapper's args.
test('hippo prompt context runs once, through the cached wrapper', { skip }, () => {
  const prompt = Object.values(JSON.parse(fs.readFileSync(SETTINGS, 'utf8')).hooks?.UserPromptSubmit || {})
    .flatMap((group) => group.hooks || []);
  const raw = prompt.filter((h) => /\bhippo\s+context\b/.test(h.command || '')).map((h) => h.command);
  assert.deepStrictEqual(raw, [], 'delete it: hippo_context_cached.py already serves the pinned rules and recall');
});
