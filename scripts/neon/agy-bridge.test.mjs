import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'agy-bridge-'));
const claudeDir = path.join(tmp, 'claude');
const geminiDir = path.join(tmp, 'gemini');
fs.mkdirSync(path.join(claudeDir, 'skills'), { recursive: true });
process.env.NEON_CLAUDE_DIR = claudeDir;
process.env.NEON_GEMINI_DIR = geminiDir;

const node = (code) => ({ type: 'command', command: 'node', args: ['-e', code], timeout: 10 });
const settings = {
  hooks: {
    PreToolUse: [
      { matcher: 'PowerShell', hooks: [node(`let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const p=JSON.parse(d);if(p.tool_input.command.includes('2>&1'))console.log(JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'no 2>&1'}}))})`)] },
      { matcher: 'Edit|Write', hooks: [node(`console.log(JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',additionalContext:'edit note'}}))`)] },
      { matcher: 'Edit|Write|Bash|PowerShell', hooks: [{ type: 'command', command: 'node', args: ['C:/x/.claude/scripts/neon/handoff.mjs', '--guard'] }] },
    ],
    PostToolUse: [{ matcher: 'Write', hooks: [{ ...node('process.exit(0)'), if: 'Write(//**/projects/*/memory/*.md)' }] }],
    UserPromptSubmit: [{ hooks: [node(`console.log('plain context line')`)] }],
    Stop: [{ hooks: [node(`let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const p=JSON.parse(d);if(!p.stop_hook_active&&/Say go/.test(p.last_assistant_message))console.log(JSON.stringify({decision:'block',reason:'do the work'}))})`)] }],
  },
};
fs.writeFileSync(path.join(claudeDir, 'settings.json'), JSON.stringify(settings));

const hooks = await import('./claude-hooks.mjs');
const bridge = await import('./agy-bridge.mjs');

test('agy tools map to Claude names and back', () => {
  assert.deepEqual(bridge.toClaude('run_command', { CommandLine: 'git status' }).tool_name, 'PowerShell');
  assert.deepEqual(bridge.toClaude('edit_file', { Path: 'a', Target: 'x', Replacement: 'y' }).tool_input, { file_path: 'a', old_string: 'x', new_string: 'y' });
  assert.deepEqual(bridge.toClaude('read_file', { Path: 'C:\\Users\\k\\.gemini\\skills\\commit\\SKILL.md' }), { tool_name: 'Skill', tool_input: { skill: 'commit' } });
  assert.equal(bridge.toClaude('call_mcp_tool', { ServerName: 'playwright', ToolName: 'browser_click', Arguments: {} }).tool_name, 'mcp__playwright__browser_click');
  const before = bridge.toClaude('edit_file', { Path: 'a', Target: 'x', Replacement: 'y' }).tool_input;
  assert.deepEqual(bridge.toAgyArgs('edit_file', before, { ...before, new_string: 'z' }), { Replacement: 'z' });
  assert.equal(bridge.toAgyArgs('invoke_subagent', {}, { model: 'sonnet' }), null);
});

test('matchers, if rules and neon handlers follow Claude', () => {
  assert.ok(hooks.matcherOk('Edit|Write', 'Write'));
  assert.ok(!hooks.matcherOk('Bash', 'PowerShell'));
  assert.ok(hooks.matcherOk('mcp__playwright__.*', 'mcp__playwright__browser_click'));
  assert.ok(hooks.ifOk('Write(//**/projects/*/memory/*.md)', 'Write', { file_path: 'C:\\Users\\k\\.claude\\projects\\C--x\\memory\\a.md' }));
  assert.ok(!hooks.ifOk('Write(//**/projects/*/memory/*.md)', 'Edit', { file_path: 'C:/k/projects/x/memory/a.md' }));
  assert.ok(hooks.ifOk('Bash(git commit:*)', 'Bash', { command: 'git commit -m x' }));
  assert.equal(hooks.handlersFor('PreToolUse', { toolName: 'Write', toolInput: {} }).length, 1, 'the neon guard is skipped');
  assert.equal(hooks.handlersFor('PostToolUse', { toolName: 'Write', toolInput: { file_path: 'C:/k/src/a.md' } }).length, 0);
});

