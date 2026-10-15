// Drive a Codemagic build through Keith's signed-in Chrome on ONE connection: every new connection is another Allow click.
// Flags and examples: ../SKILL.md, "Pressing Start new build".
import { spawn } from 'node:child_process';
import { openSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const args = parseArgs(process.argv.slice(2));
const LOG_DIR = tmpdir();
// Failures a plain rerun clears; anything else stops for a human look.
const TRANSIENT = [
  { name: 'Google Fonts fetch at build time', re: /next\/font\/google queries have exactly one entry|Failed to fetch font/ },
  { name: 'App Store Connect 5xx during upload', re: /received status code 5\d\d; internal server error/ },
];

if (args.wait) await waitForResult(args.wait, Number(args.seconds ?? 570));
if (args.detach) detach();
const { chromium } = createRequire(join(process.cwd(), 'package.json'))('playwright');
const base = `https://codemagic.io/app/${args.app}`;

console.log('Connecting to Chrome: Keith clicks Allow once.');
const portFile = join(process.env.LOCALAPPDATA, 'Google/Chrome/User Data/DevToolsActivePort');
const [port, path] = readFileSync(portFile, 'utf8').trim().split(/\r?\n/);
const browser = await chromium.connectOverCDP(`ws://127.0.0.1:${port}${path}`, { timeout: 300000 }).catch((error) => {
  console.log(`RESULT error no connection, was Allow clicked within 5 minutes? ${error.message.split('\n')[0]}`);
  process.exit(1);
});
const page = await browser.contexts()[0].newPage();
try {
  for (const id of String(args.check ?? '').split(',').filter(Boolean)) await report(id, await inspect(id));
  if (args['dry-run']) {
    await openDialog();
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    await finish('RESULT dry-run ok: the dialog reads the branch and workflow asked for', 0);
  }
  if (args.check) await finish('RESULT checked', 0);
  await release();
} catch (error) {
  await finish(`RESULT error ${error.message.split('\n')[0]}`, 1);
}

async function release() {
  const retries = Number(args.retries ?? 2);
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const dialog = await openDialog();
    await dialog.getByRole('button', { name: /start new build/i }).click();
    await page.waitForURL(/\/build\/[0-9a-f]{24}/, { timeout: 60000 });
    const id = page.url().match(/\/build\/([0-9a-f]{24})/)[1];
    console.log(`started ${base}/build/${id} (attempt ${attempt + 1})`);
    const outcome = await watch(id);
    await report(id, outcome);
    if (outcome.state === 'success') await finish(`RESULT success ${id}`, 0);
    if (!outcome.transient) await finish(`RESULT failed ${id} at "${outcome.step}", log ${outcome.log}`, 1);
    console.log(`rerunning: ${outcome.transient}`);
  }
  await finish('RESULT failed: transient errors outlasted the retries', 1);
}

async function openDialog() {
  await page.goto(`${base}/settings`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: /start new build/i }).first().click({ timeout: 90000 });
  const heading = page.getByText('Specify build configuration');
  await heading.waitFor({ timeout: 30000 });
  await page.waitForTimeout(3000);
  const dialog = page.locator('div', { has: heading }).filter({ hasText: 'Select file workflow' }).last();
  const branch = args.branch ?? 'main';
  await choose(dialog, 'Select branch', branch);
  await choose(dialog, 'Select file workflow', args.workflow);
  const text = await dialog.innerText();
  const shows = (label, value) => new RegExp(`${label}\\s*${escape(value)}\\s*\\n`).test(text);
  if (!shows('Select branch', branch) || !shows('Select file workflow', args.workflow)) {
    throw new Error(`dialog does not read the asked branch and workflow: ${JSON.stringify(text.slice(0, 300))}`);
  }
  return dialog;
}

