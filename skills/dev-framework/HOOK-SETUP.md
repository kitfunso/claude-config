# settings.json hook setup (manual)

To auto-fire `phase-capture` (which fires `hippo capture` on phase transitions), add this hook block to your `~/.claude/settings.json` under `hooks`:

## Option A â€” Stop hook (recommended, fires once per agent turn)

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "powershell -ExecutionPolicy Bypass -File C:/Users/kit.sofun/.claude/skills/dev-framework/scripts/phase-capture.ps1"
          }
        ]
      }
    ]
  }
}
```

If you already have a `Stop` hook array, append the new entry to it â€” do not overwrite.

**Behavior**: runs once per agent turn. Silent when phase is stable. Captures to hippo when phase transitions (DISCOVER â†’ SCAFFOLD, EXECUTE â†’ VERIFY, etc.).

## Option B â€” PostToolUse on git commit (fires per commit, more granular)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "powershell -ExecutionPolicy Bypass -File C:/Users/kit.sofun/.claude/skills/dev-framework/scripts/phase-capture.ps1"
          }
        ]
      }
    ]
  }
}
```

**Caveat**: fires after EVERY Bash command, not just `git commit`. The script handles no-op silently but adds tool-call overhead. Prefer Option A unless you need per-commit granularity.

## Manual fallback (no hook)

Run on demand whenever you finish a phase:
```powershell
powershell -File C:/Users/kit.sofun/.claude/skills/dev-framework/scripts/phase-capture.ps1
```

## How to verify the hook is working

1. Add the hook to settings.json
2. Run any agent task that changes phase (e.g. create `PRD.md` in a discovery project â†’ moves to SCAFFOLD)
3. Check the state file:
   ```powershell
   Get-Content C:/Users/kit.sofun/.claude/dev-framework-state.txt
   ```
4. Check hippo for the capture:
   ```bash
   hippo recall "phase transition"
   ```

## Removal

Delete the hook block from `~/.claude/settings.json` and delete the state file:
```powershell
Remove-Item C:/Users/kit.sofun/.claude/dev-framework-state.txt
```
