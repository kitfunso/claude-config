"""Fast browser launcher: TypeSafe Jev driving a dedicated Chrome via Browser Harness.

Run: uv run --project C:/Users/skf_s/tools/jev-ultrafast python C:/Users/skf_s/.claude/scripts/fast_browser.py \
    --url URL --goal "TEXT" [--say "exact text"]... [--max-steps 25] [--check] [--selftest]
"""
import argparse
import json
import os
import subprocess
import sys
import time
import winreg
import urllib.request
from typing import Callable
from urllib.parse import urlparse

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE_DIR = r"C:\Users\skf_s\tools\fast-browser-profile"
CDP_PORT = 9333
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
KEY_NAME = "TYPESAFE_API_KEY"
# The 0.5 cut-off below was tuned on this version; the jev-latest alias moves without notice.
JEV_MODEL = "jev-1.13.0"
DENY_HOST_PARTS = ("ramsky",)
TEXT_LIMIT = 2000
# the clone lists only on-screen elements and its rules never mention scrolling, so Jev said BLOCKED
SCROLL_RULE = (
    "\nOnly controls inside the visible viewport are listed. If the control the goal needs is not"
    " listed and SCROLL_DOWN is offered, choose SCROLL_DOWN before BLOCKED."
)


class NeedsSay(Exception):
    """A TYPE_TEXT step needed a --say value this run does not have."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def read_key(name: str) -> bool:
    """Load one key into os.environ from the process env or HKCU\\Environment. Never prints it."""
    if os.environ.get(name):
        return True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as hive:
            value, _ = winreg.QueryValueEx(hive, name)
    except OSError:
        return False
    if not value:
        return False
    os.environ[name] = value
    return True


def cdp_alive(timeout: float = 1.0) -> bool:
    """True when the dedicated Chrome's CDP endpoint answers."""
    try:
        urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=timeout).read()
        return True
    except OSError:
        return False


