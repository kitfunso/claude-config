---
name: claude-code-realtime
description: Bridge Claude Code to another agent, script, or workflow via a JSONL mailbox for `claude -p`.
disable-model-invocation: true
---

# Claude Code Realtime

Use a project-local mailbox when another process needs to communicate with Claude Code without driving the interactive TUI.

## Protocol

- Mailbox default: `.claude-realtime/`.
- Send requests by appending JSON lines to `inbox.jsonl`.
- Read replies from `outbox.jsonl`.
- Each request should include:
  - `id`: stable unique id.
  - `prompt`: message for Claude Code.
  - `cwd`: optional working directory.
  - `system`: optional extra instruction text.

Example request:

```json
{"id":"smoke-001","prompt":"Run the test suite and summarize failures.","cwd":"C:\\path\\to\\repo"}
```

## Workflow

1. Start the bridge from a terminal:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Start-ClaudeRealtimeBridge.ps1
```

2. Send a request:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Send-ClaudeRealtimeMessage.ps1 -Prompt "Inspect the repo and report the riskiest failing test."
```

3. Tail replies:

```powershell
Get-Content .\.claude-realtime\outbox.jsonl -Wait
```

## Operating Rules

- Treat the bridge as near-realtime, not as a long-lived shared conversation. Each request invokes `claude -p`.
- Keep prompts self-contained; include relevant paths and expected output shape.
- For automation, request JSON output from the prompt itself when the caller needs machine-readable results.
- Stop after repeated CLI/auth failures and surface the raw error from `outbox.jsonl`.
