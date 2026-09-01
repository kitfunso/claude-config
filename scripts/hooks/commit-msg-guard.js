#!/usr/bin/env node
// PreToolUse guard for git commit commands (Bash + PowerShell tools).
// Denies when:
//   1. the command text contains an em dash (U+2014): banned in commit
//      messages per Stop Slop; recurred across E2/E3/E4 ship episodes.
//   2. (PowerShell only) the command pipes stdin into git commit: PowerShell
//      pipes prepend a UTF-8 BOM to the message subject. Use the Write tool
//      to create a message file and pass `git commit -F <file>` instead.
// Scope: inline command text only; cannot inspect -F file contents.
// Emits modern PreToolUse permissionDecision JSON; silent exit 0 = allow.

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
  if (!/git\s+commit\b/.test(cmd)) process.exit(0);

  const deny = (reason) => {
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

  if (tool === 'PowerShell' && /\|\s*git\s+commit\b/.test(cmd)) {
    deny(
      'commit-msg-guard: piping into git commit from PowerShell prepends a UTF-8 BOM to the message subject. Write the message to a file with the Write tool and use: git commit -F <file>.',
    );
    return;
  }

  process.exit(0);
});
