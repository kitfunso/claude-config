#!/usr/bin/env node
// Classic command hooks: function-hook mods can be switched off remotely (tengu_plugin_hooks_modules), these cannot.
import { readFileSync } from 'node:fs'

import { HOW, board, guard } from '../lib/core.mjs'
import { repoOf } from '../lib/repo.mjs'
import { endSession, list, sessionInfo, touch } from '../lib/store.mjs'

// Only commands that can create, push, tag, merge or publish pay for the git lookups.
const RELEVANT = /\b(git|gh|npm)\b[\s\S]*\b(push|checkout|switch|branch|worktree|tag|create|merge|version|publish)\b/
const TOUCH_EVERY_MS = 5 * 60_000

const emit = (event, fields) => process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: event, ...fields } }))

function freshen(sid, cwd) {
  const seen = sessionInfo(sid)?.seen ?? 0
  if (Date.now() - seen > TOUCH_EVERY_MS) touch(sid, cwd)
}

function sessionStart(sid, cwd) {
  touch(sid, cwd)
  const repo = repoOf(cwd)
  if (repo !== undefined) emit('SessionStart', { additionalContext: `${board(list(repo), sid, repo)}\n${HOW}` })
}

function preToolUse(sid, cwd, input) {
  freshen(sid, cwd)
  const command = input.tool_input?.command
  if (input.tool_name !== 'Bash' || typeof command !== 'string' || !RELEVANT.test(command)) return
  const verdict = guard(command, sid, cwd)
  if (!verdict.allow) emit('PreToolUse', { permissionDecision: 'deny', permissionDecisionReason: verdict.text })
}

const input = JSON.parse(readFileSync(0, 'utf8'))
const { session_id: sid, cwd } = input
if (sid && process.env.CLAUDE_COORD !== 'off') {
  const event = input.hook_event_name
  if (event === 'SessionStart') sessionStart(sid, cwd)
  else if (event === 'PreToolUse') preToolUse(sid, cwd, input)
  else if (event === 'UserPromptSubmit') freshen(sid, cwd)
  else if (event === 'SessionEnd') endSession(sid)
}
