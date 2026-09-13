'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const { runHook } = require('./helpers');

const HOOK = path.join(__dirname, '..', 'triage-prompt.js');

function hasBanner(prompt) {
  const out = runHook(HOOK, { prompt });
  return !!(out && out.hookSpecificOutput && typeof out.hookSpecificOutput.additionalContext === 'string');
}

test('a plain read request does not banner', () => {
  assert.strictEqual(hasBanner('check scripts/foo.py and tell me what it does'), false);
});

test('a Sharpe claim against a named file banners', () => {
  assert.strictEqual(hasBanner('verify the Sharpe 1.8 claim in report.md'), true);
});

test('a code-shaped return statement does not banner', () => {
  assert.strictEqual(hasBanner('the function should return 0 on success'), false);
});

test('a percent return claim banners', () => {
  assert.strictEqual(hasBanner('returns 12% a year'), true);
});

test('a first name plus a role word does not banner', () => {
  assert.strictEqual(hasBanner('Keith asked the engineer to look'), false);
});
