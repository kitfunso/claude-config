#!/usr/bin/env node
'use strict';
// usage: node extract-shell-cases.js --out <file.json> [--days 14] [--max 300]
// Prints counts only. The output holds command text, so write it outside this git repo.
const fs = require('fs');
const os = require('os');
const path = require('path');
const readline = require('readline');
const crypto = require('crypto');

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : fallback;
};
// Anything that looks like a credential is dropped whole; a lost sample is cheaper than a leaked key.
const SECRET = /sk-[A-Za-z0-9]|Bearer\s+[A-Za-z0-9._-]{16,}|api[_-]?key\s*[=:]|password\s*[=:]|secret\s*[=:]|token\s*[=:]\s*\S{12,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|[A-Za-z0-9_-]{40,}/i;
const SHELLS = { Bash: 'bash', PowerShell: 'powershell' };

function recentTranscripts(dir, cutoff, found = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) recentTranscripts(full, cutoff, found);
    else if (entry.name.endsWith('.jsonl') && fs.statSync(full).mtimeMs >= cutoff) found.push(full);
  }
  return found;
}

async function shellCalls(file, seen, counts) {
  const lines = readline.createInterface({ input: fs.createReadStream(file, 'utf8'), crlfDelay: Infinity });
  for await (const line of lines) {
    if (!line.includes('"tool_use"') || !(line.includes('"Bash"') || line.includes('"PowerShell"'))) continue;
    let content;
    try { content = JSON.parse(line).message?.content; } catch (e) { counts.unparsed++; continue; }
    for (const item of Array.isArray(content) ? content : []) {
      const command = item.type === 'tool_use' && SHELLS[item.name] && item.input?.command;
      if (!command || seen.has(command)) continue;
      if (SECRET.test(command)) { counts.secretShaped++; continue; }
      seen.set(command, { shell: SHELLS[item.name], command, description: item.input.description || '' });
    }
  }
}

async function main() {
  const out = arg('out');
  if (!out) throw new Error('--out is required');
  const cutoff = Date.now() - Number(arg('days', 14)) * 86400000;
  const files = recentTranscripts(path.join(os.homedir(), '.claude', 'projects'), cutoff);
  const seen = new Map();
  const counts = { unparsed: 0, secretShaped: 0 };
  for (const file of files) await shellCalls(file, seen, counts);
  const hash = (s) => crypto.createHash('sha1').update(s).digest('hex');
  const sample = [...seen.values()].sort((a, b) => hash(a.command).localeCompare(hash(b.command))).slice(0, Number(arg('max', 300)));
  fs.writeFileSync(out, JSON.stringify(sample.map((input, i) => ({ id: `replay-${i}`, input, expect: null }))));
  console.log(`files=${files.length} unique=${seen.size} dropped-secret-shaped=${counts.secretShaped} unparsed-lines=${counts.unparsed} sampled=${sample.length}`);
}

main();
