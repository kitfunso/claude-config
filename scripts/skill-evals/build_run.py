"""Build one eval run folder for a skill: a clean skill copy, neutral message files and the workflow args.

Usage: python build_run.py SKILL ROOT [--runs 3] [--without NAME ... | --without-split test]
Writes ROOT/args.json for run-evals.js. Test-split prompts are never printed.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SKILLS = Path.home() / ".claude" / "skills"
SPLITS = {"train": "evals", "test": "evals-test"}
# Everything a run must not see: the rubrics of both splits, backups, test files and caches.
HIDDEN = ("evals", "evals-test", "*.old-*", "__pycache__", ".pytest_cache", "test_*.py")


def read_case(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    prompt = re.search(r"prompt: \|\n((?:    .*\n|\n)+?)  max_turns", text)
    if not prompt:
        raise ValueError(f"{path}: no prompt block before max_turns")
    tools = re.search(r"allowed_tools: \[(.*)\]", text)
    criteria = text.split("criteria: |", 1)[1]
    return {
        "prompt": "\n".join(line[4:] for line in prompt.group(1).splitlines()).strip() + "\n",
        "n_criteria": len(re.findall(r"^\s+\d+\. ", criteria, flags=re.M)),
        "expect_fire": "skill-not-fired" not in text,
        "writes": bool(tools and "Write" in tools.group(1)),
    }


def description(skill_dir: Path) -> str:
    head = (skill_dir / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    match = re.search(r'^description:\s*"?(.*?)"?\s*$', head, flags=re.M)
    if not match:
        raise ValueError("SKILL.md frontmatter has no description")
    return match.group(1)


def build(skill: str, root: Path, runs: int, without: set[str], without_splits: set[str]) -> dict[str, object]:
    skill_dir = SKILLS / skill
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(skill_dir, root / "skill" / skill, ignore=shutil.ignore_patterns(*HIDDEN))
    (root / "msgs").mkdir()
    (root / "proj").mkdir()
    found = [
        (split, case)
        for split, folder in SPLITS.items()
        for case in sorted((skill_dir / folder).glob("*/case.yaml"))
    ]
    cases = []
    # Sorted by name across both splits, so a message number says nothing about its split.
    for i, (split, case) in enumerate(sorted(found, key=lambda sc: sc[1].parent.name), 1):
        info = read_case(case)
        msg = f"msg-{i:02d}"
        (root / "msgs" / f"{msg}.txt").write_text(str(info.pop("prompt")), encoding="utf-8")
        cases.append({"name": case.parent.name, "msg": msg, "split": split, "case_dir": str(case.parent), **info})
    names = {c["name"] for c in cases}
    unknown = without - names
    if unknown:
        raise ValueError(f"--without names no case: {sorted(unknown)}")
    rerun = sorted(without | {c["name"] for c in cases if c["split"] in without_splits})
    args = {"root": str(root), "skill": skill, "desc": description(skill_dir), "runs": runs,
            "without": rerun, "regrade_splits": ["test"], "cases": cases}
    (root / "args.json").write_text(json.dumps(args, indent=1), encoding="utf-8")
    return args


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("skill")
    ap.add_argument("root", type=Path)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--without", nargs="*", default=[], help="cases to rerun without the skill")
    ap.add_argument("--without-split", nargs="*", default=[], choices=tuple(SPLITS), help="whole splits to rerun without")
    a = ap.parse_args(argv)
    args = build(a.skill, a.root, a.runs, set(a.without), set(a.without_split))
    for split in SPLITS:
        mine = [c for c in args["cases"] if c["split"] == split]
        print(f"{split}: {len(mine)} cases, {sum(c['name'] in args['without'] for c in mine)} also run without the skill")
    print(f"args: {a.root / 'args.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
