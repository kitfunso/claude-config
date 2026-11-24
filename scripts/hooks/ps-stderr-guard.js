#!/usr/bin/env node

let record = () => {};
try { ({ record } = require('./lib/record-component')); } catch (e) {}

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
    const reason =
      'ps-stderr-guard: 2>&1 in PowerShell 5.1 wraps native-exe stderr in NativeCommandError and reports failure even on exit 0 (21 measured incidents). stderr is already captured - run the command bare, or use the Bash tool if you need stream routing.';
    record({
      kind: 'hook',
      name: 'ps-stderr-guard.js',
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
  }

  process.exit(0);
});
