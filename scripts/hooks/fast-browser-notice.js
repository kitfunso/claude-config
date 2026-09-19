#!/usr/bin/env node
// PreToolUse hook: shows the fast browser command on the first browser tool call per session.
// Notice only, never permissionDecision; fails open on any error.
const fs = require('fs');
const os = require('os');
const path = require('path');

const RUN = 'uv run --project C:/Users/skf_s/tools/jev-ultrafast python C:/Users/skf_s/.claude/scripts/fast_browser.py --url "<URL>" --goal "<goal>" --say "<exact text to type>"';
const NOTICE = `[FAST BROWSER] A faster browser route is installed. For a plain click-and-type task on a normal web page, run ONE shell call instead of stepping this tool: ${RUN}. Pass one --say per field that needs typing; the route never writes text itself. No password, key or other secret in --goal or --say: both are sent to TypeSafe. It prints a JSON line per step, then a last line with status and page_text (the first 2,000 characters of the final page). Its tab closes when it ends, so check the outcome from page_text; DONE is a claim, not proof. BLOCKED, MAX_STEPS, ERROR or NO_KEY: carry on with this tool. Use this tool for the whole task when it pages through results with a Next link, ends in a submit, pay, publish or send click, needs a login, or involves screenshots, frames, canvas, file uploads or pop-up tabs. Never point it at RamSky. Shown once per session.`;

function decide(input, opts) {
  const env = (opts && opts.env) || process.env;
  if (env.CLAUDE_FAST_BROWSER_NOTICE === 'off') return null;

  const toolName = (input && input.tool_name) || '';
  if (!/^mcp__(claude-in-chrome|playwright)__/.test(toolName)) return null;

  const launcherPath = (opts && opts.launcherPath) || path.join(os.homedir(), '.claude', 'scripts', 'fast_browser.py');
  if (!fs.existsSync(launcherPath)) return null;

  const sessionId = String((input && input.session_id) || 'unknown').replace(/[^A-Za-z0-9_-]/g, '_');
  const markerDir = (opts && opts.markerDir) || path.join(os.tmpdir(), 'claude-fast-browser');
  const markerPath = path.join(markerDir, sessionId);
  if (fs.existsSync(markerPath)) return null;

  fs.mkdirSync(markerDir, { recursive: true });
  fs.writeFileSync(markerPath, '');
  return NOTICE;
}

function main() {
  let raw = '';
  process.stdin.on('data', (d) => (raw += d));
  process.stdin.on('end', () => {
    try {
      const notice = decide(JSON.parse(raw), {});
      if (notice) {
        process.stdout.write(JSON.stringify({
          hookSpecificOutput: { hookEventName: 'PreToolUse', additionalContext: notice },
        }));
      }
    } catch (e) {
      // bad stdin or fs error: stay silent, never break the browser call
    }
    process.exit(0);
  });
}

if (require.main === module) main();

module.exports = { decide, NOTICE };
