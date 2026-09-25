#!/usr/bin/env python3
"""Resource tripwire: UserPromptSubmit + PreToolUse (Bash|PowerShell).

Backstop for the pinned campaign rule (alphanova cycle 2: 47 serial shell calls of
the full runner, 0 skills, 0 agents). Reads the transcript and counts tool calls.
- UserPromptSubmit: warns once TOOL_CALL_FLOOR calls pass with no Skill, Agent
  or Workflow call, and reports per-repo tripwire counts and the next audit due.
- PreToolUse: for a command matching a rule in the nearest `.claude/tripwires.json`,
  denies when the protocol file is missing, and denies run N*every (and every run
  after it) until `AUDIT <sid8> #N` exists in the rule's audit file.
- PreToolUse, Fable orchestrator: on a Fable main thread, denies exec tools (shell,
  edits, browser) past FABLE_EXEC_BUDGET calls since the last human message or the
  last Agent spawn. Sub-agents (payload carries agent_id) are never counted.
  Measured 2026-09-12: 1,656 Fable requests in a day, all main thread, 0 delegated.
`--count <transcript> [pattern]` prints the counters, for evidence files.
Contract: hook JSON on stdin, hook JSON on stdout, always exits 0.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
try:
    from record_component import record
except Exception:  # the recorder is optional, the deny is not
    def record(**_: object) -> None:
        return None

TOOL_CALL_FLOOR = 40
SHELL_TOOLS = {"Bash", "PowerShell"}
LEVERAGE_TOOLS = ("Skill", "Agent", "Workflow")
EXEC_TOOLS = {"Bash", "PowerShell", "Edit", "Write", "MultiEdit", "NotebookEdit"}
EXEC_PREFIXES = ("mcp__claude-in-chrome__", "mcp__playwright__")
FABLE_EXEC_BUDGET = os.environ.get("CLAUDE_FABLE_EXEC_BUDGET") or "25"
MODEL_RE = re.compile(rb'"model"\s*:\s*"([^"]+)"')
TYPE_RE = re.compile(rb'"type"\s*:\s*"(user|assistant)"')
CACHE_VERSION = 2  # v2 caches carry __user__ and __model__ marker blocks
MAX_WALK_UP = 6
ABS_PATH = re.compile(r"(?:[A-Za-z]:[/\\]|/[a-z]/)[^\s\"'|;&]+")
CACHE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "cache" / "tripwire"
CACHE_TTL_DAYS = 7
# The harness kills the hook at its configured timeout and throws the output away, so
# a busy box costs a partial scan here rather than a lost notice. See docs/incidents.md.
DEADLINE = time.monotonic() + float(os.environ.get("TRIPWIRE_BUDGET_S") or 6.0)


def prune(cache_dir: Path) -> None:
    """One cache file per session accumulates forever otherwise."""
    cutoff = time.time() - CACHE_TTL_DAYS * 86400
    for stale in cache_dir.glob("*.json"):
        try:
            if stale.stat().st_mtime < cutoff:
                stale.unlink()
        except OSError:
            pass


def slim(block: dict) -> dict:
    """Only the fields the counters read; the transcript stays the source of truth."""
    name = block.get("name")
    out: dict = {"name": name, "id": block.get("id")}
    cmd = (block.get("input") or {}).get("command")
    if name in SHELL_TOOLS and isinstance(cmd, str):
        out["input"] = {"command": cmd}
    return out


def human_turn(raw: bytes) -> bool:
    """A user line that is not a tool result and not a background task notification."""
    try:
        content = ((json.loads(raw).get("message") or {}).get("content"))
    except ValueError:
        return False
    if isinstance(content, str):
        return True
    if isinstance(content, list) and content and isinstance(content[0], dict):
        text = content[0].get("text")
        return isinstance(text, str) and not text.lstrip().startswith("<task-notification>")
    return False


def current_model(blocks: list[dict]) -> str:
    for block in reversed(blocks):
        if block.get("name") == "__model__":
            return str(block.get("id") or "")
    return ""


def scan(data: bytes, blocks: list[dict]) -> int:
    """Parse whole lines until the deadline; returns the bytes actually consumed."""
    used = 0
    model = current_model(blocks)
    for i, raw in enumerate(data.split(b"\n")):
        if not i % 5000 and time.monotonic() > DEADLINE:
            break
        used += len(raw) + 1
        kind = TYPE_RE.search(raw)
        if kind and kind.group(1) == b"user":
            if b'"tool_result"' not in raw and human_turn(raw):
                blocks.append({"name": "__user__"})
            continue
        if kind:
            m = MODEL_RE.search(raw)
            if m and m.group(1).decode("utf-8", "replace") != model:
                model = m.group(1).decode("utf-8", "replace")
                blocks.append({"name": "__model__", "id": model})
        if b'"tool_use"' not in raw:
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                blocks.append(slim(block))
    return min(used, len(data))


def load_tool_uses(transcript: Path) -> list[dict]:
    """Parse only the bytes appended since the last call, keyed on a byte offset.

    A full re-parse ran on every prompt and every shell call and scaled with the
    transcript, which reaches 200MB+ here. See docs/incidents.md (2026-09-06).
    """
    try:
        size = transcript.stat().st_size
    except OSError:
        return []
    cache = CACHE_DIR / f"{transcript.stem}.json"
    blocks: list[dict] = []
    offset = 0
    try:
        state = json.loads(cache.read_text(encoding="utf-8"))
        if isinstance(state["blocks"], list) and 0 <= state["offset"] <= size:
            blocks, offset = state["blocks"], state["offset"]
            if state.get("v") != CACHE_VERSION:  # pre-marker cache: the exec budget starts now
                blocks.append({"name": "__user__"})
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if offset == size:
        return blocks
    try:
        with transcript.open("rb") as fh:
            fh.seek(offset)
            data = fh.read()
    except OSError:
        return blocks
    cut = data.rfind(b"\n") + 1  # a half-written trailing line is re-read next call
    offset += scan(data[:cut], blocks)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        prune(CACHE_DIR)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps({"offset": offset, "blocks": blocks, "v": CACHE_VERSION}), encoding="utf-8")
        os.replace(tmp, cache)
    except OSError:
        pass
    return blocks


def count_tools(blocks: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for block in blocks:
        name = str(block.get("name") or "?")
        if name.startswith("__"):
            continue
        counts[name] = counts.get(name, 0) + 1
    return counts


def is_exec(name: object) -> bool:
    return name in EXEC_TOOLS or str(name).startswith(EXEC_PREFIXES)


def exec_calls_this_leg(blocks: list[dict]) -> int:
    """Exec calls since the last human message or the last Agent spawn, whichever is later."""
    n = 0
    for block in reversed(blocks):
        name = block.get("name")
        if name == "__user__" or name == "Agent":
            break
        if is_exec(name):
            n += 1
    return n


def fable_guard(payload: dict, blocks: list[dict]) -> dict | None:
    """Fable orchestrates; a Sonnet sub-agent grinds. Sub-agent calls carry agent_id."""
    if payload.get("agent_id") or FABLE_EXEC_BUDGET.lower() == "off":
        return None
    if "fable" not in current_model(blocks).lower():
        return None
    try:
        budget = int(FABLE_EXEC_BUDGET)
    except ValueError:
        budget = 25
    n = exec_calls_this_leg(blocks) + 1  # the transcript does not yet hold this call
    if n <= budget:
        return None
    return deny(
        f"[FABLE ORCHESTRATOR] Exec call {n} on the Fable main thread since the last user "
        f"message or Agent spawn (budget {budget}). Fable reads, decides and briefs; the grind "
        "goes to a Sonnet sub-agent. Brief one Agent (model sonnet) with the remaining "
        "commands, the files, and the pass/fail check, then take its report. Each Agent spawn "
        "resets the budget. CLAUDE_FABLE_EXEC_BUDGET=off disables this guard."
    )


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
    tool = payload.get("tool_name")
    transcript = Path(payload.get("transcript_path") or "")
    blocks: list[dict] | None = None
    if is_exec(tool) and not payload.get("agent_id"):
        blocks = load_tool_uses(transcript)
        out = fable_guard(payload, blocks)
        if out:
            return out
    if tool not in SHELL_TOOLS:
        return None
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
                    "file first: load /quant-ml-protocol, write its plan page with stage 0 "
                    "(prior art) and stage 1 (framing, target and power) closed, then re-run.")
    if blocks is None:
        blocks = load_tool_uses(transcript)
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
    if "fable" in current_model(blocks).lower() and FABLE_EXEC_BUDGET.lower() != "off":
        notes.append(f"[FABLE ORCHESTRATOR] Fable main thread: {FABLE_EXEC_BUDGET} exec calls per "
                     "turn or per Agent spawn, then the hook denies. Brief Sonnet sub-agents "
                     "for shell, edit and browser grind; keep reads and decisions here.")
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
    elif event == "PreToolUse":
        out = pre_tool_use(payload)
    else:
        out = None
    if out:
        decision = out.get("hookSpecificOutput") or {}
        if decision.get("permissionDecision") == "deny":
            record(kind="hook", name=Path(__file__).name, session_id=payload.get("session_id"),
                   cwd=payload.get("cwd"), blocked=True, notes=decision.get("permissionDecisionReason"))
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
