"""Grade a seeded-duplicates run: python grade.py <repo> <run-folder>. Exit 0 only if every check passes."""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path


def git(repo: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def _show(repo: str, ref: str, path: str) -> str:
    out = subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ""


def tests_on(repo: str, ref: str) -> set[str]:
    names = set()
    for path in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines():
        if path.startswith("tests/") and path.endswith(".py"):
            tree = ast.parse(git(repo, "show", f"{ref}:{path}"))
            names |= {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
    return names


def main() -> int:
    repo, run = sys.argv[1], Path(sys.argv[2])
    branches = [b.strip("* ").strip() for b in git(repo, "branch").splitlines()]
    cut = [b for b in branches if b != "master"]
    if len(cut) != 1:
        print(f"FAIL expected one cut branch, found {cut}")
        return 1
    have = tests_on(repo, cut[0])
    plans = list(run.rglob("plan.json"))
    heavy = json.loads(plans[0].read_text(encoding="utf-8"))["heavy"] if plans else []
    checks = {
        "duplicates cut": not {"test_band_low_again", "test_clamp_low_dup"} & have
        and len({"test_spread", "test_spread_copy"} & have) == 1,
        "lone catcher kept": "test_band_edge" in have,
        "originals kept": {"test_band_cases", "test_clamp_all", "test_rolling_total"} <= have,
        "source untouched": git(repo, "show", "master:pricing.py") == git(repo, "show", f"{cut[0]}:pricing.py"),
        "heavy flagged, report written": any("test_rolling_total" in h for h in heavy)
        and any(run.rglob("report.html")),
        "default run keeps every test": not re.search(r"addopts.*-m", _show(repo, cut[0], "pytest.ini")),
        "commit message carries the lost counts": bool(re.search(r"lost", git(repo, "log", "-1", "--format=%B",
                                                                             cut[0]), re.IGNORECASE)),
    }
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
