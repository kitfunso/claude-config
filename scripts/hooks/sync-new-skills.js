#!/usr/bin/env node
// SessionStart hook: bring ~/.claude up to kitfunso/claude-config origin/main.
// A clean tree that is only behind fast-forwards; a dirty or diverged one gets new
// skills/commands only, so no local edit is ever modified, deleted or merged.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const REPO = path.join(os.homedir(), '.claude');

function git(args, input) {
  return execFileSync('git', ['-C', REPO, ...args], { encoding: 'utf8', timeout: 20000, input });
}

function behindOnly() {
  if (git(['status', '--porcelain', '--untracked-files=no']).trim()) return false;
  try {
    git(['merge-base', '--is-ancestor', 'HEAD', 'origin/main']);
    return true;
  } catch {
    return false; // exit 1: HEAD holds commits origin/main lacks
  }
}

// checkout <tree> -- <new path> ignores sparse rules, and would half-install a parked skill.
function insideSparse(files) {
  const sparse = git(['config', '--type=bool', '--default=false', '--get', 'core.sparseCheckout']).trim();
  if (sparse !== 'true') return files;
  return git(['sparse-checkout', 'check-rules'], files.join('\n') + '\n').split('\n').filter(Boolean);
}

// A path a local commit deleted still reads as an origin-side 'A'. Checking it out
// resurrects it, so ask the merge base which side actually did the deleting.
function locallyDeleted() {
  const base = git(['merge-base', 'HEAD', 'origin/main']).trim();
  return new Set(
    git(['diff', '--name-only', '--diff-filter=D', `${base}..HEAD`, '--', 'skills/', 'commands/'])
      .split('\n')
      .filter(Boolean)
  );
}

function installAdditions() {
  const deleted = locallyDeleted();
  const candidates = git(['diff', '--name-status', 'HEAD..origin/main'])
    .split('\n')
    .map((line) => line.split('\t'))
    .filter(([status, file]) =>
      status === 'A' &&
      file &&
      (file.startsWith('skills/') || file.startsWith('commands/')) &&
      !deleted.has(file) &&
      !fs.existsSync(path.join(REPO, file)) // guard: additions must not clobber anything on disk
    )
    .map(([, file]) => file);
  const adds = candidates.length ? insideSparse(candidates) : [];

  if (adds.length) {
    git(['checkout', 'origin/main', '--', ...adds]);
    const names = [...new Set(adds.map((f) => f.split('/')[1]))];
    console.log('[sync-new-skills] installed from claude-config origin/main: ' + names.join(', '));
  }
}

try {
  git(['fetch', '--quiet', 'origin']);
  const target = git(['rev-parse', 'origin/main']).trim();
  if (git(['rev-parse', 'HEAD']).trim() !== target) {
    if (behindOnly()) {
      git(['merge', '--ff-only', '--quiet', 'origin/main']);
      console.log('[sync-new-skills] fast-forwarded ~/.claude to claude-config origin/main ' + target.slice(0, 7));
    } else {
      installAdditions();
    }
  }
} catch (err) {
  // Never block session start; stderr keeps the reason out of the model's context.
  console.error('[sync-new-skills] skipped: ' + String(err.message).split('\n')[0]);
}
process.exit(0);
