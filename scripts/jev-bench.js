#!/usr/bin/env node
'use strict';
// usage: node jev-bench.js <pack.js> [--cases file.json] [--repeat 2] [--thr 0.5] [--limit N] [--show 60] [--out file.jsonl]
// Results hold command text, so --out defaults to the temp dir and never to this git repo.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { ask, lint, provider, USD_PER_MTOK, NEURONS_PER_MTOK } = require('./hooks/lib/jev');

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : fallback;
};
const rate = (n, d) => (d ? (n / d).toFixed(3) : 'n/a');
const clip = (s, n = 140) => String(s).replace(/\s+/g, ' ').slice(0, n);
const anyNoul = (answers, thr) => Object.values(answers).some((a) => typeof a.noul === 'number' && a.noul >= thr);

async function pool(items, limit, fn) {
  const out = new Array(items.length);
  let cursor = 0;
  const worker = async () => {
    while (cursor < items.length) {
      const i = cursor++;
      out[i] = await fn(items[i]);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return out;
}

// A flip between repeats counts against Jev both ways: `all` scores recall, `any` scores false flags.
function decide(runs, thr, flag) {
  const decisions = runs.filter((r) => !r.error).map((r) => flag(r.answers, thr));
  return { all: decisions.length > 0 && decisions.every(Boolean), any: decisions.some(Boolean) };
}

function nouls(runs) {
  const byQuestion = {};
  for (const r of runs.filter((x) => !x.error)) {
    for (const [q, a] of Object.entries(r.answers)) {
      if (typeof a.noul === 'number') (byQuestion[q] = byQuestion[q] || []).push(a.noul);
    }
  }
  return byQuestion;
}

// A baseline may return one boolean, or an object of booleans keyed like `expect` for per-question rates.
const baseFlag = (v) => (v && typeof v === 'object' ? Object.values(v).some(Boolean) : Boolean(v));
const label = (c) => c.input.command || c.id;

function perQuestion(rows, thr, baselines) {
  console.log('  per question (Jev: recall needs every repeat, a false flag any repeat):');
  for (const q of Object.keys(rows[0].c.expect)) {
    const pos = rows.filter((r) => r.c.expect[q]);
    const neg = rows.filter((r) => !r.c.expect[q]);
    const jev = (r) => (r.nouls[q] || []).map((v) => v >= thr);
    const cells = [`A2 recall=${rate(pos.filter((r) => jev(r).length && jev(r).every(Boolean)).length, pos.length)} ff=${rate(neg.filter((r) => jev(r).some(Boolean)).length, neg.length)}`];
    for (const [name, fn] of Object.entries(baselines)) {
      if (typeof fn(rows[0].c.input) !== 'object') continue;
      cells.push(`${name} recall=${rate(pos.filter((r) => fn(r.c.input)[q]).length, pos.length)} ff=${rate(neg.filter((r) => fn(r.c.input)[q]).length, neg.length)}`);
    }
    console.log(`    ${q} (+${pos.length}/-${neg.length})  ${cells.join('  ')}`);
  }
}

function reportLabelled(rows, thr, flag, baselines, positive) {
  const pos = rows.filter((r) => positive(r.c.expect));
  const neg = rows.filter((r) => !positive(r.c.expect));
  console.log(`\nLABELLED  n=${rows.length}  flag=${pos.length}  no-flag=${neg.length}`);
  for (const t of [0.3, 0.5, 0.7]) {
    const tag = t === thr ? 'A2_jev (primary)' : 'A2_jev (diagnostic)';
    const hit = pos.filter((r) => decide(r.runs, t, flag).all).length;
    const falseFlag = neg.filter((r) => decide(r.runs, t, flag).any).length;
    console.log(`  ${tag} thr=${t}  recall=${rate(hit, pos.length)}  false-flag=${rate(falseFlag, neg.length)}`);
  }
  for (const [name, fn] of Object.entries(baselines)) {
    const hit = pos.filter((r) => baseFlag(fn(r.c.input))).length;
    const falseFlag = neg.filter((r) => baseFlag(fn(r.c.input))).length;
    console.log(`  ${name}  recall=${rate(hit, pos.length)}  false-flag=${rate(falseFlag, neg.length)}${hit === 0 ? '  DEAD ARM' : ''}`);
  }
  perQuestion(rows, thr, baselines);
  console.log('  per-question misses at the primary threshold:');
  for (const r of rows) {
    for (const [q, want] of Object.entries(r.c.expect)) {
      const values = r.nouls[q] || [];
      const mean = values.reduce((a, b) => a + b, 0) / (values.length || 1);
      if ((mean >= thr) !== want) console.log(`    ${q} want=${want} noul=${mean.toFixed(2)}  ${clip(label(r.c), 90)}`);
    }
  }
}

function reportUnlabelled(rows, thr, flag, baselines, show) {
  console.log(`\nUNLABELLED  n=${rows.length}`);
  const jev = rows.filter((r) => decide(r.runs, thr, flag).any);
  console.log(`  A2_jev thr=${thr} flag-rate=${rate(jev.length, rows.length)} (${jev.length})`);
  for (const [name, fn] of Object.entries(baselines)) {
    console.log(`  ${name} flag-rate=${rate(rows.filter((r) => baseFlag(fn(r.c.input))).length, rows.length)}`);
  }
  const last = Object.values(baselines).pop();
  const strongest = last ? (input) => baseFlag(last(input)) : () => false;
  const top = (r) => Object.entries(r.nouls).map(([q, v]) => [q, Math.max(...v)]).sort((a, b) => b[1] - a[1])[0] || ['-', 0];
  const line = (r) => `${top(r)[0]}=${top(r)[1].toFixed(2)}  ${clip(label(r.c))}`;
  console.log('  flagged by Jev:');
  jev.slice(0, show).forEach((r) => console.log(`    ${strongest(r.c.input) ? 'both' : 'JEV '}  ${line(r)}`));
  console.log('  flagged by the last baseline only:');
  rows.filter((r) => !jev.includes(r) && strongest(r.c.input)).slice(0, show).forEach((r) => console.log(`    BASE  ${line(r)}`));
}

function reportRun(rows, results) {
  const ok = results.filter((r) => !r.error);
  const errors = results.filter((r) => r.error);
  const ms = ok.map((r) => r.ms).sort((a, b) => a - b);
  const tokens = ok.reduce((sum, r) => sum + (r.usage.input_tokens || 0), 0);
  const all = rows.flatMap((r) => Object.values(r.nouls).flat());
  const noise = Math.max(0, ...rows.flatMap((r) => Object.values(r.nouls).map((v) => Math.max(...v) - Math.min(...v))));
  console.log(`\nRUN  requests=${results.length}  errors=${errors.length}${errors[0] ? `  first="${errors[0].error}"` : ''}`);
  console.log(`  latency p50=${ms[Math.floor(ms.length / 2)]}ms  p95=${ms[Math.floor(ms.length * 0.95)]}ms`);
  const model = provider().model;
  const cost = model === "clef-local" ? "free (local)" : model in NEURONS_PER_MTOK ? `${Math.round((tokens / 1e6) * NEURONS_PER_MTOK[model])} neurons` : `$${((tokens / 1e6) * USD_PER_MTOK).toFixed(4)}`;
  console.log(`  ${model}  input tokens=${tokens}  cost=${cost}  per request=${Math.round(tokens / (ok.length || 1))} tok`);
  console.log(`  noul spread across all answers=${all.length ? (Math.max(...all) - Math.min(...all)).toFixed(2) : 'none'}${all.length && Math.max(...all) === Math.min(...all) ? '  DEAD ARM' : ''}`);
  console.log(`  largest noul move between repeats=${noise.toFixed(3)}`);
}

async function main() {
  const pack = require(path.resolve(process.argv[2]));
  const casesFile = arg('cases');
  const source = casesFile ? JSON.parse(fs.readFileSync(casesFile, 'utf8')) : pack.cases;
  const cases = source.slice(0, Number(arg('limit', source.length)));
  const repeat = Number(arg('repeat', 1));
  const thr = Number(arg('thr', 0.5));
  const flag = pack.flag || anyNoul;
  const out = arg('out', path.join(os.tmpdir(), `jev-bench-${pack.name}.jsonl`));

  const first = pack.build(cases[0].input);
  const problems = lint(first.state, first.questions);
  problems.forEach((p) => console.log(`lint ${p}`));
  if (problems.some((p) => !p.startsWith('warn:'))) process.exit(1);

  const jobs = cases.flatMap((c, i) => Array.from({ length: repeat }, () => i));
  const results = await pool(jobs, 8, (i) => {
    const { state, questions } = pack.build(cases[i].input);
    return ask(state, questions, { timeoutMs: 15000 });
  });
  const rows = cases.map((c, i) => {
    const runs = results.filter((_, j) => jobs[j] === i);
    return { c, runs, nouls: nouls(runs) };
  });

  console.log(`PACK ${pack.name}  cases=${cases.length}  repeat=${repeat}  thr=${thr}`);
  const labelled = rows.filter((r) => r.c.expect);
  const unlabelled = rows.filter((r) => !r.c.expect);
  const positive = pack.positive || ((expect) => Object.values(expect).some(Boolean));
  if (labelled.length) reportLabelled(labelled, thr, flag, pack.baselines || {}, positive);
  if (unlabelled.length) reportUnlabelled(unlabelled, thr, flag, pack.baselines || {}, Number(arg('show', 60)));
  reportRun(rows, results);
  fs.writeFileSync(out, rows.map((r) => JSON.stringify({ id: r.c.id, input: r.c.input, expect: r.c.expect, nouls: r.nouls })).join('\n'));
  console.log(`\nrows written to ${out}`);
}

main();
