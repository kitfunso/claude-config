#!/usr/bin/env node
'use strict';
// File walk mirrors extract-shell-cases.js's recentTranscripts; SECRET extends its pattern.
const fs = require('fs');
const os = require('os');
const path = require('path');
const readline = require('readline');
const crypto = require('crypto');

const PROJECTS_DIR = path.join(os.homedir(), '.claude', 'projects');
// Outputs hold command text, so they go to the temp dir, never into this git repo.
const OUT_DIR = path.join(os.tmpdir(), 'claude-token-map');
const DAYS = 14;
const REPLAY_MIN_CHARS = 4000;
const REPLAY_CAP_TOTAL = 200;
const REPLAY_CAP_PER_FAMILY = 15;

const SECRET = /sk-[A-Za-z0-9]|Bearer\s|api[_-]?key|apikey|password\s*[=:]|secret|token\s*=|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN|[A-Za-z0-9_-]{40,}/i;

const MULTIWORD = new Set(['git', 'npm', 'npx', 'uv', 'node', 'python', 'gh', 'cargo', 'docker', 'hippo']);
const NAMED_TOOLS = new Set(['Bash', 'PowerShell', 'Read', 'Grep', 'Glob', 'WebFetch', 'Edit', 'Write']);

function recentTranscripts(dir, cutoff, found = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) recentTranscripts(full, cutoff, found);
    else if (entry.name.endsWith('.jsonl') && fs.statSync(full).mtimeMs >= cutoff) found.push(full);
  }
  return found;
}

function toolFamily(name) {
  if (name.startsWith('mcp__playwright__')) return 'mcp__playwright__*';
  if (name.startsWith('mcp__claude-in-chrome__')) return 'mcp__claude-in-chrome__*';
  if (name === 'Agent') return 'Agent/Task';
  if (NAMED_TOOLS.has(name)) return name;
  return 'other';
}

function shellFamily(cmd) {
  const toks = cmd.trim().split(/\s+/);
  if (!toks[0]) return '(empty)';
  const base = toks[0].split(/[\\/]/).pop().replace(/\.exe$/i, '').toLowerCase();
  if (MULTIWORD.has(base) && toks[1]) return base + ' ' + toks[1].toLowerCase();
  return base;
}

// Uses the inline transcript size, not the true size behind a persisted-output pointer.
function contentChars(content) {
  if (typeof content === 'string') return content.length;
  if (Array.isArray(content)) {
    let n = 0;
    for (const c of content) {
      if (typeof c === 'string') n += c.length;
      else if (c && typeof c.text === 'string') n += c.text.length;
      else if (c && c.type === 'image') n += 0;
      else n += JSON.stringify(c || '').length;
    }
    return n;
  }
  return JSON.stringify(content || '').length;
}

function contentText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) return content.map((c) => (typeof c === 'string' ? c : (c && c.text) || '')).join('\n');
  return JSON.stringify(content || '');
}

function bump(map, key, chars) {
  let e = map.get(key);
  if (!e) { e = { calls: 0, total: 0, lengths: [] }; map.set(key, e); }
  e.calls++;
  e.total += chars;
  e.lengths.push(chars);
}

function stats(e) {
  const s = e.lengths.slice().sort((a, b) => a - b);
  const at = (p) => (s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : 0);
  return { calls: e.calls, total: e.total, median: at(0.5), p95: at(0.95), max: s.length ? s[s.length - 1] : 0 };
}

function sha1(s) { return crypto.createHash('sha1').update(s).digest('hex'); }

const toolStats = new Map();
const shellStats = new Map();
let shellTotalChars = 0, shellOver4000 = 0, shellOver10000 = 0;
const browserStats = new Map();
const browserPerSession = new Map();
const browserBiggest = [];
const hookSessions = new Map();
const hookByHead = new Map();
const attachmentTypes = new Map();
let overall = { userText: 0, assistantText: 0, toolResult: 0, hookInject: 0 };
const replayCandidates = [];
let droppedSecret = 0;
let unparsed = 0;

fs.mkdirSync(OUT_DIR, { recursive: true });
const files = recentTranscripts(PROJECTS_DIR, Date.now() - DAYS * 86400000);
console.error(`scanning ${files.length} transcripts (${DAYS}d)...`);

