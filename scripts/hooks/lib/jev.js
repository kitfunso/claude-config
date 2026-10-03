'use strict';
// Fail-open Jev client: ask() never throws, it returns { error } so callers keep their pre-Jev path.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const ENDPOINT = 'https://api.typesafe.ai/v1/systemone';
const RETRY_STATUS = new Set([429, 529]);
const USD_PER_MTOK = 0.042;
// Bench numbers and thresholds were measured on this version; the jev-latest alias moves without notice.
const MODEL = 'jev-1.13.0';
const NO_MATCH =/^(none|other|no_match|neither|unknown|not_applicable)/i;
const PATH = /`([^`]+)`/g;

// Workers AI price in neurons per million input tokens, read 2026-10-03; output is free.
const NEURONS_PER_MTOK = { 'clef-flash': 8182, clef: 21818 };
const LOCAL_URL = 'http://127.0.0.1:8787/ai/run/clef-flash';
const STATE_DIR = process.env.CLEF_STATE_DIR || path.join(os.homedir(), '.claude', 'state');
const WRANGLER_TOML = path.join(os.homedir(), '.wrangler', 'config', 'default.toml');

// Clef-flash on the free allocation is the default once CLOUDFLARE_ACCOUNT_ID is set; JEV_PROVIDER=jev picks paid Jev.
function provider(env = process.env) {
  const account = (env.CLOUDFLARE_ACCOUNT_ID || '').trim();
  const name = (env.JEV_PROVIDER || (account ? 'clef-flash' : 'jev')).trim();
  if (!name.startsWith('clef')) return { endpoint: ENDPOINT, model: MODEL, key: env.TYPESAFE_API_KEY };
  // The local server takes no auth; the placeholder key only gets past ask()'s 'no key' guard.
  if (name === 'clef-local') return { endpoint: env.CLEF_LOCAL_URL || LOCAL_URL, model: 'clef-local', key: 'local', billed: false };
  return {
    endpoint: `https://api.cloudflare.com/client/v4/accounts/${account}/ai/run/@cf/cloudflare/${name}`,
    model: name,
    key: account ? (env.CLOUDFLARE_API_TOKEN || wranglerToken()) : '',
    billed: true,
  };
}

