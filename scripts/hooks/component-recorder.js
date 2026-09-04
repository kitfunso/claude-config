#!/usr/bin/env node
// PostToolUse recorder: one component_outcomes row per Skill or Agent call.
// Never blocks; a recorder that breaks a tool call is worse than no recorder.

const { record } = require('./lib/record-component');

const KINDS = {
  Skill: (ti) => ['skill', ti.skill],
  // No subagent_type means the tool ran general-purpose; 14% of live calls omit it.
  Agent: (ti) => ['agent', ti.subagent_type || 'general-purpose'],
};

function handle(input) {
  const resolve = KINDS[input && input.tool_name];
  if (!resolve || !input.tool_input) return;

  const [kind, name] = resolve(input.tool_input);
  record({ kind, name, sessionId: input.session_id, cwd: input.cwd });
}

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  try {
    handle(JSON.parse(raw));
  } catch {
    // Swallowed on purpose: every failure here must still exit 0.
  }
  process.exit(0);
});