async function processFile(file) {
  const idToTool = new Map();
  const idToCmd = new Map();
  let pendingNext = [];
  const rl = readline.createInterface({ input: fs.createReadStream(file, { encoding: 'utf8', highWaterMark: 1 << 20 }), crlfDelay: Infinity });

  for await (const line of rl) {
    if (line.length < 15) continue;
    const isAssistant = line.includes('"type":"assistant"');
    const isUser = !isAssistant && line.includes('"type":"user"');
    const isAttachment = !isAssistant && !isUser && line.includes('"type":"attachment"');
    if (!isAssistant && !isUser && !isAttachment) continue;
    let d;
    try { d = JSON.parse(line); } catch (e) { unparsed++; continue; }

    if (isAttachment) {
      const att = d.attachment;
      if (!att) continue;
      const chars = JSON.stringify(att).length;
      overall.hookInject += chars;
      bump(attachmentTypes, att.type || 'unknown', chars);
      if (att.type === 'hook_additional_context' && att.hookEvent === 'UserPromptSubmit') {
        const sid = d.sessionId || file;
        let hs = hookSessions.get(sid);
        if (!hs) { hs = { prompts: 0, totalChars: 0, repeatChars: 0, seen: new Set() }; hookSessions.set(sid, hs); }
        const text = Array.isArray(att.content) ? att.content.join('\n\n') : String(att.content || '');
        const head = text.trim().split('\n')[0].slice(0, 60);
        let hh = hookByHead.get(head);
        if (!hh) { hh = { total: 0, repeat: 0 }; hookByHead.set(head, hh); }
        hs.prompts++;
        hs.totalChars += text.length;
        hh.total += text.length;
        if (hs.seen.has(text)) { hs.repeatChars += text.length; hh.repeat += text.length; }
        else hs.seen.add(text);
      }
      continue;
    }

    const content = d.message && d.message.content;

    if (isAssistant) {
      if (!Array.isArray(content)) continue;
      let firstText = null;
      for (const item of content) {
        if (!item || typeof item !== 'object') continue;
        if (item.type === 'text') {
          overall.assistantText += item.text.length;
          if (firstText === null) firstText = item.text;
        } else if (item.type === 'thinking') {
          overall.assistantText += (item.thinking || '').length;
        } else if (item.type === 'tool_use' && item.id) {
          idToTool.set(item.id, item.name);
          if ((item.name === 'Bash' || item.name === 'PowerShell') && item.input && item.input.command) {
            idToCmd.set(item.id, item.input.command);
          }
        }
      }
      if (firstText !== null && pendingNext.length) {
        const snippet = firstText.slice(0, 1500);
        for (const idx of pendingNext) replayCandidates[idx].next_assistant_text = snippet;
        pendingNext = [];
      }
      continue;
    }

    if (typeof content === 'string') {
      overall.userText += content.length;
      continue;
    }
    if (!Array.isArray(content)) continue;
    for (const item of content) {
      if (!item || typeof item !== 'object' || item.type !== 'tool_result') continue;
      const name = idToTool.get(item.tool_use_id) || 'unknown';
      const chars = contentChars(item.content);
      overall.toolResult += chars;
      bump(toolStats, toolFamily(name), chars);

      if (name === 'Bash' || name === 'PowerShell') {
        shellTotalChars += chars;
        if (chars > 4000) shellOver4000 += chars;
        if (chars > 10000) shellOver10000 += chars;
        const cmd = idToCmd.get(item.tool_use_id) || '';
        const fam = shellFamily(cmd);
        bump(shellStats, fam, chars);
        if (chars > REPLAY_MIN_CHARS) {
          const text = contentText(item.content);
          if (SECRET.test(cmd) || SECRET.test(text)) {
            droppedSecret++;
          } else {
            const idx = replayCandidates.length;
            replayCandidates.push({ family: fam, command: cmd.slice(0, 300), output: text, next_assistant_text: '' });
            pendingNext.push(idx);
          }
        }
      } else if (name.startsWith('mcp__playwright__') || name.startsWith('mcp__claude-in-chrome__')) {
        const fam = toolFamily(name);
        bump(browserStats, fam, chars);
        const sid = d.sessionId || file;
        let bp = browserPerSession.get(sid);
        if (!bp) { bp = {}; browserPerSession.set(sid, bp); }
        bp[fam] = (bp[fam] || 0) + 1;
        browserBiggest.push({ name, size: chars });
      }
    }
  }
}

