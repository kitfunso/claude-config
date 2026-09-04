// Shared writer for component_outcomes: the PostToolUse recorder and every
// guard's deny path go through here. Never throws, because recording must never
// change what the caller was going to do.

const fs = require('fs');

const DEFAULT_DB = 'C:/Users/skf_s/.claude/dev-framework/episodes.db';

function record({ kind, name, sessionId, cwd, blocked = 0, notes = null }) {
  try {
    if (!kind || !name) return;

    const dbPath = process.env.DEVRL_DB || DEFAULT_DB;
    // Opening a missing file would create an empty db in whatever repo we ran in.
    if (!fs.existsSync(dbPath)) return;

    process.removeAllListeners('warning');
    process.on('warning', () => {});

    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(dbPath);
    try {
      db.exec('PRAGMA busy_timeout = 3000');
      db.prepare(
        'INSERT INTO component_outcomes ' +
          '(kind, name, session_id, invoked_at, blocked, cwd, notes) ' +
          'VALUES (?, ?, ?, ?, ?, ?, ?)'
      ).run(
        String(kind),
        String(name),
        sessionId || null,
        new Date().toISOString(),
        blocked ? 1 : 0,
        cwd || null,
        notes ? String(notes).slice(0, 500) : null
      );
    } finally {
      db.close();
    }
  } catch {
    // Swallowed on purpose: every failure here must leave the caller untouched.
  }
}

module.exports = { record };
