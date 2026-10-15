// Start, watch and rerun a Codemagic build through its REST API, so no release needs a browser.
// Flags and examples: ../SKILL.md, "Starting a Codemagic build".
import { execFileSync, spawn } from 'node:child_process';
import { openSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const args = parseArgs(process.argv.slice(2));
const LOG_DIR = tmpdir();
// CODEMAGIC_API points the script at the stand-in server in codemagic-run.test.mjs.
const API = process.env.CODEMAGIC_API ?? 'https://api.codemagic.io';
// Failures a plain rerun clears; anything else stops for a human look.
const TRANSIENT = [
  { name: 'Google Fonts fetch at build time', re: /next\/font\/google queries have exactly one entry|Failed to fetch font/ },
  { name: 'App Store Connect 5xx during upload', re: /received status code 5\d\d; internal server error/ },
];
// Listing the end states, not the running ones: an unknown new state then reads as still running.
const FINAL = new Set(['finished', 'failed', 'canceled', 'timeout', 'skipped', 'warning']);
const GOOD = ['success', 'dry-run', 'checked'];

if (args.wait) await waitForResult(args.wait, Number(args.seconds ?? 570));
if (args.detach) detach();
const token = readToken();
const result = token
  ? await main().catch((error) => `RESULT error ${error.message}`)
  : 'RESULT error no CODEMAGIC_AUTH_TOKEN: see "One-time setup" in the build-release skill';
console.log(result);
// exitCode, never process.exit(): exiting with a fetch socket open trips a libuv assertion on Windows.
process.exitCode = GOOD.includes(result.split(' ')[1]) ? 0 : 1;

async function main() {
  if (args['dry-run']) {
    const { application } = await api(`/apps/${args.app}`);
    return `RESULT dry-run ok: the token reads app "${application.appName}"`;
  }
  for (const id of String(args.check ?? '').split(',').filter(Boolean)) await report(id, await inspect(id));
  return args.check ? 'RESULT checked' : release();
}

async function release() {
  const retries = Number(args.retries ?? 2);
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const body = { appId: args.app, workflowId: args.workflow, branch: args.branch };
    const { buildId } = await api('/builds', { method: 'POST', body: JSON.stringify(body) });
    console.log(`started https://codemagic.io/app/${args.app}/build/${buildId} (attempt ${attempt + 1})`);
    const outcome = await watch(buildId);
    await report(buildId, outcome);
    if (outcome.state === 'success') return `RESULT success ${buildId}`;
    if (!outcome.transient) return `RESULT failed ${buildId} at "${outcome.step}", log ${outcome.log}`;
    console.log(`rerunning: ${outcome.transient}`);
  }
  return 'RESULT failed: transient errors outlasted the retries';
}

async function watch(id) {
  const deadline = Date.now() + Number(args['max-minutes'] ?? 45) * 60000;
  while (Date.now() < deadline) {
    const outcome = await inspect(id);
    if (outcome.state !== 'running') return outcome;
    console.log(`${new Date().toISOString().slice(11, 19)} ${outcome.status}, ${outcome.done} steps done`);
    await new Promise((resolve) => setTimeout(resolve, 30000));
  }
  return { state: 'failed', step: 'watch timed out', log: '' };
}

async function inspect(id) {
  const { build } = await api(`/builds/${id}`);
  if (args.check) writeFileSync(join(LOG_DIR, `codemagic-${id}.json`), JSON.stringify(build, null, 2));
  const steps = (build.buildActions ?? []).flatMap((action) => (action.subactions?.length ? action.subactions : [action]));
  const done = steps.filter((step) => step.status === 'success').length;
  if (!FINAL.has(build.status)) return { state: 'running', status: build.status, done };
  if (build.status === 'finished') return { state: 'success', steps, done };
  const failed = steps.find((step) => step.status === 'failed');
  if (!failed) return { state: 'failed', step: `build ${build.status}`, log: '', done };
  const log = await stepLog(id, failed);
  const transient = TRANSIENT.find((t) => t.re.test(readFileSync(log, 'utf8')))?.name;
  return { state: 'failed', step: failed.name, log, transient, done };
}