test('merge reads deny, block, context and exit code 2', () => {
  const deny = JSON.stringify({ hookSpecificOutput: { permissionDecision: 'deny', permissionDecisionReason: 'r1' } });
  const v = hooks.merge([{ code: 0, stdout: deny }, { code: 2, stderr: 'r2', stdout: '' }, { code: 0, stdout: 'text' }], 'PreToolUse');
  assert.deepEqual(v.deny, ['r1', 'r2']);
  assert.deepEqual(v.context, []);
  assert.deepEqual(hooks.merge([{ code: 0, stdout: 'text' }], 'UserPromptSubmit').context, ['text']);
  assert.deepEqual(hooks.merge([{ code: 0, stdout: '{"decision":"block","reason":"go"}' }], 'Stop').block, ['go']);
});

test('agy steps become Claude transcript rows', () => {
  const rows = bridge.claudeRows([
    { step_index: 0, source: 'USER_EXPLICIT', type: 'USER_INPUT', content: '<USER_REQUEST>\nfix it\n</USER_REQUEST>' },
    { step_index: 1, source: 'SYSTEM_SDK', type: 'SYSTEM_MESSAGE', content: 'rules' },
    { step_index: 2, source: 'MODEL', type: 'PLANNER_RESPONSE', model: 'm', content: 'ok', tool_calls: [{ name: 'run_command', args: { CommandLine: 'ls' } }] },
  ], 'c1', 'C:/w');
  assert.equal(rows.length, 2);
  assert.equal(rows[0].message.content, 'fix it');
  assert.equal(rows[0].origin.kind, 'human');
  assert.deepEqual(rows[1].message.content.map((b) => b.type), ['text', 'tool_use']);
  assert.equal(rows[1].message.content[1].name, 'PowerShell');
});

function runBridge(event, p) {
  return JSON.parse(execFileSync('node', [path.join(HERE, 'agy-bridge.mjs'), event], { input: JSON.stringify(p), encoding: 'utf8', env: process.env }));
}

test('bridge end to end: deny, allow, context, stop', () => {
  const transcriptPath = path.join(tmp, 'agy.jsonl');
  const say = (text) => fs.writeFileSync(transcriptPath, [
    { step_index: 0, source: 'USER_EXPLICIT', type: 'USER_INPUT', content: 'go on' },
    { step_index: 1, source: 'MODEL', type: 'PLANNER_RESPONSE', content: text },
  ].map((s) => JSON.stringify(s)).join('\n'));
  say('Next is X. Say go.');
  const base = { conversationId: 'conv-1', cwd: tmp, transcriptPath };
  const tc = (name, args) => ({ ...base, toolCall: { name, args, id: 't1' } });
  assert.equal(runBridge('PreToolUse', tc('run_command', { CommandLine: 'git log 2>&1' })).decision, 'deny');
  assert.deepEqual(runBridge('PreToolUse', tc('run_command', { CommandLine: 'git log' })), { decision: 'allow' });
  assert.deepEqual(runBridge('PreToolUse', tc('read_file', { Path: 'x' })), { decision: 'allow' });
  runBridge('PreToolUse', tc('write_file', { Path: 'x', Content: 'y' }));
  const pre = runBridge('PreInvocation', { ...base, invocationNum: 0, lastUserInput: 'go on' });
  const texts = pre.injectSteps.map((s) => s.systemMessage.systemMessage).join('\n');
  assert.match(texts, /plain context line/);
  assert.match(texts, /edit note/);
  assert.equal(runBridge('PreInvocation', { ...base, invocationNum: 1, lastUserInput: 'go on' }).injectSteps.length, 0, 'prompt hooks run once per prompt');
  assert.deepEqual(runBridge('Stop', { ...base, continuationActive: false, terminationReason: 'model_stop' }), { decision: 'continue', reason: 'do the work' });
  assert.deepEqual(runBridge('Stop', { ...base, continuationActive: true, terminationReason: 'model_stop' }), {});
  say('Done: shipped.');
  assert.deepEqual(runBridge('Stop', { ...base, continuationActive: false, terminationReason: 'model_stop' }), {});
});
