#!/usr/bin/env node
// SessionStart hook: install NEW skills/commands pushed to kitfunso/claude-config.
// Additions only. It never modifies or deletes a local file, and never merges.
// Why: ~/.claude is a clone shared by two machines with divergent tracked state;
// a plain `git pull` would import the other box's machine-specific config.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const REPO = path.join(os.homedir(), '.claude');

function git(args) {
  return execFileSync('git', ['-C', REPO, ...args], { encoding: 'utf8', timeout: 20000 });
}

try {
  git(['fetch', '--quiet', 'origin']);
  const adds = git(['diff', '--name-status', 'HEAD..origin/main'])
    .split('\n')
    .map((line) => line.split('\t'))
    .filter(([status, file]) =>
      status === 'A' &&
      file &&
      (file.startsWith('skills/') || file.startsWith('commands/')) &&
      !fs.existsSync(path.join(REPO, file)) // guard: additions must not clobber anything on disk
    )
    .map(([, file]) => file);

  if (adds.length) {
    git(['checkout', 'origin/main', '--', ...adds]);
    const names = [...new Set(adds.map((f) => f.split('/')[1]))];
    console.log('[sync-new-skills] installed from claude-config origin/main: ' + names.join(', '));
  }
} catch (err) {
  // Offline or git failure: stay silent. This hook must never block session start.
}
process.exit(0);
