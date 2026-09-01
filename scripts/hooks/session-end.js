#!/usr/bin/env node
/**
 * Stop hook that persists session summary to ~/.claude/sessions/.
 *
 * Extracts key info from the transcript:
 * - Last 10 user messages (what was worked on)
 * - Files modified
 * - Tools used
 *
 * Uses marker-based idempotent updates so repeated invocations are safe.
 */
const fs = require('fs');
const path = require('path');
const os = require('os');

const SESSIONS_DIR = path.join(os.homedir(), '.claude', 'sessions');
const SUMMARY_START = '<!-- ECC:SUMMARY:START -->';
const SUMMARY_END = '<!-- ECC:SUMMARY:END -->';

function main() {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { input += chunk; });
  process.stdin.on('end', () => {
    try {
      const data = JSON.parse(input);
      const transcriptPath = data.transcript_path;

      if (!transcriptPath || !fs.existsSync(transcriptPath)) {
        process.exit(0);
      }

      // Ensure sessions directory exists
      if (!fs.existsSync(SESSIONS_DIR)) {
        fs.mkdirSync(SESSIONS_DIR, { recursive: true });
      }

      // Parse transcript (JSONL format)
      const content = fs.readFileSync(transcriptPath, 'utf8');
      const lines = content.split('\n').filter(l => l.trim());

      const userMessages = [];
      const toolsUsed = new Set();
      const filesModified = new Set();

      for (const line of lines) {
        try {
          const entry = JSON.parse(line);
          const msg = entry.message || entry;

          // Extract user messages
          if (msg.type === 'user' || msg.role === 'user') {
            const rawContent = msg.content;
            const text = Array.isArray(rawContent)
              ? rawContent.map(c => (c && c.text) || '').join(' ')
              : (typeof rawContent === 'string' ? rawContent : '');
            if (text.trim()) {
              userMessages.push(text.trim().substring(0, 200));
            }
          }

          // Extract tool usage
          if (msg.type === 'tool_use' || msg.tool_name) {
            const toolName = msg.tool_name || msg.name || '';
            if (toolName) toolsUsed.add(toolName);
          }

          // Extract file paths from tool inputs
          if (msg.tool_input) {
            const input = msg.tool_input;
            if (input.file_path) filesModified.add(input.file_path);
            if (input.path) filesModified.add(input.path);
          }
        } catch (e) {
          // Skip unparseable lines
        }
      }

      if (userMessages.length === 0) {
        process.exit(0);
      }

      // Build session file
      const now = new Date();
      const dateStr = now.toISOString().split('T')[0];
      const timeStr = now.toTimeString().substring(0, 5);
      const sessionId = (process.env.CLAUDE_SESSION_ID || `${process.ppid}`).substring(0, 8);
      const filename = `${dateStr}-${sessionId}-session.md`;
      const filepath = path.join(SESSIONS_DIR, filename);

      // Build summary block
      const lastMessages = userMessages.slice(-10);
      const summaryBlock = [
        SUMMARY_START,
        '## Session Summary',
        '### Tasks',
        ...lastMessages.map(m => `- ${m}`),
        '### Files Modified',
        ...[...filesModified].slice(0, 20).map(f => `- ${f}`),
        '### Tools Used',
        [...toolsUsed].join(', '),
        `### Stats`,
        `- Total user messages: ${userMessages.length}`,
        SUMMARY_END
      ].join('\n');

      // Idempotent update: replace between markers or create new
      if (fs.existsSync(filepath)) {
        let existing = fs.readFileSync(filepath, 'utf8');
        if (existing.includes(SUMMARY_START) && existing.includes(SUMMARY_END)) {
          const regex = new RegExp(
            escapeRegExp(SUMMARY_START) + '[\\s\\S]*?' + escapeRegExp(SUMMARY_END)
          );
          existing = existing.replace(regex, summaryBlock);
          fs.writeFileSync(filepath, existing);
        } else {
          fs.appendFileSync(filepath, '\n' + summaryBlock + '\n');
        }
      } else {
        const template = [
          `# Session: ${dateStr}`,
          `**Date:** ${dateStr}`,
          `**Started:** ${timeStr}`,
          `**Last Updated:** ${timeStr}`,
          '',
          summaryBlock,
          '',
          '### Notes for Next Session',
          '- ',
          ''
        ].join('\n');
        fs.writeFileSync(filepath, template);
      }

    } catch (e) {
      // Never fail the session
    }
  });
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

main();