async function choose(dialog, label, value) {
  const current = (await dialog.innerText()).split(label)[1]?.trim().split('\n')[0];
  if (!current) throw new Error(`no "${label}" field in the dialog`);
  if (current === value) return;
  await dialog.getByText(current, { exact: true }).first().click();
  await page.getByText(value, { exact: true }).last().click();
  await page.waitForTimeout(1500);
}

async function watch(id) {
  const deadline = Date.now() + Number(args['max-minutes'] ?? 45) * 60000;
  while (Date.now() < deadline) {
    // A Codemagic tab left open reads stale, so every look starts from a fresh load.
    const outcome = await inspect(id);
    if (outcome.state !== 'running') return outcome;
    console.log(`${new Date().toISOString().slice(11, 19)} running, ${outcome.timed} steps done`);
    await page.waitForTimeout(30000);
  }
  return { state: 'failed', step: 'watch timed out', log: '' };
}

async function inspect(id) {
  await page.goto(`${base}/build/${id}`, { waitUntil: 'domcontentloaded' });
  await page.getByText('Build overview').waitFor({ timeout: 60000 });
  await page.waitForTimeout(6000);
  if (args.check) writeFileSync(join(LOG_DIR, `codemagic-${id}.html`), await page.content());
  const text = await page.locator('body').innerText();
  const overview = text.slice(text.indexOf('Build overview'));
  const timed = overview.split('\n').filter((line) => /^(\d+m )?\d+s$|^< 1s$/.test(line.trim())).length;
  if (text.includes('Cancel build')) return { state: 'running', timed };
  const failed = text.match(/Step \d+ script `([^`]+)` exited with status code [1-9]/);
  if (!failed) return { state: 'success', timed };
  const log = await stepLog(id, failed[1]);
  const transient = TRANSIENT.find((t) => t.re.test(readFileSync(log, 'utf8')))?.name;
  return { state: 'failed', step: failed[1], log, transient, timed };
}

async function stepLog(id, step) {
  const full = page.getByText(/load the full log/i);
  if (!(await full.count())) await page.getByText(step, { exact: true }).first().click();
  await page.waitForTimeout(2000);
  if (await full.count()) await full.first().click();
  await page.waitForTimeout(5000);
  const text = await page.locator('body').innerText();
  const file = join(LOG_DIR, `codemagic-${id}-${step.replace(/\W+/g, '-')}.log`);
  writeFileSync(file, text.slice(text.indexOf(step)));
  return file;
}

async function report(id, outcome) {
  const where = outcome.step ? ` at "${outcome.step}"` : '';
  console.log(`${id}: ${outcome.state}${where}${outcome.transient ? ` (transient: ${outcome.transient})` : ''}`);
  if (outcome.state !== 'success' || !args['report-step']) return;
  const log = await stepLog(id, args['report-step']);
  const lines = readFileSync(log, 'utf8').split('\n').map((line) => line.trim())
    .filter((line) => /^(Version code|Version|State|Submitted date):|^Created Review Submission/.test(line));
  console.log(`${args['report-step']}:\n  ${[...new Set(lines)].join('\n  ')}`);
}

async function finish(line, code) {
  console.log(line);
  // Close only our tab: browser.close() on a CDP connection would end Keith's own browser session.
  await page.close().catch((error) => console.log(`could not close the tab: ${error.message}`));
  process.exit(code);
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

// Reads only the log file, never Chrome; exit 0 success, 1 failure, 2 still running (wait again).
async function waitForResult(file, seconds) {
  let shown = 0;
  for (const end = Date.now() + seconds * 1000; Date.now() < end; await new Promise((r) => setTimeout(r, 5000))) {
    const text = readFileSync(file, 'utf8');
    process.stdout.write(text.slice(shown));
    shown = text.length;
    const result = text.match(/^RESULT (\S+)/m);
    if (result) process.exit(['success', 'dry-run', 'checked'].includes(result[1]) ? 0 : 1);
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
  if (!out.wait && (!out.app || !out.workflow)) throw new Error('--app and --workflow are required');
  return out;
}

function escape(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
