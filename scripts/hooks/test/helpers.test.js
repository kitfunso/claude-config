'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { runHook } = require('./helpers');

const PROBE = path.join(os.tmpdir(), 'hook-test-print-devrl-db.js');
fs.writeFileSync(PROBE, 'process.stdout.write(JSON.stringify({ db: process.env.DEVRL_DB || null }));');

test('runHook points DEVRL_DB at a missing file so hook denials never reach the live devrl db', () => {
  const { db } = runHook(PROBE, {});
  assert.ok(db, 'DEVRL_DB unset: the hook records into the live devrl db');
  assert.ok(!fs.existsSync(db), `DEVRL_DB is a real file, so the hook records into it: ${db}`);
});
