'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const { spawnSync } = require('node:child_process');

const HOOK = path.join(__dirname, '..', 'pre-write-guard.js');
const BACKUP_ROOT = path.join(os.homedir(), '.claude', 'backups');
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pwg-test-'));
const tempClaudeMd = path.join(tmpDir, 'CLAUDE.md');
fs.writeFileSync(tempClaudeMd, 'test content for backup mapping\n');

// Reproduces backup()'s own formula since the hook has no exports to import.
function expectedBackupPath(filePath) {
  const mapped = path.resolve(filePath).replace(':', '');
  return path.join(BACKUP_ROOT, mapped) + '.old';
}

test('a file named CLAUDE.md anywhere is backed up under backups/ with the drive colon stripped', () => {
  const expected = expectedBackupPath(tempClaudeMd);
  spawnSync('node', [HOOK], {
    input: JSON.stringify({ tool_name: 'Write', tool_input: { file_path: tempClaudeMd, content: 'new content' }, session_id: 'test' }),
    encoding: 'utf8',
  });
  assert.ok(fs.existsSync(expected), `expected backup at ${expected}`);
  assert.strictEqual(fs.readFileSync(expected, 'utf8'), 'test content for backup mapping\n');
  fs.rmSync(expected, { force: true });
});

after(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});
