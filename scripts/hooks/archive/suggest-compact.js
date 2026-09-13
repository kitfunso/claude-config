#!/usr/bin/env node
/**
 * PostToolUse hook that tracks tool call count per session.
 * Suggests /compact at logical intervals (every ~50 tool calls).
 *
 * Based on ECC's strategic-compact pattern: compact at phase transitions,
 * not mid-implementation.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

const THRESHOLD = parseInt(process.env.COMPACT_THRESHOLD || '50', 10);
const REMINDER_INTERVAL = 25;

function main() {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { input += chunk; });
  process.stdin.on('end', () => {
    try {
      // Use session ID from env or fallback to PID-based
      const sessionId = process.env.CLAUDE_SESSION_ID || `session-${process.ppid}`;
      const counterDir = path.join(os.tmpdir(), 'claude-compact-counters');
      const counterFile = path.join(counterDir, sessionId);

      // Ensure directory exists
      if (!fs.existsSync(counterDir)) {
        fs.mkdirSync(counterDir, { recursive: true });
      }

      // Read and increment counter (fd-based to reduce race window)
      let count = 1;
      try {
        const fd = fs.openSync(counterFile, 'a+');
        try {
          const buf = Buffer.alloc(64);
          const bytesRead = fs.readSync(fd, buf, 0, 64, 0);
          if (bytesRead > 0) {
            const parsed = parseInt(buf.toString('utf8', 0, bytesRead).trim(), 10);
            count = (Number.isFinite(parsed) && parsed > 0 && parsed <= 1000000)
              ? parsed + 1
              : 1;
          }
          fs.ftruncateSync(fd, 0);
          fs.writeSync(fd, String(count), 0);
        } finally {
          fs.closeSync(fd);
        }
      } catch (e) {
        // Silently continue if counter fails
      }

      // Suggest compaction at threshold and every REMINDER_INTERVAL after
      if (count === THRESHOLD) {
        const msg = {
          systemMessage: `[Strategic Compact] ${THRESHOLD} tool calls reached. Consider /compact if you're transitioning between phases (research→planning, planning→implementation). Don't compact mid-implementation.`
        };
        process.stdout.write(JSON.stringify(msg));
      } else if (count > THRESHOLD && (count - THRESHOLD) % REMINDER_INTERVAL === 0) {
        const msg = {
          systemMessage: `[Strategic Compact] ${count} tool calls. Good checkpoint for /compact if context is getting stale.`
        };
        process.stdout.write(JSON.stringify(msg));
      }
    } catch (e) {
      // Never block on error
    }
  });
}

main();