// SHORTCUT: borrows wrangler's hourly OAuth token until a permanent CLOUDFLARE_API_TOKEN exists.
function wranglerToken() {
  try {
    const toml = fs.readFileSync(WRANGLER_TOML, 'utf8');
    const expires = Date.parse((toml.match(/expiration_time\s*=\s*"([^"]+)"/) || [])[1] || '');
    if (expires - Date.now() > 60000) return (toml.match(/oauth_token\s*=\s*"([^"]+)"/) || [])[1] || '';
    refreshWrangler();
  } catch (e) {
    // no wrangler login on this box: the caller sees 'no key' and keeps its old path
  }
  return '';
}

// Expired token: start one detached `wrangler whoami` (it refreshes the toml) and fail open this call.
function refreshWrangler() {
  const marker = path.join(os.tmpdir(), 'clef-wrangler-refresh');
  try {
    if (Date.now() - fs.statSync(marker).mtimeMs < 300000) return;
  } catch (e) {
    // no marker yet: first refresh
  }
  fs.writeFileSync(marker, '');
  spawn('wrangler', ['whoami'], { detached: true, stdio: 'ignore', shell: true, windowsHide: true }).unref();
}

// SHORTCUT: local append-only counter, so a shared Cloudflare account can still overshoot; GraphQL usage if that bites.
function budgetFile() {
  return path.join(STATE_DIR, `clef-neurons-${new Date().toISOString().slice(0, 10)}.log`);
}

function neuronsUsed() {
  try {
    return fs.readFileSync(budgetFile(), 'utf8').split('\n').reduce((sum, line) => sum + (Number(line) || 0), 0);
  } catch (e) {
    return 0;
  }
}

function recordNeurons(model, inputTokens) {
  const neurons = (inputTokens * (NEURONS_PER_MTOK[model] || NEURONS_PER_MTOK.clef)) / 1e6;
  fs.mkdirSync(STATE_DIR, { recursive: true });
  fs.appendFileSync(budgetFile(), `${neurons.toFixed(2)}\n`);
}

function apiKey() {
  return (provider().key || '').trim() || null;
}

function resolves(state, path) {
  const parts = path.replace(/\[(\d+)\]/g, '.$1').split('.');
  let node = state;
  for (const part of parts) {
    if (node === null || typeof node !== 'object' || !(part in node)) return false;
    node = node[part];
  }
  return true;
}

function isMap(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

// A `warn:` prefix means legal but risky; anything else would 422 or mislead.
function lint(state, questions) {
  const problems = [];
  for (const [name, q] of Object.entries(questions)) {
    const where = `${name}:`;
    if (!['noul', 'choice', 'score'].includes(q.type)) problems.push(`${where} unknown type ${q.type}`);
    if (!q.instructions) problems.push(`${where} no instructions`);
    if (q.type === 'noul' && q.criteria !== undefined) {
      const bad = !isMap(q.criteria) || Object.keys(q.criteria).some((k) => k !== 'true' && k !== 'false');
      if (bad) problems.push(`${where} noul criteria must be a map with only true/false keys`);
    }
    if (q.type === 'noul' && q.criteria === undefined) problems.push(`warn: ${where} noul has no true/false definition`);
    if (q.type === 'choice') {
      const keys = isMap(q.criteria) ? Object.keys(q.criteria) : [];
      if (keys.length < 2 || keys.length > 255) problems.push(`${where} choice criteria must be a map of 2..255 options`);
      else if (!keys.some((k) => NO_MATCH.test(k))) problems.push(`warn: ${where} choice has no no-match option; Jev never abstains`);
    }
    if (q.type === 'score' && !(Array.isArray(q.criteria) && q.criteria.length >= 2 && q.criteria.length <= 10)) {
      problems.push(`${where} score criteria must be a list of 2..10 levels`);
    }
    if (isMap(state)) {
      const text = JSON.stringify([q.instructions, q.criteria]);
      for (const match of text.matchAll(PATH)) {
        if (!resolves(state, match[1])) problems.push(`${where} backticked path \`${match[1]}\` is not in state`);
      }
    }
  }
  return problems;
}

async function ask(state, questions, opts = {}) {
  const key = opts.apiKey || apiKey();
  if (!key) return { error: 'no key' };
  const fetchFn = opts.fetcher || fetch;
  const { endpoint, model, billed } = provider();
  // Stop short of the 10,000 free neurons a day so no call is ever billed.
  if (billed && neuronsUsed() >= Number(process.env.CLEF_DAILY_NEURONS || 9000)) return { error: 'free allocation used' };
  const body = JSON.stringify({ state, model: opts.model || model, questions });
  const started = Date.now();
  for (let attempt = 0; attempt < 2; attempt++) {
    let res;
    try {
      res = await fetchFn(endpoint, {
        method: 'POST',
        headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
        body,
        signal: AbortSignal.timeout(opts.timeoutMs || 4000),
      });
    } catch (e) {
      return { error: `fetch: ${e.name}` };
    }
    if (RETRY_STATUS.has(res.status) && attempt === 0) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      continue;
    }
    if (!res.ok) {
      const detail = await res.text().catch(() => '');
      return { error: `http ${res.status}: ${detail.slice(0, 300)}` };
    }
    try {
      const raw = await res.json();
      const data = raw.result || raw; // Workers AI wraps the System One reply in its { result } envelope
      const usage = data.usage || {};
      // Unknown usage is not zero: fall back to a 4-chars-per-token estimate of the request.
      if (billed) recordNeurons(model, usage.input_tokens || usage.prompt_tokens || body.length / 4);
      return { answers: data.answers || {}, usage, ms: Date.now() - started, model };
    } catch (e) {
      return { error: 'bad json' };
    }
  }
  return { error: 'retry exhausted' };
}

module.exports = { ask, lint, apiKey, provider, neuronsUsed, USD_PER_MTOK, NEURONS_PER_MTOK, ENDPOINT };