async function stepLog(id, step) {
  if (!step.logUrl) throw new Error(`step "${step.name}" of ${id} has no logUrl`);
  const file = join(LOG_DIR, `codemagic-${id}-${step.name.replace(/\W+/g, '-')}.log`);
  writeFileSync(file, await api(step.logUrl, { text: true }));
  return file;
}

async function report(id, outcome) {
  const where = outcome.step ? ` at "${outcome.step}"` : '';
  console.log(`${id}: ${outcome.state}${where}${outcome.transient ? ` (transient: ${outcome.transient})` : ''}`);
  if (outcome.state !== 'success' || !args['report-step']) return;
  const step = outcome.steps.find((s) => s.name === args['report-step']);
  if (!step) return console.log(`no step named "${args['report-step']}" in ${id}`);
  const lines = readFileSync(await stepLog(id, step), 'utf8').split('\n').map((line) => line.trim())
    .filter((line) => /^(Version code|Version|State|Submitted date):|^Created Review Submission/.test(line));
  console.log(`${args['report-step']}:\n  ${[...new Set(lines)].join('\n  ')}`);
}

async function api(path, { method = 'GET', body, text = false } = {}) {
  const url = /^https?:\/\//.test(path) ? path : `${API}${path}`;
  const response = await fetch(url, { method, body, headers: { 'Content-Type': 'application/json', 'x-auth-token': token } });
  const payload = await response.text();
  if (!response.ok) throw new Error(`${method} ${url} answered ${response.status}: ${payload.slice(0, 300)}`);
  return text ? payload : JSON.parse(payload);
}

function readToken() {
  if (process.env.CODEMAGIC_AUTH_TOKEN?.trim()) return process.env.CODEMAGIC_AUTH_TOKEN.trim();
  // A session started before the token was set has an old environment; the User scope lives in the registry.
  try {
    const out = execFileSync('reg', ['query', 'HKCU\\Environment', '/v', 'CODEMAGIC_AUTH_TOKEN'], { encoding: 'utf8', stdio: 'pipe' });
    const value = out.match(/CODEMAGIC_AUTH_TOKEN\s+REG_\w+\s+(\S+)/)?.[1];
    if (value) return value;
  } catch (error) {
    if (error.status !== 1) throw error;
  }
  return null;
}

function detach() {
  const log = join(LOG_DIR, `codemagic-run-${Date.now()}.log`);
  const fd = openSync(log, 'a');
  const rest = process.argv.slice(2).filter((arg) => arg !== '--detach');
  // Parentless, so the harness's low-memory reaper cannot take it down with a shell.
  spawn(process.execPath, [process.argv[1], ...rest], { cwd: process.cwd(), detached: true, stdio: ['ignore', fd, fd], windowsHide: true }).unref();
  console.log(`LOG ${log}`);
  process.exit(0);
}

// Reads only the log file; exit 0 success, 1 failure, 2 still running (wait again).
async function waitForResult(file, seconds) {
  let shown = 0;
  for (const end = Date.now() + seconds * 1000; Date.now() < end; await new Promise((r) => setTimeout(r, 5000))) {
    const text = readFileSync(file, 'utf8');
    process.stdout.write(text.slice(shown));
    shown = text.length;
    const result = text.match(/^RESULT (\S+)/m);
    if (result) process.exit(GOOD.includes(result[1]) ? 0 : 1);
  }
  process.exit(2);
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i].replace(/^--/, '');
    if (argv[i + 1] === undefined || argv[i + 1].startsWith('--')) out[key] = true;
    else out[key] = argv[(i += 1)];
  }
  const starts = !out.wait && !out.check && !out['dry-run'];
  if (!out.wait && !out.app) throw new Error('--app is required');
  if (starts && (!out.workflow || !out.branch)) throw new Error('--workflow and --branch are required to start a build');
  return out;
}
