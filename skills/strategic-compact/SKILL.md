---
name: strategic-compact
description: Guide for using /compact at phase transitions - research to planning to implementation - or when context is large or stale.
---

# Strategic Compact

Compact at **phase transitions**, not arbitrary token thresholds. The goal is to shed bulk while preserving what matters for the next phase.

## When to Compact

| Transition | Compact? | Why |
|---|---|---|
| Research → Planning | YES | Research is bulky; the plan is the distilled output |
| Planning → Implementation | YES | Plan is saved to file/TodoWrite; free context for code |
| After completing a milestone | YES | Fresh start for the new phase |
| Mid-implementation | NO | Losing variable names, paths, and reasoning is costly |
| Debugging → Next feature | YES | Clear dead-end traces and stack traces |
| Before context shift | YES | Clear exploration before switching to different task |

## What Survives Compaction
- CLAUDE.md instructions
- Memory files
- Git state awareness
- TodoWrite task lists

## What Gets Lost
- Intermediate reasoning and exploration
- File contents you read (must re-read)
- Conversation context and corrections
- Tool call history and error traces

## Best Practice
1. **Save your plan** to a file or TodoWrite BEFORE compacting
2. Compact with a descriptive message: `/compact Completed research phase. Plan saved to TODO. Starting implementation.`
3. After compacting, re-read any files you'll need for the next phase
