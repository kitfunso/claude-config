#!/usr/bin/env node
/**
 * Stop hook.
 * After the assistant finishes a turn, scan the last assistant message in the
 * transcript. If it contains markers that should have triggered a
 * <verification>, <diagnosis>, or <cost-calculus> artifact and the artifact
 * is missing, append to a session violation log and emit a system message
 * that the next turn will see.
 */
const fs = require('fs');
const path = require('path');

function main() {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { input += chunk; });
  process.stdin.on('end', () => {
    try {
      const data = JSON.parse(input);
      const transcriptPath = data.transcript_path;
      if (!transcriptPath || !fs.existsSync(transcriptPath)) return process.exit(0);

      const lines = fs.readFileSync(transcriptPath, 'utf8').trim().split('\n');
      let assistantText = '';
      for (let i = lines.length - 1; i >= 0; i--) {
        try {
          const obj = JSON.parse(lines[i]);
          if (obj.type === 'assistant' || obj.role === 'assistant') {
            const content = obj.message?.content || obj.content || '';
            assistantText = typeof content === 'string'
              ? content
              : Array.isArray(content)
                ? content.filter(c => c.type === 'text').map(c => c.text).join('\n')
                : JSON.stringify(content);
            break;
          }
        } catch {}
      }
      if (!assistantText) return process.exit(0);

      const violations = [];

      // Verification artifact required
      const namedEntityRe = /\b(Marshall Wace|Tudor Investment|Millennium|Valent Asset Management|Blenheim Capital|Brevan Howard|Soros Fund|Graham Capital|Citadel|DE Shaw|Bridgewater|Two Sigma|Renaissance|Point72|Balyasny)\b/i;
      const firmStructureRe = /\b[A-Z][a-z]+ (Asset Management|Capital|Fund|Holdings|Partners|Advisors)\b/;
      if ((namedEntityRe.test(assistantText) || firmStructureRe.test(assistantText)) && !assistantText.includes('<verification>')) {
        violations.push('Named financial entity referenced without <verification> block');
      }

      // Diagnosis artifact required for fix-it tasks
      const fixItRe = /\b(I'll fix|let me fix|wiring up|hooking up|making it work)\b/i;
      if (fixItRe.test(assistantText) && /\.(py|ts|js|tsx|jsx)\b/.test(assistantText) && !assistantText.includes('<diagnosis>')) {
        violations.push('Fix-it language with code refs but no <diagnosis> block');
      }

      // Cost-calculus required for non-trivial tasks
      const nonTrivialRe = /\b(I'll (build|implement|refactor|redesign|migrate|rebuild)|let me (build|implement|refactor|redesign|migrate|rebuild))\b/i;
      if (nonTrivialRe.test(assistantText) && !assistantText.includes('<cost-calculus>')) {
        violations.push('Non-trivial task starting without <cost-calculus> block');
      }

      if (violations.length > 0) {
        const home = process.env.USERPROFILE || process.env.HOME;
        const logPath = path.join(home, '.claude', 'sessions', 'rule-violations.log');
        try {
          fs.mkdirSync(path.dirname(logPath), { recursive: true });
          const entry = `${new Date().toISOString()}\t${(data.session_id || 'unknown')}\t${violations.join(' | ')}\n`;
          fs.appendFileSync(logPath, entry);
        } catch {}

        process.stdout.write(JSON.stringify({
          decision: 'continue',
          systemMessage: `[RULE VIOLATIONS DETECTED IN PRIOR TURN]\n${violations.map(v => '- ' + v).join('\n')}\nNext reply: include the missing artifact OR re-draft to remove the unsourced claim.`
        }));
      }
      process.exit(0);
    } catch (e) {
      process.exit(0);
    }
  });
}

main();
