#!/usr/bin/env node
/**
 * UserPromptSubmit hook.
 * Scans the user prompt for verifiable-entity tokens. If detected, injects a
 * [VERIFICATION ARTIFACT REQUIRED] reminder into the prompt context so the
 * model sees it as part of the user's message and sources its claims this turn.
 */
const fs = require('fs');

function main() {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { input += chunk; });
  process.stdin.on('end', () => {
    try {
      const data = JSON.parse(input);
      const prompt = (data.prompt || data.user_prompt || '').toString();

      const triggers = [];

      // Financial firm structures
      if (/\b[A-Z][a-z]+ (Asset Management|Capital|Fund|Holdings|Partners|Securities|Investments|Group|Advisors)\b/.test(prompt)) {
        triggers.push('financial firm');
      }
      // Known seed names — extend over time
      if (/\b(Marshall Wace|Tudor Investment|Millennium|Valent Asset Management|Blenheim Capital|Brevan Howard|Soros Fund|Graham Capital|Citadel|DE Shaw|Bridgewater|Two Sigma|Renaissance|Point72|Balyasny|ExodusPoint)\b/i.test(prompt)) {
        triggers.push('known financial entity');
      }
      // Person + role hint
      if (/\b(CIO|CEO|CFO|portfolio manager|head of|founder)\b/i.test(prompt) && /\b[A-Z][a-z]+\s+[A-Z][a-z]+\b/.test(prompt)) {
        triggers.push('named individual + role');
      }
      // Numeric financial claims. return/returns needs a percent marker so "return 0" (code) can't match.
      const hasNumericTerm = /\b(Sharpe|PnL|drawdown|AUM|alpha)\s*[:\-=]?\s*[-+]?\d+/i.test(prompt);
      const hasPercentReturn = /\breturns?\s*[:\-=]?\s*[-+]?\d+(?:\.\d+)?\s*(?:%|\bpercent\b)/i.test(prompt);
      if (hasNumericTerm || hasPercentReturn) {
        triggers.push('numeric financial claim');
      }
      // Verification verbs against named code paths
      if (/\b(verify|audit|is.{0,20}true|prove)\b/i.test(prompt) && /\b[\w\-/]+\.(py|js|ts|tsx|jsx|md|json)\b/.test(prompt)) {
        triggers.push('file/code verification request');
      }

      if (triggers.length > 0) {
        const reminder = [
          '',
          '[VERIFICATION ARTIFACT REQUIRED]',
          `This prompt contains verifiable entities (${triggers.join(', ')}).`,
          'Before responding:',
          '  1. Each load-bearing claim cites a tool call from THIS turn inline (file:line, URL, command).',
          '  2. A claim with no source this turn: run the tool now, before replying.',
          '  3. The <verification> block only forces a missing source; never send "not yet verified".',
          '  4. Quick-mode preference applies to output length, never investigation depth.',
          ''
        ].join('\n');

        process.stdout.write(JSON.stringify({
          hookSpecificOutput: {
            hookEventName: 'UserPromptSubmit',
            additionalContext: reminder
          }
        }));
      }
      process.exit(0);
    } catch (e) {
      process.exit(0);  // never block on hook errors
    }
  });
}

main();
