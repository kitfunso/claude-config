#!/usr/bin/env node
/**
 * PreToolUse hook for the Edit and Write tools.
 *
 * Auto-creates a .old backup of any file in ~/.claude/ or named CLAUDE.md
 * before allowing the Write to proceed. Enforces the Hand-Maintained Files
 * (CRITICAL) rule in ~/.claude/CLAUDE.md.
 *
 * Behavior: silent auto-backup, then defer. Recovery: copy the backup back:
 * `~/.claude/backups/<path with the drive colon removed>.old` -> `<path>`.
 * Emits NO decision: "approve" would auto-approve the writes this rule exists
 * to make you confirm, so the hook backs up and leaves permission alone.
 * Log: ~/.claude/logs/hand-maintained-backups.log
 */
const fs = require('fs');
const path = require('path');
const os = require('os');

const HOME = os.homedir();
const CLAUDE_DIR = path.join(HOME, '.claude').replace(/\\/g, '/');
const LOG_FILE = path.join(HOME, '.claude', 'logs', 'hand-maintained-backups.log');
const BACKUP_ROOT = path.join(HOME, '.claude', 'backups');

function isProtected(filePath) {
  if (!filePath) return false;
  const normalized = path.resolve(filePath).replace(/\\/g, '/');
  if (normalized.startsWith(CLAUDE_DIR + '/')) return true;
  if (path.basename(normalized).toLowerCase() === 'claude.md') return true;
  return false;
}

function ensureLogDir() {
  const dir = path.dirname(LOG_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function backup(filePath) {
  if (!fs.existsSync(filePath)) return null;
  // Mirrors the absolute path under backups/ so N files never collide into one <file>.old.
  const mapped = path.resolve(filePath).replace(':', '');
  const backupPath = path.join(BACKUP_ROOT, mapped) + '.old';
  fs.mkdirSync(path.dirname(backupPath), { recursive: true });
  fs.copyFileSync(filePath, backupPath);
  return backupPath;
}

function log(message) {
  try {
    ensureLogDir();
    const ts = new Date().toISOString();
    fs.appendFileSync(LOG_FILE, `${ts} ${message}\n`);
  } catch (e) {
    // never block on logging failure
  }
}

function main() {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { input += chunk; });
  process.stdin.on('end', () => {
    try {
      const data = JSON.parse(input);
      const filePath = data.tool_input?.file_path;

      if (filePath && isProtected(filePath)) {
        const backupPath = backup(filePath);
        if (backupPath) log(`backed up ${filePath} -> ${backupPath}`);
      }
    } catch (e) {
      log(`guard error: ${e && e.message}`);
    }
  });
}

main();
