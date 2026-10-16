# Driving Keith's signed-in Chrome with no clicks from him

Use this when a task needs his logged-in Chrome and the Claude in Chrome tools are not in
the session. It is never a release route: releases start from `release-*` tags.

1. Start the bridge in the background: `node ~/.claude/scripts/chrome/bridge.mjs`.
2. Chrome shows "Allow remote debugging?". Press it yourself:
   `powershell -File ~/.claude/scripts/chrome/allow.ps1`. Keith asked for this
   (2026-10-16); never wait for his click.
3. POST a JS function body to `http://127.0.0.1:9557`. It runs with `goto(url)`,
   `evalPage(expression)`, `send(method, params, session)` and `session` in scope. Every
   reply hides strings of 24 or more characters.
4. POST `EXIT` to close the tab and disconnect. Never close his other tabs.

Two traps from 2026-10-16:
- UIA `Invoke` on Allow only moves focus. The prompt stays up, so `allow.ps1` clicks with the mouse.
- Playwright `connectOverCDP` hung after Allow because it attaches to every open tab. The bridge
  opens and attaches only its own tab.
