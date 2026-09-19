'use strict';
// Fail-open Jev client: ask() never throws, it returns { error } so callers keep their pre-Jev path.
const ENDPOINT = 'https://api.typesafe.ai/v1/systemone';
const RETRY_STATUS = new Set([429, 529]);
const USD_PER_MTOK = 0.042;
// Bench numbers and thresholds were measured on this version; the jev-latest alias moves without notice.
const MODEL = 'jev-1.13.0';
const NO_MATCH =/^(none|other|no_match|neither|unknown|not_applicable)/i;
const PATH = /`([^`]+)`/g;

function apiKey() {
  return (process.env.TYPESAFE_API_KEY || '').trim() || null;
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
  const body = JSON.stringify({ state, model: opts.model || MODEL, questions });
  const started = Date.now();
  for (let attempt = 0; attempt < 2; attempt++) {
    let res;
    try {
      res = await fetchFn(ENDPOINT, {
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
      const data = await res.json();
      return { answers: data.answers || {}, usage: data.usage || {}, ms: Date.now() - started };
    } catch (e) {
      return { error: 'bad json' };
    }
  }
  return { error: 'retry exhausted' };
}

module.exports = { ask, lint, apiKey, USD_PER_MTOK, ENDPOINT };
