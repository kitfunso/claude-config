// Reads a Claude Code transcript (JSONL, can be 500 MB) in one streamed pass and keeps only what a handoff brief needs.
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';

export const GRACE_TEXT = '[Usage limit reached; a short grace allowance remains';
export const RESET_TEXT = 'usage limit has reset';
const LIMIT_RE = /hit your (?:session |weekly |usage )?limit/i;
const NOT_KEITH = ['<task-notification>', '<command-', '<local-command-', '<bash-', '<system-reminder>'];
const EDIT_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit']);

export const isLimitText = (text) => LIMIT_RE.test(text || '');

export function findTranscript(claudeDir, sessionId) {
  const root = path.join(claudeDir, 'projects');
  for (const dir of fs.readdirSync(root)) {
    const file = path.join(root, dir, `${sessionId}.jsonl`);
    if (fs.existsSync(file)) return file;
  }
  return null;
}

/** Last `bytes` of the file as parsed lines; the first partial line is dropped. */
export function readTail(file, bytes = 256 * 1024) {
  const { size } = fs.statSync(file);
  const start = Math.max(0, size - bytes);
  const fd = fs.openSync(file, 'r');
  try {
    const buf = Buffer.alloc(size - start);
    fs.readSync(fd, buf, 0, buf.length, start);
    const lines = buf.toString('utf8').split('\n');
    if (start > 0) lines.shift();
    return lines.map(parse).filter(Boolean);
  } finally {
    fs.closeSync(fd);
  }
}

function parse(line) {
  try { return line ? JSON.parse(line) : null; } catch { return null; }
}

export function keithPromptText(o) {
  if (o?.type !== 'user' || o.isMeta || o.isCompactSummary) return null;
  const c = o.message?.content;
  if (typeof c !== 'string') return null;
  const t = c.trimStart();
  return NOT_KEITH.some((p) => t.startsWith(p)) ? null : c;
}

/** Limit state from parsed lines in order: is there a limit signal after Keith's last prompt? */
export function limitState(lines) {
  let lastPrompt = -1, lastLimit = -1, lastReset = -1, limitText = '';
  lines.forEach((o, i) => {
    if (keithPromptText(o) !== null) lastPrompt = i;
    const raw = textOf(o);
    if (raw.includes(GRACE_TEXT) || (o.isApiErrorMessage && isLimitText(raw))) { lastLimit = i; limitText = raw; }
    if (o.isMeta && raw.includes(RESET_TEXT)) lastReset = i;
  });
  const hit = lastLimit > lastReset;
  return { hit, working: hit && lastLimit > lastPrompt, limitText: hit ? limitText.slice(0, 300) : '' };
}

function textOf(o) {
  const c = o?.message?.content;
  if (typeof c === 'string') return c;
  if (Array.isArray(c)) return c.map((b) => (b.type === 'text' ? b.text : '')).join('\n');
  return '';
}

const push = (arr, item, max) => { arr.push(item); if (arr.length > max) arr.shift(); };

/** One streamed pass. Cheap substring checks gate every JSON.parse. */
export async function scanTranscript(file) {
  const s = {
    prompts: [], texts: [], edits: [], commands: [], cwds: [], todos: null,
    permissionMode: null, jobs: new Map(), doneJobs: new Set(), ordered: [],
  };
  const rl = readline.createInterface({ input: fs.createReadStream(file, { encoding: 'utf8' }), crlfDelay: Infinity });
  for await (const line of rl) {
    const cwd = grab(line, 'cwd');
    if (cwd) noteCwd(s.cwds, cwd);
    s.permissionMode = grab(line, 'permissionMode') || s.permissionMode;
    if (line.includes('"type":"user"')) userLine(s, line);
    else if (line.includes('"type":"assistant"')) assistantLine(s, line);
  }
  for (const id of s.doneJobs) s.jobs.delete(id);
  return { ...s, jobs: [...s.jobs.values()], limit: limitState(s.ordered) };
}

/** Top-level keys sit after `message`, so take the last unescaped `"key":"` in the line. */
function grab(line, key) {
  const i = line.lastIndexOf(`"${key}":"`);
  if (i === -1) return null;
  const m = /^"((?:[^"\\]|\\.)*)"/.exec(line.slice(i + key.length + 3, i + key.length + 3 + 2000));
  try { return m ? JSON.parse(`"${m[1]}"`) : null; } catch { return null; }
}

function noteCwd(cwds, cwd) {
  const i = cwds.indexOf(cwd);
  if (i !== -1) cwds.splice(i, 1);
  push(cwds, cwd, 30);
}

function userLine(s, line) {
  const isString = line.includes('"role":"user","content":"');
  if (!isString) settleForegroundAgents(s, line);
  if (!isString && !line.includes(RESET_TEXT)) return;
  const o = parse(line);
  if (!o) return;
  const text = keithPromptText(o);
  if (text !== null) {
    push(s.prompts, { at: o.timestamp, text: text.length > 2000 ? `${text.slice(0, 2000)} …[cut]` : text }, 20);
    push(s.ordered, o, 400);
    return;
  }
  const raw = textOf(o);
  if (raw.startsWith('<task-notification>')) {
    const id = /<tool-use-id>([^<]+)</.exec(raw);
    if (id) s.doneJobs.add(id[1]);
  }
  if (o.isMeta && raw.includes(RESET_TEXT)) push(s.ordered, o, 400);
  if (raw.includes(GRACE_TEXT)) push(s.ordered, o, 400);
}

/** A foreground sub-agent ends with its tool_result; a background one only says it launched. */
function settleForegroundAgents(s, line) {
  for (const job of s.jobs.values()) {
    if (job.kind !== 'sub-agent' || job.launched || !line.includes(`"tool_use_id":"${job.id}"`)) continue;
    if (/launched successfully|running in the background/i.test(line.slice(0, 20000))) job.launched = true;
    else s.doneJobs.add(job.id);
  }
}

function assistantLine(s, line) {
  const wanted = line.includes('"type":"text"') || line.includes('"type":"tool_use"') || line.includes('isApiErrorMessage');
  if (!wanted) return;
  const o = parse(line);
  if (!o) return;
  if (o.isApiErrorMessage) { push(s.ordered, o, 400); return; }
  for (const b of o.message?.content || []) {
    if (b.type === 'text' && b.text?.trim()) push(s.texts, { at: o.timestamp, text: b.text.slice(0, 4000) }, 3);
    if (b.type !== 'tool_use') continue;
    const inp = b.input || {};
    if (EDIT_TOOLS.has(b.name) && (inp.file_path || inp.notebook_path)) noteCwd(s.edits, inp.file_path || inp.notebook_path);
    if (b.name === 'Bash' || b.name === 'PowerShell') {
      push(s.commands, String(inp.command || '').slice(0, 300), 15);
      if (inp.run_in_background) s.jobs.set(b.id, { id: b.id, kind: b.name, what: String(inp.command || '').slice(0, 200) });
    }
    if (b.name === 'Agent' || b.name === 'Task') {
      s.jobs.set(b.id, { id: b.id, kind: 'sub-agent', what: inp.description || String(inp.prompt || '').slice(0, 120) });
    }
    if (b.name === 'TodoWrite' && Array.isArray(inp.todos)) s.todos = inp.todos;
  }
}
