#!/usr/bin/env python3
"""Resource tripwire: UserPromptSubmit + PreToolUse (Bash|PowerShell).

Backstop for the pinned campaign rule (alphanova cycle 2: 47 serial shell calls of
the full runner, 0 skills, 0 agents). Reads the transcript and counts tool calls.
- UserPromptSubmit: warns once TOOL_CALL_FLOOR calls pass with no Skill, Agent
  or Workflow call, and reports per-repo tripwire counts and the next audit due.
- PreToolUse: for a command matching a rule in the nearest `.claude/tripwires.json`,
  denies when the protocol file is missing, and denies run N*every (and every run
  after it) until `AUDIT <sid8> #N` exists in the rule's audit file.
`--count <transcript> [pattern]` prints the counters, for evidence files.
Contract: hook JSON on stdin, hook JSON on stdout, always exits 0.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TOOL_CALL_FLOOR = 40
SHELL_TOOLS = {"Bash", "PowerShell"}
LEVERAGE_TOOLS = ("Skill", "Agent", "Workflow")
MAX_WALK_UP = 6
ABS_PATH = re.compile(r"(?:[A-Za-z]:[/\\]|/[a-z]/)[^\s\"'|;&]+")


def load_tool_uses(transcript: Path) -> list[dict]:
    blocks: list[dict] = []
    try:
        fh = transcript.open(encoding="utf-8", errors="replace")
    except OSError:
        return blocks
    with fh:
        for line in fh:
            if '"tool_use"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    blocks.append(block)
    return blocks


def count_tools(blocks: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for block in blocks:
        name = str(block.get("name") or "?")
        counts[name] = counts.get(name, 0) + 1
    return counts


def count_matches(blocks: list[dict], pattern: str, exclude_id: str | None = None) -> int:
    pat = re.compile(pattern)
    n = 0
    for block in blocks:
        if block.get("name") not in SHELL_TOOLS or block.get("id") == exclude_id:
            continue
        cmd = (block.get("input") or {}).get("command")
        if isinstance(cmd, str) and pat.search(cmd):
            n += 1
    return n


def to_windows(path: str) -> str:
    m = re.match(r"^/([a-z])/(.*)$", path)
    return f"{m.group(1).upper()}:/{m.group(2)}" if m else path


def find_tripwires(cwd: str | None, command: str = "") -> tuple[Path | None, dict | None]:
    """Walk up from cwd and from every absolute path named in the command."""
    starts = [cwd] if cwd else []
    starts += [to_windows(p) for p in ABS_PATH.findall(command)]
    seen: set[Path] = set()
    for start in starts:
        d = Path(start)
        if not d.is_dir():
            d = d.parent
        for _ in range(MAX_WALK_UP):
            if d in seen:
                break
            seen.add(d)
            f = d / ".claude" / "tripwires.json"
            if f.is_file():
                try:
                    return d, json.loads(f.read_text(encoding="utf-8"))
                except ValueError:
                    return d, None
            if d.parent == d:
                break
            d = d.parent
    return None, None


def marker_present(root: Path, rule: dict, marker: str) -> bool:
    audit = root / str(rule.get("audit_file", ""))
    if not audit.is_file():
        return False
    return marker in audit.read_text(encoding="utf-8", errors="replace")


def deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def pre_tool_use(payload: dict) -> dict | None:
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not isinstance(command, str) or not command:
        return None
    root, cfg = find_tripwires(payload.get("cwd"), command)
    if root is None or not isinstance(cfg, dict):
        return None
    rules = [r for r in cfg.get("rules", []) if re.search(str(r.get("pattern", "(?!)")), command)]
    if not rules:
        return None
    protocol = cfg.get("protocol_file")
    if protocol and not (root / protocol).is_file():
        return deny(f"[TRIPWIRE] {root / protocol} is missing. A campaign run needs the protocol "
                    "file first: load /quant-ml-protocol, write Stage 0 (sample-size math, "
                    "decision rule, registry), then re-run.")
    blocks = load_tool_uses(Path(payload.get("transcript_path") or ""))
    sid = str(payload.get("session_id") or "session")[:8]
    for rule in rules:
        every = int(rule.get("every", 0) or 0)
        if every <= 0:
            continue
        # The transcript does not yet hold this call when PreToolUse fires (measured Sep-2).
        n = count_matches(blocks, str(rule["pattern"]), exclude_id=payload.get("tool_use_id")) + 1
        k = n // every
        if k == 0:
            continue
        marker = f"AUDIT {sid} #{k}"
        if marker_present(root, rule, marker):
            continue
        name = rule.get("name", rule["pattern"])
        return deny(
            f"[TRIPWIRE {name}] This would be run {n} of '{rule['pattern']}' this session; "
            f"{every} runs = one Stage 5.6 self-audit. Append a line starting `{marker}` to "
            f"{root / rule.get('audit_file', '')} covering all four categories (data, statistics, "
            "code, process) and naming the new input or mechanism the next run tests. Ten runs "
            "of one construct with no new input = stop (pinned rule). Then re-run."
        )
    return None


def user_prompt_submit(payload: dict) -> dict | None:
    blocks = load_tool_uses(Path(payload.get("transcript_path") or ""))
    counts = count_tools(blocks)
    total = sum(counts.values())
    leverage = {t: counts.get(t, 0) for t in LEVERAGE_TOOLS}
    notes: list[str] = []
    if total >= TOOL_CALL_FLOOR and sum(leverage.values()) == 0:
        notes.append(f"[RESOURCE TRIPWIRE] {total} tool calls this session, Skill 0, Agent 0, "
                     "Workflow 0. Forty or more calls with no skill or agent is a defect (pinned "
                     "rule). Load the skill that fits the task, or delegate the width to Sonnet "
                     "sub-agents, before the next run.")
    root, cfg = find_tripwires(payload.get("cwd"))
    if root is not None and isinstance(cfg, dict):
        sid = str(payload.get("session_id") or "session")[:8]
        for rule in cfg.get("rules", []):
            every = int(rule.get("every", 0) or 0)
            n = count_matches(blocks, str(rule.get("pattern", "(?!)")))
            if not n or every <= 0:
                continue
            k = n // every
            name = rule.get("name", rule.get("pattern"))
            audit = root / str(rule.get("audit_file", ""))
            if k and not marker_present(root, rule, f"AUDIT {sid} #{k}"):
                notes.append(f"[TRIPWIRE {name}] {n} runs this session and audit #{k} is OVERDUE: "
                             f"the next matching run is denied until `AUDIT {sid} #{k}` exists "
                             f"in {audit}.")
            else:
                notes.append(f"[TRIPWIRE {name}] {n} runs this session; audit #{k + 1} "
                             f"(`AUDIT {sid} #{k + 1}` in {audit}) is due at run {(k + 1) * every}.")
    if not notes:
        return None
    return {"suppressOutput": True,
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                   "additionalContext": "\n".join(notes)}}


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "--count":
        blocks = load_tool_uses(Path(sys.argv[2]))
        out: dict = {"tools": count_tools(blocks), "total": len(blocks)}
        if len(sys.argv) > 3:
            out["pattern"] = sys.argv[3]
            out["pattern_runs"] = count_matches(blocks, sys.argv[3])
        print(json.dumps(out, indent=1, sort_keys=True))
        return
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    event = payload.get("hook_event_name")
    if event is None:
        event = "UserPromptSubmit" if "prompt" in payload else "PreToolUse"
    if event == "UserPromptSubmit":
        out = user_prompt_submit(payload)
    elif event == "PreToolUse" and payload.get("tool_name") in SHELL_TOOLS:
        out = pre_tool_use(payload)
    else:
        out = None
    if out:
        print(json.dumps(out))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--count":
        main()
        sys.exit(0)
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
