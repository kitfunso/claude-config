#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { handlersFor, runClaudeHooks } from './claude-hooks.mjs';
import { runSync } from './sync-agy.mjs';
import { chunk } from './agy-rules.mjs';

const GEMINI = process.env.NEON_GEMINI_DIR || path.join(os.homedir(), '.gemini');
const STATE = path.join(GEMINI, 'claude-bridge');
const SKILL_FILE = /[\\/]\.gemini[\\/]skills[\\/]([^\\/]+)[\\/]SKILL\.md$/i;

/** One agy tool call as the Claude tool name and input that Claude's matchers and hooks expect. agy runs commands in PowerShell 5.1. */
export function toClaude(name, args = {}) {
  switch (name) {
    case 'run_command': return { tool_name: 'PowerShell', tool_input: { command: args.CommandLine ?? '', description: args.toolSummary ?? '', ...(args.Cwd ? { cwd: args.Cwd } : {}) } };
    case 'read_file': {
      const skill = SKILL_FILE.exec(args.Path || '');
      return skill ? { tool_name: 'Skill', tool_input: { skill: skill[1] } } : { tool_name: 'Read', tool_input: { file_path: args.Path } };
    }
    case 'write_file': return { tool_name: 'Write', tool_input: { file_path: args.Path, content: args.Content ?? '' } };
    case 'edit_file': return { tool_name: 'Edit', tool_input: { file_path: args.Path, old_string: args.Target ?? '', new_string: args.Replacement ?? '' } };
    case 'search_web': return { tool_name: 'WebSearch', tool_input: { query: args.Query ?? args.query ?? '' } };
    case 'invoke_subagent': return { tool_name: 'Agent', tool_input: { prompt: args.Prompt ?? '', subagent_type: args.TypeName ?? '', description: args.Role ?? '' } };
    case 'call_mcp_tool': return { tool_name: `mcp__${args.ServerName}__${args.ToolName}`, tool_input: args.Arguments || {} };
    case 'manage_task': return { tool_name: 'TodoWrite', tool_input: args };
    default: return { tool_name: name, tool_input: args };
  }
}

const BACK = {
  run_command: { command: 'CommandLine' },
  write_file: { file_path: 'Path', content: 'Content' },
  edit_file: { file_path: 'Path', old_string: 'Target', new_string: 'Replacement' },
  read_file: { file_path: 'Path' },
};

export function toAgyArgs(name, before, updated) {
  if (name === 'call_mcp_tool') return { Arguments: { ...before, ...updated } };
  const out = {};
  for (const [k, v] of Object.entries(updated || {})) if (BACK[name]?.[k] && v !== before[k]) out[BACK[name][k]] = v;
  return Object.keys(out).length ? out : null;
}

const readSteps = (file) => {
  try { return fs.readFileSync(file, 'utf8').split('\n').filter(Boolean).flatMap((l) => { try { return [JSON.parse(l)]; } catch { return []; } }); } catch { return []; }
};
const isUser = (s) => s.type === 'USER_INPUT' && s.source === 'USER_EXPLICIT';
const userText = (s) => String(s.content || '').replace(/^\s*<USER_REQUEST>\s*/, '').replace(/\s*<\/USER_REQUEST>[\s\S]*$/, '');

export function claudeRows(steps, sessionId, cwd) {
  const rows = [];
  for (const s of steps) {
    const base = { isSidechain: false, sessionId, cwd, timestamp: s.created_at, uuid: `agy-${s.step_index}` };
    if (isUser(s)) rows.push({ ...base, type: 'user', origin: { kind: 'human' }, message: { role: 'user', content: userText(s) } });
    if (s.type !== 'PLANNER_RESPONSE') continue;
    const content = s.content ? [{ type: 'text', text: String(s.content) }] : [];
    (s.tool_calls || []).forEach((c, i) => {
      const t = toClaude(c.name, c.args);
      content.push({ type: 'tool_use', id: `agy_${s.step_index}_${i}`, name: t.tool_name, input: t.tool_input });
    });
    if (content.length) rows.push({ ...base, type: 'assistant', message: { role: 'assistant', model: s.model, content } });
  }
  return rows;
}

