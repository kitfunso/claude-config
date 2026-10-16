// Raw CDP to Keith's signed-in Chrome through one tab of our own; Playwright's connectOverCDP
// hung attaching to his many open tabs (2026-10-16). Usage: README.md beside this file.
import http from 'node:http';
import { readFileSync } from 'node:fs';

const PORT = Number(process.env.BRIDGE_PORT ?? 9557);
// Replies hide long strings so a secret on the page never reaches a transcript.
const redact = (s) => String(s).replace(/[A-Za-z0-9_\-.]{24,}/g, '[long]');
const portFile = `${process.env.LOCALAPPDATA}/Google/Chrome/User Data/DevToolsActivePort`;
const [port, path] = readFileSync(portFile, 'utf8').trim().split(/\r?\n/);

const ws = new WebSocket(`ws://127.0.0.1:${port}${path}`);
let nextId = 1;
const pending = new Map();
const send = (method, params = {}, sessionId) =>
  new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params, sessionId }));
  });
ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data);
  if (!msg.id || !pending.has(msg.id)) return;
  const { resolve, reject } = pending.get(msg.id);
  pending.delete(msg.id);
  if (msg.error) reject(new Error(msg.error.message));
  else resolve(msg.result);
};

await new Promise((resolve, reject) => {
  ws.onopen = resolve;
  ws.onerror = () => reject(new Error('websocket error'));
});
const { targetId } = await send('Target.createTarget', { url: 'about:blank', background: true });
const { sessionId: session } = await send('Target.attachToTarget', { targetId, flatten: true });
await send('Page.enable', {}, session);
console.log(`CONNECTED; bridge on ${PORT}`);

const evalPage = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, session);
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
  return r.result.value;
};
const goto = async (url, settleMs = 6000) => {
  await send('Page.navigate', { url }, session);
  await new Promise((resolve) => setTimeout(resolve, settleMs));
};

const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
http
  .createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    if (body.trim() === 'EXIT') {
      await send('Target.closeTarget', { targetId }).catch(() => {});
      res.end('bye');
      ws.close();
      setTimeout(() => process.exit(0), 300);
      return;
    }
    try {
      const result = await new AsyncFunction('send', 'evalPage', 'goto', 'session', body)(send, evalPage, goto, session);
      res.end(redact(JSON.stringify({ ok: true, result }, null, 1)));
    } catch (error) {
      res.end(redact(JSON.stringify({ ok: false, error: String(error?.message ?? error) })));
    }
  })
  .listen(PORT, '127.0.0.1');
