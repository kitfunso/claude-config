#!/usr/bin/env node
const fs = require('fs');
let record = () => {};
try { ({ record } = require('./lib/record-component')); } catch (e) {}
let devrlDenial = () => null;
try { ({ devrlDenial } = require('./lib/devrl-episode-guard')); } catch (e) { process.stderr.write(`devrl episode guard off: ${e.message}\n`); }

function unboundedPoll(cmd) {
  if (!/\b(until|while)\s+(?!(IFS=\S*\s+)?read\b)[^]*?\bdo\b[^]*?\bsleep\b/.test(cmd)) return false;
  return !/\btimeout\s+(-\S+\s+)*\d|\bSECONDS\b|\bdeadline\b|\s-(lt|le|gt|ge)\s/.test(cmd);
}

function main() {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { input += chunk; });
  process.stdin.on('end', () => {
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

      if (/\b(npm run dev|npm start|yarn dev|pnpm dev|next dev|uvicorn .* --reload)\b/.test(cmd)) {
        const backgrounded = data.tool_input && data.tool_input.run_in_background === true;
        if (!process.env.TMUX && !backgrounded) {
          emit('deny', 'Dev servers hang the session. Use `run_in_background: true` or run in a separate terminal/tmux.');
        }
      }

      if (unboundedPoll(cmd)) {
        emit('deny', 'This until/while loop sleeps with no deadline, so it runs forever if the job it waits on dies. '
          + "Bound it: `timeout 3600 bash -c 'until ...; do sleep 5; done'`, or add `[ $SECONDS -lt 3600 ]` to the condition.");
      }

      if (/git push.*--force.*\b(main|master)\b/.test(cmd) || /git push.*\b(main|master)\b.*--force/.test(cmd)) {
        emit('deny', 'Force pushing to main/master is dangerous. Use a feature branch instead.');
      }

      try {
        const reason = devrlDenial(cmd, data.session_id);
        if (reason) emit('deny', reason);
      } catch (e) {
        process.stderr.write(`devrl episode guard skipped: ${e.message}\n`);
      }

      if (/\brm\s+-rf\s+[\/~]/.test(cmd) || /git reset --hard/.test(cmd) || /git clean -fd/.test(cmd)) {
        emit('ask', `Destructive command detected: "${cmd.substring(0, 80)}". Confirm before proceeding.`);
      }

      process.exit(0);
    } catch (e) {
      process.exit(0);
    }
  });
}

main();