const cwdOf = (p) => p.cwd || p.workspacePaths?.[0] || process.cwd();
const file = (p, ext) => path.join(STATE, `${p.conversationId || 'unknown'}${ext}`);
const log = (line) => { try { fs.appendFileSync(path.join(STATE, 'bridge.log'), `${new Date().toISOString()} ${line}\n`); } catch { /* logging must never block agy */ } };

function claudeTranscript(p) {
  const steps = readSteps(p.transcriptPath);
  const out = file(p, '.jsonl');
  fs.writeFileSync(out, claudeRows(steps, p.conversationId, cwdOf(p)).map((r) => JSON.stringify(r)).join('\n') + '\n');
  return { transcript: out, steps };
}

const payload = (p, event, transcript) => ({ session_id: p.conversationId, transcript_path: transcript, cwd: cwdOf(p), hook_event_name: event, model: p.modelName });

function steps(label, texts) {
  const body = texts.filter(Boolean).join('\n\n');
  const parts = body ? chunk(body) : [];
  return parts.map((t, i) => ({ systemMessage: { systemMessage: `[${label}${parts.length > 1 ? ` part ${i + 1}/${parts.length}` : ''}]\n${t}` } }));
}

/** Tool-hook context waits here until the next model call, the first point where agy can inject it. */
function addPending(p, label, texts) {
  const body = texts.filter(Boolean).join('\n\n');
  if (body) fs.appendFileSync(file(p, '.pending'), `${JSON.stringify(`[${label}]\n${body}`)}\n`);
}

