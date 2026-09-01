#!/usr/bin/env node
/**
 * UserPromptSubmit hook: capability existence check.
 *
 * Scans the user prompt for /slash-command references. For each token that
 * resolves to an installed skill directory (~/.claude/skills/<name>/ or a
 * project .claude/skills/<name>/), injects a reminder that the skill EXISTS,
 * so the model cannot claim it is unavailable nor silently substitute its own
 * plan.
 *
 * Match on DIRECTORY existence, not the manifest filename — gstack skills vary
 * the case (project-scaffold/skill.md vs office-hours/SKILL.md), so a
 * SKILL.md-based check produces false negatives.
 *
 * Fail-open: any error exits 0 with no output. Fires only on real on-disk
 * matches, so it can never produce a false "this exists" signal.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

function skillDirs() {
  const cfg = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
  const dirs = [path.join(cfg, 'skills')];
  if (process.env.CLAUDE_PROJECT_DIR) {
    dirs.push(path.join(process.env.CLAUDE_PROJECT_DIR, '.claude', 'skills'));
  }
  try { dirs.push(path.join(process.cwd(), '.claude', 'skills')); } catch (e) {}
  return [...new Set(dirs)];
}

function resolveSkill(token, dirs) {
  // Strip a plugin namespace prefix (plugin:skill -> skill).
  const name = token.includes(':') ? token.split(':').pop() : token;
  if (!name) return null;
  for (const d of dirs) {
    try {
      const p = path.join(d, name);
      if (fs.existsSync(p) && fs.statSync(p).isDirectory()) return p;
    } catch (e) {}
  }
  return null;
}

function main() {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', c => { input += c; });
  process.stdin.on('end', () => {
    try {
      const data = JSON.parse(input);
      const prompt = (data.prompt || data.user_prompt || '').toString();

      // /token references: a slash at a word boundary, then a skill-ish name.
      // Leading [\s(] or start-of-string avoids matching paths like src/foo or and/or.
      const tokens = new Set();
      const re = /(?:^|[\s(])\/([a-zA-Z][a-zA-Z0-9_:-]*)/g;
      let m;
      while ((m = re.exec(prompt)) !== null) tokens.add(m[1]);
      if (tokens.size === 0) { process.exit(0); }

      const dirs = skillDirs();
      const found = [];
      for (const t of tokens) {
        const p = resolveSkill(t, dirs);
        if (p) found.push({ token: t, path: p });
      }
      if (found.length === 0) { process.exit(0); }

      const reminder = [
        '',
        '[CAPABILITY EXISTS — DO NOT CLAIM OTHERWISE]',
        'The user referenced these skills, which ARE installed on disk:',
        ...found.map(f => `  /${f.token}  ->  ${f.path}`),
        'Do NOT tell the user any of these is unavailable, does not exist, or cannot be found.',
        'Invoke it via the Skill tool, or ask one scoping question. Never substitute your own',
        'plan and present it as the only option.',
        ''
      ].join('\n');

      process.stdout.write(JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'UserPromptSubmit',
          additionalContext: reminder
        }
      }));
      process.exit(0);
    } catch (e) {
      process.exit(0);  // never block on hook errors
    }
  });
}

main();
