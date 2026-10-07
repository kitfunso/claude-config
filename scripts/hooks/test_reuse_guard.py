#!/usr/bin/env python3
"""Self-check for the reuse guard: `python test_reuse_guard.py`."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reuse_guard", HERE / "reuse_guard.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def write(path: Path, content: str, session: str = "s1") -> dict | None:
    return gate.decide({"tool_name": "Write", "session_id": session,
                        "tool_input": {"file_path": str(path), "content": content}})


def edit(path: Path, old: str, new: str, session: str = "s1") -> dict | None:
    return gate.decide({"tool_name": "Edit", "session_id": session,
                        "tool_input": {"file_path": str(path), "old_string": old, "new_string": new}})


def denied(out: dict | None) -> str:
    spec = (out or {}).get("hookSpecificOutput", {})
    return spec.get("permissionDecisionReason", "") if spec.get("permissionDecision") == "deny" else ""


def reminded(out: dict | None) -> str:
    return (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")


def repo(tmp: Path) -> Path:
    """Today's case: spread-carry with sc/book.py and strat_page.py, no .git."""
    root = tmp / "spread-carry"
    (root / "sc").mkdir(parents=True)
    (root / "seasonal").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n")
    (root / "sc" / "book.py").write_text(
        "import math\n\ndef interval(x, block):\n    pass\n\ndef sharpe(x):\n    pass\n")
    (root / "strat_page.py").write_text("def with_holm(d, rows):\n    pass\n\ndef main():\n    pass\n")
    (root / "web").mkdir()
    (root / "web" / "chart.ts").write_text("export function drawChart(el: Element) {}\n")
    (tmp / "other.py").write_text("def unrelated_outside(x):\n    pass\n")
    return root


def main() -> None:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        gate.LOG = tmp / "state" / "reuse_guard.jsonl"
        root = repo(tmp)
        perf = root / "seasonal" / "perf.py"
        body = ("def sharpe(x):\n    pass\n\ndef interval(x, year):\n    pass\n\n"
                "def with_holm(rows):\n    pass\n\ndef main():\n    pass\n")
        reason = denied(write(perf, body))
        for hit in ("sharpe (sc/book.py:6)", "interval (sc/book.py:3)", "with_holm (strat_page.py:1)"):
            assert hit in reason, f"today's perf.py must name {hit}: {reason}"
        assert "main" not in reason.split("defines:")[1], "entry points must not count"
        assert write(perf, body) is None, "the same write again must pass"
        assert denied(write(perf, body, session="s2")), "a new session must deny again"

        fresh = root / "seasonal" / "fresh.py"
        assert "[REUSE]" in reminded(write(fresh, "def novel_metric(x):\n    pass\n")), "new file reminder"
        assert write(root / "seasonal" / "fresh2.py", "def other_new(x):\n    pass\n") is None, \
            "the reminder fires once per session per repo"
        assert write(fresh, "def row(x):\n    pass\n", session="s3") is not None, "short names pass to the reminder"
        assert not denied(write(root / "x.py", "def row(x):\n    pass\n", session="s4")), "short names never deny"
        assert not denied(write(root / "y.py", "def unrelated_outside(x):\n    pass\n")), \
            "files outside the repo root are not searched"

        lib = root / "sc" / "lib.py"
        lib.write_text("def keep(x):\n    pass\n")
        assert denied(edit(lib, "def keep(x):", "def keep(x):\n    pass\n\ndef sharpe(x):")), \
            "an Edit adding a known name must deny"
        assert edit(lib, "def sharpe(x):\n    pass", "def sharpe(x):\n    return 1") is None, \
            "an Edit that keeps an existing def must pass"

        ui = root / "web" / "ui.js"
        assert "drawChart (web/chart.ts:1)" in denied(write(ui, "const drawChart = (el) => el;\n")), \
            "JS and TS share a family"
        assert not denied(write(root / "web" / "z.js", "function interval(a) {}\n", session="s5")), \
            "a Python def never clashes with JS"

        for i in range(4):
            (root / f"view_{i}.py").write_text("def render_page(st):\n    pass\n")
        assert not denied(write(root / "view_new.py", "def render_page(st):\n    pass\n", session="s7")), \
            "a name four other files define is a convention"
        (root / "view_0.py").unlink()
        assert denied(write(root / "view_new.py", "def render_page(st):\n    pass\n", session="s8")), \
            "three other definitions still deny"
        (root / "tests").mkdir()
        (root / "tests" / "test_book.py").write_text("def only_in_tests(x):\n    pass\n")
        assert not denied(write(root / "z.py", "def only_in_tests(x):\n    pass\n", session="s9")), \
            "test files are not searched"
        assert not denied(write(root / "tests" / "test_new.py", "def sharpe(x):\n    pass\n", session="s9")), \
            "a test file is never denied"

        page = root / "docs" / "report.html"
        assert "[REPORT]" in reminded(write(page, "<html></html>")), "a new report gets the report rule"
        page.parent.mkdir()
        page.write_text("<html></html>")
        assert write(page, "<html>v2</html>", session="s6") is None, "an existing report passes"
        assert write(root / "notes.md", "def sharpe(x):") is None, "non-code files pass"
        assert gate.decide({"tool_name": "Bash", "tool_input": {"command": "ls"}}) is None
    print("reuse_guard: ok")


if __name__ == "__main__":
    main()