function takePending(p) {
  const f = file(p, '.pending');
  const tmp = `${f}.${process.pid}`;
  try { fs.renameSync(f, tmp); } catch { return []; }
  const out = fs.readFileSync(tmp, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
  fs.rmSync(tmp, { force: true });
  return out;
}

const loadState = (p) => { try { return JSON.parse(fs.readFileSync(file(p, '.state.json'), 'utf8')); } catch { return { users: 0, lastInput: null }; } };

function pruneState(days = 14) {
  const cut = Date.now() - days * 86_400_000;
  for (const f of fs.readdirSync(STATE)) {
    const full = path.join(STATE, f);
    if (f !== 'bridge.log' && fs.statSync(full).mtimeMs < cut) fs.rmSync(full, { force: true });
  }
}

async function onSessionStart(p) {
  try { runSync(); pruneState(); } catch (e) { log(`sync failed: ${e.message}`); }
  const { transcript } = claudeTranscript(p);
  const v = await runClaudeHooks('SessionStart', { ...payload(p, 'SessionStart', transcript), source: 'startup' }, { matchValue: 'startup' }, { cwd: cwdOf(p), capMs: 40_000 });
  return { injectSteps: steps('claude SessionStart hooks', v.context) };
}

async function onPreInvocation(p) {
  const st = loadState(p);
  const users = readSteps(p.transcriptPath).filter(isUser).length;
  const inject = [];
  let terminate = false;
  if (p.invocationNum === 0 && (users > st.users || p.lastUserInput !== st.lastInput)) {
    fs.writeFileSync(file(p, '.state.json'), JSON.stringify({ users, lastInput: p.lastUserInput }));
    const { transcript } = claudeTranscript(p);
    const v = await runClaudeHooks('UserPromptSubmit', { ...payload(p, 'UserPromptSubmit', transcript), prompt: p.lastUserInput || '' }, {}, { cwd: cwdOf(p) });
    if (v.block.length) {
      inject.push({ errorMessage: { userMessage: `A Claude hook blocked this prompt: ${v.block.join(' | ')}` } });
      terminate = true;
      log(`UserPromptSubmit blocked: ${v.block.join(' | ')}`);
    }
    inject.push(...steps('claude UserPromptSubmit hooks', v.context));
  }
  for (const t of takePending(p)) inject.push(...steps('claude hook note', [t]));
  return { injectSteps: inject, ...(terminate ? { terminationBehavior: 'terminate' } : {}) };
}

async function onPreToolUse(p) {
  const { name, args = {}, id } = p.toolCall || {};
  const t = toClaude(name, args);
  const sel = { toolName: t.tool_name, toolInput: t.tool_input };
  if (!handlersFor('PreToolUse', sel).length) return { decision: 'allow' };
  const { transcript } = claudeTranscript(p);
  const v = await runClaudeHooks('PreToolUse', { ...payload(p, 'PreToolUse', transcript), tool_name: t.tool_name, tool_input: t.tool_input, tool_use_id: id }, sel, { cwd: cwdOf(p) });
  addPending(p, `claude PreToolUse hooks on ${t.tool_name}`, v.context);
  if (v.deny.length) { log(`deny ${t.tool_name}: ${v.deny.join(' | ').slice(0, 300)}`); return { decision: 'deny', reason: v.deny.join('\n') }; }
  const overwrite = v.updatedInput ? toAgyArgs(name, t.tool_input, v.updatedInput) : null;
  return { decision: v.ask.length ? 'ask' : 'allow', ...(v.ask.length ? { reason: v.ask.join('\n') } : {}), ...(overwrite ? { overwrite } : {}) };
}

async function onPostToolUse(p) {
  const { name, args = {}, id } = p.toolCall || {};
  const t = toClaude(name, args);
  const event = p.error ? 'PostToolUseFailure' : 'PostToolUse';
  const sel = { toolName: t.tool_name, toolInput: t.tool_input };
  if (!handlersFor(event, sel).length) return {};
  const { transcript } = claudeTranscript(p);
  const extra = { tool_name: t.tool_name, tool_input: t.tool_input, tool_use_id: id, tool_response: {}, ...(p.error ? { error: p.error } : {}) };
  const v = await runClaudeHooks(event, { ...payload(p, event, transcript), ...extra }, sel, { cwd: cwdOf(p) });
  addPending(p, `claude ${event} hooks on ${t.tool_name}`, [...v.block, ...v.context]);
  return {};
}

async function onStop(p) {
  if (p.terminationReason === 'error' || !handlersFor('Stop').length) return {};
  const { transcript, steps: all } = claudeTranscript(p);
  const last = [...all].reverse().find((s) => s.type === 'PLANNER_RESPONSE' && s.content);
  const extra = { stop_hook_active: !!p.continuationActive, last_assistant_message: last ? String(last.content) : '' };
  const v = await runClaudeHooks('Stop', { ...payload(p, 'Stop', transcript), ...extra }, {}, { cwd: cwdOf(p) });
  if (!v.block.length) return {};
  log(`Stop continue: ${v.block.join(' | ').slice(0, 300)}`);
  return { decision: 'continue', reason: v.block.join('\n') };
}

const HANDLERS = { SessionStart: onSessionStart, PreInvocation: onPreInvocation, PreToolUse: onPreToolUse, PostToolUse: onPostToolUse, Stop: onStop };

async function main(event) {
  let p = {};
  try { p = JSON.parse(fs.readFileSync(0, 'utf8') || '{}'); } catch { /* empty payload: run with defaults */ }
  fs.mkdirSync(STATE, { recursive: true });
  let out = event === 'PreToolUse' ? { decision: 'allow' } : {};
  try { if (HANDLERS[event]) out = await HANDLERS[event](p); } catch (e) { log(`${event} failed, Claude hooks skipped: ${e.stack}`); }
  process.stdout.write(JSON.stringify(out));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main(process.argv[2]);
