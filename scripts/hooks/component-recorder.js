#!/usr/bin/env node

const { record } = require('./lib/record-component');

const KINDS = {
  Skill: (ti) => ['skill', ti.skill],
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
  }
  process.exit(0);
});
