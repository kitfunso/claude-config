#!/usr/bin/env node
/**
 * PreToolUse hook for Bash commands.
 * - Blocks `npm run dev` / `npm start` outside tmux (hangs the session)
 * - Warns before `git push --force` to main/master
 * - Warns before destructive commands (rm -rf, git reset --hard)
 */
const fs = require('fs');
let record = () => {};
try { ({ record } = require('./lib/record-component')); } catch (e) { /* recorder missing: keep denying */ }

function main() {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { input += chunk; });
  process.stdin.on('end', () => {
    // Modern PreToolUse output shape (same as commit-msg-guard.js):
    // silent exit 0 = allow; hookSpecificOutput.permissionDecision for deny/ask.
    // The old {decision:"allow"} shape fails hook schema validation on every call.
    let payload = {};
    const emit = (permissionDecision, reason) => {
      if (permissionDecision === 'deny') {
        record({
          kind: 'hook',
          name: 'pre-bash-guard.js',
          sessionId: payload.session_id,
          cwd: payload.cwd,
          blocked: 1,
          notes: reason,
        });
      }
      process.stdout.write(JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision,
          permissionDecisionReason: reason,
        },
      }));
      process.exit(0);
    };
    try {
      const data = JSON.parse(input);
      payload = data;
      const cmd = (data.tool_input?.command || '').trim();

      // Block dev servers outside tmux (they hang the session)
      if (/\b(npm run dev|npm start|yarn dev|pnpm dev|next dev|uvicorn .* --reload)\b/.test(cmd)) {
        if (!process.env.TMUX) {
          emit('deny', 'Dev servers hang the session. Use `run_in_background: true` or run in a separate terminal/tmux.');
        }
      }

      // Warn on force push to main/master
      if (/git push.*--force.*\b(main|master)\b/.test(cmd) || /git push.*\b(main|master)\b.*--force/.test(cmd)) {
        emit('deny', 'Force pushing to main/master is dangerous. Use a feature branch instead.');
      }

      // Warn on destructive commands
      if (/\brm\s+-rf\s+[\/~]/.test(cmd) || /git reset --hard/.test(cmd) || /git clean -fd/.test(cmd)) {
        emit('ask', `Destructive command detected: "${cmd.substring(0, 80)}". Confirm before proceeding.`);
      }

      // Allow everything else: silent exit 0, no output
      process.exit(0);
    } catch (e) {
      // On error, don't block
      process.exit(0);
    }
  });
}

main();