(async () => {
  let done = 0;
  for (const f of files) {
    await processFile(f);
    done++;
    if (done % 100 === 0) console.error(`  ${done}/${files.length} files...`);
  }

  const toolRows = [...toolStats.entries()].map(([k, v]) => [k, stats(v)]).sort((a, b) => b[1].total - a[1].total);
  const totalToolChars = toolRows.reduce((s, [, v]) => s + v.total, 0);

  const shellRows = [...shellStats.entries()].map(([k, v]) => [k, stats(v)]).sort((a, b) => b[1].total - a[1].total).slice(0, 25);

  const hookRows = [...hookSessions.entries()].map(([sid, h]) => ({ sid, prompts: h.prompts, totalChars: h.totalChars, repeatChars: h.repeatChars }));
  const hookTotalChars = hookRows.reduce((s, r) => s + r.totalChars, 0);
  const hookRepeatChars = hookRows.reduce((s, r) => s + r.repeatChars, 0);
  const hookHeads = [...hookByHead.entries()].map(([head, v]) => ({ head, ...v })).sort((a, b) => b.total - a.total).slice(0, 10);

  browserBiggest.sort((a, b) => b.size - a.size);
  const browserTop5 = browserBiggest.slice(0, 5);
  const browserRows = [...browserStats.entries()].map(([k, v]) => [k, stats(v)]);
  const browserSessCalls = [...browserPerSession.values()];
  function avgCallsPerSession(fam) {
    const arr = browserSessCalls.map((bp) => bp[fam] || 0).filter((n) => n > 0);
    if (!arr.length) return { sessions: 0, avgCalls: 0 };
    return { sessions: arr.length, avgCalls: arr.reduce((a, b) => a + b, 0) / arr.length };
  }

  const grandTotal = overall.userText + overall.assistantText + overall.toolResult + overall.hookInject;

  const byFamily = new Map();
  for (const c of replayCandidates) {
    if (!byFamily.has(c.family)) byFamily.set(c.family, []);
    byFamily.get(c.family).push(c);
  }
  for (const arr of byFamily.values()) {
    arr.sort((a, b) => sha1(a.command + a.output.slice(0, 200)).localeCompare(sha1(b.command + b.output.slice(0, 200))));
    arr.length = Math.min(arr.length, REPLAY_CAP_PER_FAMILY);
  }
  // Pass 1 takes one sample per family for breadth; pass 2 fills the big families toward the cap.
  const familyKeys = [...byFamily.keys()].sort((a, b) => byFamily.get(b).length - byFamily.get(a).length || a.localeCompare(b));
  const taken = new Map(familyKeys.map((fk) => [fk, 0]));
  const replaySet = [];
  for (const fk of familyKeys) {
    if (replaySet.length >= REPLAY_CAP_TOTAL) break;
    replaySet.push(byFamily.get(fk)[0]);
    taken.set(fk, 1);
  }
  for (const fk of familyKeys) {
    const arr = byFamily.get(fk);
    while (replaySet.length < REPLAY_CAP_TOTAL && taken.get(fk) < arr.length) {
      replaySet.push(arr[taken.get(fk)]);
      taken.set(fk, taken.get(fk) + 1);
    }
    if (replaySet.length >= REPLAY_CAP_TOTAL) break;
  }
  const replayOut = replaySet.map((c, i) => ({ id: `trim-${i}`, family: c.family, command: c.command, output: c.output, next_assistant_text: c.next_assistant_text }));

  fs.writeFileSync(path.join(OUT_DIR, 'trim-replay-cases.json'), JSON.stringify(replayOut));

  const fullResults = {
    files: files.length,
    unparsedLines: unparsed,
    tools: toolRows.map(([k, v]) => ({ tool: k, ...v, shareOfToolChars: totalToolChars ? v.total / totalToolChars : 0 })),
    shellTop25: shellRows.map(([k, v]) => ({ family: k, ...v })),
    shellTotalChars, shellOver4000, shellOver10000,
    attachmentTypes: [...attachmentTypes.entries()].map(([k, v]) => ({ type: k, ...stats(v) })).sort((a, b) => b.total - a.total),
    hookSessions: hookRows.length, hookTotalChars, hookRepeatChars, hookHeads,
    browser: browserRows.map(([k, v]) => ({ family: k, ...stats(browserStats.get(k)), ...avgCallsPerSession(k) })),
    browserTop5,
    overall,
    grandTotal,
    replay: { candidates: replayCandidates.length, kept: replayOut.length, droppedSecret },
  };
  fs.writeFileSync(path.join(OUT_DIR, 'token-map-results.json'), JSON.stringify(fullResults, null, 2));

  console.log('\n=== TOOL RESULTS BY TOOL (chars) ===');
  for (const [k, v] of toolRows.slice(0, 15)) {
    console.log(`${k.padEnd(28)} calls=${v.calls.toString().padStart(7)} total=${v.total.toString().padStart(10)} share=${(100 * v.total / totalToolChars).toFixed(1).padStart(5)}% median=${v.median.toString().padStart(6)} p95=${v.p95.toString().padStart(7)} max=${v.max}`);
  }
  console.log(`TOTAL tool-result chars: ${totalToolChars} (~${Math.round(totalToolChars / 4)} tok)`);

  console.log('\n=== SHELL FAMILIES (top 25 by total chars) ===');
  for (const [k, v] of shellRows) {
    console.log(`${k.padEnd(20)} calls=${v.calls.toString().padStart(6)} total=${v.total.toString().padStart(10)} median=${v.median.toString().padStart(6)} p95=${v.p95}`);
  }
  console.log(`shell total chars=${shellTotalChars} over4000=${shellOver4000} (${(100 * shellOver4000 / shellTotalChars).toFixed(1)}%) over10000=${shellOver10000} (${(100 * shellOver10000 / shellTotalChars).toFixed(1)}%)`);

  console.log('\n=== ATTACHMENT TYPES (transcript records, chars) ===');
  const attRows = [...attachmentTypes.entries()].map(([k, v]) => [k, stats(v)]).sort((a, b) => b[1].total - a[1].total);
  for (const [k, v] of attRows) {
    console.log(`${k.padEnd(26)} calls=${v.calls.toString().padStart(6)} total=${v.total.toString().padStart(10)} share=${(100 * v.total / overall.hookInject).toFixed(1)}%`);
  }

  console.log('\n=== PER-PROMPT HOOK TEXT (UserPromptSubmit) ===');
  console.log(`sessions with hook context=${hookRows.length} total prompts=${hookRows.reduce((s, r) => s + r.prompts, 0)}`);
  console.log(`total injected chars=${hookTotalChars} repeat chars=${hookRepeatChars} repeat share=${(100 * hookRepeatChars / hookTotalChars).toFixed(1)}%`);
  for (const h of hookHeads) {
    console.log(`  ${h.head.padEnd(60)} total=${h.total.toString().padStart(9)} repeat=${h.repeat.toString().padStart(9)}`);
  }

  console.log('\n=== BROWSER FAMILIES ===');
  for (const [k, v] of browserRows) {
    const a = avgCallsPerSession(k);
    console.log(`${k.padEnd(28)} calls=${v.calls} total=${v.total} median=${v.median} p95=${v.p95} max=${v.max} sessionsUsing=${a.sessions} avgCallsPerSession=${a.avgCalls.toFixed(1)}`);
  }
  console.log('top5 biggest single browser results:', browserTop5);

  console.log('\n=== OVERALL SPLIT (chars) ===');
  for (const k of Object.keys(overall)) {
    console.log(`${k.padEnd(14)} ${overall[k]} (${(100 * overall[k] / grandTotal).toFixed(1)}%)`);
  }
  console.log(`grand total chars=${grandTotal} (~${Math.round(grandTotal / 4)} tok)`);

  console.log('\n=== REPLAY SET ===');
  console.log(`candidates>4000chars=${replayCandidates.length} droppedSecretShaped=${droppedSecret} kept=${replayOut.length}`);
  console.log(`unparsed lines=${unparsed}`);
  console.log(`outputs in ${OUT_DIR}`);
})();
