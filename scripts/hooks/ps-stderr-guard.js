#!/usr/bin/env node
// PreToolUse guard for the PowerShell tool.
// Denies commands containing `2>&1`: PowerShell 5.1 wraps each stderr line
// from a native executable in a NativeCommandError ErrorRecord and reports
// failure even when the exe exited 0 (git prints progress to stderr, so git
// flows are the classic victim). Measured 2026-07-18 via Mirror: 21 incidents,
// 9.1% of all PowerShell tool errors, despite a prose warning in the tool docs.
// stderr is already captured by the harness; run the command bare, or use the
// Bash tool when stream routing is genuinely needed.
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
  if (input.tool_name !== 'PowerShell') process.exit(0);
  const cmd = (input.tool_input && input.tool_input.command) || '';

  if (/2>\s*&\s*1/.test(cmd)) {
    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'deny',
          permissionDecisionReason:
            'ps-stderr-guard: 2>&1 in PowerShell 5.1 wraps native-exe stderr in NativeCommandError and reports failure even on exit 0 (21 measured incidents). stderr is already captured - run the command bare, or use the Bash tool if you need stream routing.',
        },
      }),
    );
    process.exit(0);
  }

  process.exit(0);
});
