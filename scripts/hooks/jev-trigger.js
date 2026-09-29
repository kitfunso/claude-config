#!/usr/bin/env node
// UserPromptSubmit + PreToolUse(Edit|Write) hook: tells the model to load /jev when Jev work starts.
// Notice only, never blocks; once per session per trigger; fails open on any error.
const fs = require('fs');
const os = require('os');
const path = require('path');

const JEV_WORDS = /\bjev\b|typesafe|\bnoul\b|system[ -]?one|TYPESAFE_API_KEY|jev-packs|jev-bench/i;
const LLM_CALL = /messages\.create|chat\.completions|responses\.create|generateText|generateObject|anthropic\s*\(|new\s+(Anthropic|OpenAI)\b|claude\s+-p\b|\/v1\/messages|ollama\.(chat|generate)/;
const DECISION = /\b(classif\w*|route|routing|relevan\w*|grade|grading|judge|is_\w+|yes\/no|true\/false|pick\w*|filter\w*|triage|gate|should_\w+|label\w*)\b/i;
const CODE_EXT = /\.(js|mjs|cjs|ts|tsx|py|go|rs|rb|java|kt|cs|sh|ps1)$/i;

const LOAD = 'Load the /jev skill with the Skill tool now (and /typesafe-ai for API shape) before writing or changing this.';
const PROMPT_NOTICE = `[JEV] This prompt is about TypeSafe Jev. ${LOAD} It holds our measured rules: when Jev beats a free baseline, the question-writing lint, the labelled bench, and the go-live rule.`;
const CALL_NOTICE = (f) => `[JEV] This edit writes a Jev/TypeSafe call in ${f}. ${LOAD} Check the pack lint, fail-open client shape and secret scrub from the skill before saving.`;
const DECIDE_NOTICE = (f) => `[JEV] This edit adds an LLM call that makes a yes/no, pick or grade decision in ${f}. Load /jev with the Skill tool and apply its section 1 test: if Jev can replace this call, say so in one line; if not, carry on. Text generation stays with the LLM.`;

function editedText(input) {
  const ti = (input && input.tool_input) || {};
  if (typeof ti.content === 'string') return ti.content;
  if (typeof ti.new_string === 'string') return ti.new_string;
  if (Array.isArray(ti.edits)) return ti.edits.map((e) => e.new_string || '').join('\n');
  return '';
}

function firstTime(markerDir, sessionId, key) {
  const safe = `${sessionId}__${key}`.replace(/[^A-Za-z0-9_-]/g, '_').slice(0, 200);
  const p = path.join(markerDir, safe);
  if (fs.existsSync(p)) return false;
  fs.mkdirSync(markerDir, { recursive: true });
  fs.writeFileSync(p, '');
  return true;
}

function decide(input, opts) {
  const env = (opts && opts.env) || process.env;
  if (env.CLAUDE_JEV_TRIGGER === 'off') return null;
  const markerDir = (opts && opts.markerDir) || path.join(os.tmpdir(), 'claude-jev-trigger');
  const sessionId = String((input && input.session_id) || 'unknown');
  const event = (input && input.hook_event_name) || (input && input.tool_name ? 'PreToolUse' : 'UserPromptSubmit');

  if (event === 'UserPromptSubmit') {
    const prompt = String((input && (input.prompt || input.user_prompt)) || '');
    if (!JEV_WORDS.test(prompt)) return null;
    return firstTime(markerDir, sessionId, 'prompt') ? { event, text: PROMPT_NOTICE } : null;
  }

  const file = String(((input && input.tool_input) || {}).file_path || '');
  // The skill's own files and its scripts discuss Jev by design.
  if (/[\\/]\.claude[\\/](skills[\\/](jev|typesafe-ai)|scripts[\\/]jev-)/i.test(file)) return null;
  const text = editedText(input);
  if (!text || !CODE_EXT.test(file)) return null;
  const base = path.basename(file);
  if (JEV_WORDS.test(text)) {
    return firstTime(markerDir, sessionId, `call_${file}`) ? { event, text: CALL_NOTICE(base) } : null;
  }
  if (LLM_CALL.test(text) && DECISION.test(text)) {
    return firstTime(markerDir, sessionId, `decide_${file}`) ? { event, text: DECIDE_NOTICE(base) } : null;
  }
  return null;
}

function main() {
  let raw = '';
  process.stdin.on('data', (d) => (raw += d));
  process.stdin.on('end', () => {
    try {
      const out = decide(JSON.parse(raw), {});
      if (out) {
        process.stdout.write(JSON.stringify({
          hookSpecificOutput: { hookEventName: out.event, additionalContext: out.text },
        }));
      }
    } catch (e) {
      // bad stdin or fs error: stay silent, never block the prompt or the edit
    }
    process.exit(0);
  });
}

if (require.main === module) main();

module.exports = { decide };