def start_chrome() -> bool:
    """Launch the dedicated automation Chrome and wait up to 10s for its CDP port."""
    subprocess.Popen(
        [
            CHROME_EXE,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={PROFILE_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if cdp_alive():
            return True
        time.sleep(0.3)
    return False


def ensure_chrome() -> bool:
    return cdp_alive() or start_chrome()


def denied(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(part in host for part in DENY_HOST_PARTS)


def emit(payload: dict) -> None:
    print(json.dumps(payload), flush=True)


def pick_say_value(candidates: list[str], context: dict) -> str | None:
    """One TypeSafe choice request: which remaining --say value fits this field."""
    from jev_ultrafast.model import post_json, validate_choice

    options = {str(i + 1): {"text": v} for i, v in enumerate(candidates)}
    options["none"] = {"text": "None of these values fit this field."}
    field = context.get("field", {})
    body = {
        "model": os.environ.get("TYPESAFE_MODEL", JEV_MODEL),
        "state": {"goal": context.get("goal"), "field": field},
        "questions": {
            "say_choice": {
                "type": "choice",
                "criteria": options,
                "instructions": {
                    "goal": context.get("goal"),
                    "field": field,
                    "rules": "Pick the value that belongs in this field, or none if nothing fits.",
                },
            }
        },
    }
    result = post_json("https://api.typesafe.ai/v1/systemone", os.environ[KEY_NAME], body)
    answer = validate_choice(result["answers"]["say_choice"], set(options))
    if answer["choice"] == "none" or answer["confidence"] < 0.5:
        return None
    return candidates[int(answer["choice"]) - 1]


def make_writer(
    say_values: list[str], chooser: Callable[[list[str], dict], str | None] = pick_say_value
) -> Callable[[dict], tuple[str, dict]]:
    """Drop-in replacement for jev_ultrafast.model.field_text: no second model, caller supplies text."""
    remaining = list(say_values)

    def writer(context: dict) -> tuple[str, dict]:
        if not remaining:
            raise NeedsSay("needs --say text")
        if len(remaining) == 1:
            return remaining.pop(0), {"model": "say-literal", "latency_ms": 0}
        picked = chooser(remaining, context)
        if picked is None:
            raise NeedsSay("no --say value fits")
        remaining.remove(picked)
        return picked, {"model": "say-choice", "latency_ms": 0}

    return writer


def run_check() -> int:
    """Free self-check: no TypeSafe call, no Agent run."""
    key_ok = read_key(KEY_NAME)
    chrome_found = os.path.isfile(CHROME_EXE)
    cdp_up = ensure_chrome()
    attach_ok = False
    if cdp_up:
        os.environ["BU_CDP_URL"] = CDP_URL
        os.environ["BU_NAME"] = "fastbrowser"
        try:
            from browser_harness.admin import ensure_daemon
            from browser_harness.helpers import current_tab

            ensure_daemon()
            current_tab()
            attach_ok = True
        except Exception as exc:
            attach_ok = False
            print(f"attach failed: {type(exc).__name__}: {exc}", file=sys.stderr)
    report = {
        KEY_NAME: key_ok,
        "chrome_exe_found": chrome_found,
        "cdp_port_answering": cdp_up,
        "harness_attach_ok": attach_ok,
    }
    emit(report)
    return 0 if all(report.values()) else 1


def run_agent(url: str, goals: list[str], max_steps: int, say_values: list[str]) -> int:
    # browser_harness reads BU_NAME once at import, so set it before the import below
    os.environ["BU_CDP_URL"] = CDP_URL
    os.environ["BU_NAME"] = "fastbrowser"
    import jev_ultrafast.agent as agent_module
    import jev_ultrafast.model as model_module

    agent_module.field_text = make_writer(say_values)
    model_module.NEXT_ACTION += SCROLL_RULE
    started = time.perf_counter()
    steps = 0
    status = "ERROR"
    reason = None
    final_url = url
    try:
        with agent_module.Agent(url, goals) as agent:
            for state in agent.run():
                steps += 1
                final_url = state["page"]["url"]
                last = state["history"][-1] if state["history"] else {}
                emit(
                    {
                        "elapsed_ms": state["elapsed_ms"],
                        "status": state["status"],
                        "operation": last.get("operation"),
                        "target": last.get("target"),
                        "action": str(last.get("action") or "")[:60],
                    }
                )
                if steps >= max_steps:
                    status = "MAX_STEPS"
                    break
            else:
                status = "DONE" if agent.state["status"] == "done" else "BLOCKED"
                final_url = agent.state["page"]["url"]
    except NeedsSay as exc:
        status, reason = "BLOCKED", exc.reason
        final_url = agent.state["page"]["url"]
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        emit(
            {
                "status": "ERROR",
                "steps": steps,
                "elapsed_ms": elapsed_ms,
                "url": final_url,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        )
        return 3
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    final = {"status": status, "steps": steps, "elapsed_ms": elapsed_ms, "url": final_url}
    if reason:
        final["reason"] = reason
    # the agent closes its tab on exit, so the last observed text is the caller's only outcome check
    final["page_text"] = str(agent.state["page"].get("text", ""))[:TEXT_LIMIT]
    emit(final)
    return 0 if status == "DONE" else 3


def run_selftest() -> int:
    """Free logic check of make_writer with a fake chooser. No network, no Agent."""
    calls = []

    def fake_chooser(candidates: list[str], context: dict) -> str | None:
        calls.append(list(candidates))
        return candidates[0]

    def none_chooser(candidates: list[str], context: dict) -> str | None:
        calls.append(list(candidates))
        return None

    checks = []
    writer = make_writer([], chooser=fake_chooser)
    try:
        writer({})
        checks.append(("zero values -> NeedsSay", False))
    except NeedsSay as exc:
        checks.append(("zero values -> NeedsSay", exc.reason == "needs --say text"))

    writer = make_writer(["only-one"], chooser=fake_chooser)
    value, _ = writer({})
    checks.append(("one value -> used, no chooser call", value == "only-one" and calls == []))

    calls.clear()
    writer = make_writer(["a", "b", "c"], chooser=fake_chooser)
    value, _ = writer({})
    checks.append(("several values -> chooser called once", value == "a" and len(calls) == 1))

    writer = make_writer(["a", "b"], chooser=none_chooser)
    try:
        writer({})
        checks.append(("none -> BLOCKED", False))
    except NeedsSay as exc:
        checks.append(("none -> BLOCKED", exc.reason == "no --say value fits"))

    ok = True
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
        ok = ok and passed
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--goal", action="append")
    parser.add_argument("--say", action="append", default=[])
    parser.add_argument("--max-steps", type=int, default=25)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    # jev_ultrafast/model.py reads the same variable, so one line pins every call in the run
    os.environ.setdefault("TYPESAFE_MODEL", JEV_MODEL)

    if args.selftest:
        return run_selftest()
    if args.check:
        return run_check()

    if not args.url or not args.goal:
        emit({"status": "ERROR", "error_type": "ValueError", "error_message": "--url and --goal are required"})
        return 3
    if denied(args.url):
        emit({"status": "REFUSED", "reason": "denied host"})
        return 4
    if not read_key(KEY_NAME):
        emit({"status": "NO_KEY", "missing": [KEY_NAME]})
        return 2
    if not ensure_chrome():
        emit(
            {
                "status": "ERROR",
                "error_type": "RuntimeError",
                "error_message": "dedicated Chrome CDP port did not come up",
            }
        )
        return 3
    return run_agent(args.url, args.goal, args.max_steps, args.say)


if __name__ == "__main__":
    sys.exit(main())
