#!/usr/bin/env node

let record = () => {};
try { ({ record } = require('./lib/record-component')); } catch (e) { /* recorder missing: keep denying */ }

const GIT_COMMIT = /\bgit\b[^|&;]*\bcommit\b/;
const PIPED_COMMIT = /\|\s*git\b[^|&;]*\bcommit\b/;

let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.exit(0);
  }
  const cmd = (input.tool_input && input.tool_input.command) || '';
  const tool = input.tool_name || '';
  if (!GIT_COMMIT.test(cmd)) process.exit(0);

  const deny = (reason) => {
    record({
      kind: 'hook',
      name: 'commit-msg-guard.js',
      sessionId: input.session_id,
      cwd: input.cwd,
      blocked: 1,
      notes: reason,
    });
    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'deny',
          permissionDecisionReason: reason,
        },
      }),
    );
    process.exit(0);
  };

  if (cmd.includes('—')) {
    deny(
      'commit-msg-guard: command contains an em dash (U+2014), banned in commit messages per Stop Slop. Replace it with a hyphen, colon, or comma and retry.',
    );
    return;
  }

  if (tool === 'PowerShell' && PIPED_COMMIT.test(cmd)) {
    deny(
      'commit-msg-guard: piping into git commit from PowerShell prepends a UTF-8 BOM to the message subject. Write the message to a file with the Write tool and use: git commit -F <file>.',
    );
    return;
  }

  process.exit(0);
});
