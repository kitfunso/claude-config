#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys

HASH_COMMENT = {".py", ".sh", ".bash", ".ps1", ".r", ".rb", ".pl", ".cmake"}
SLASH_COMMENT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".c", ".h", ".cpp",
    ".hpp", ".cs", ".go", ".rs", ".swift", ".kt", ".scala", ".css", ".scss",
}
DASH_COMMENT = {".sql"}
TOKENS = {**{e: "#" for e in HASH_COMMENT}, **{e: "//" for e in SLASH_COMMENT}, **{e: "--" for e in DASH_COMMENT}}

API_DOC = re.compile(r"@param|@returns|@return|@type(?![a-zA-Z])|@typedef|@property|@callback|@example|@throws")
MARK = re.compile(r"\b(SHORTCUT|SAFETY):")
LICENSE = re.compile(r"copyright|licen[cs]e\b|spdx-|all rights reserved|@license|@preserve", re.I)
KEEP = re.compile("|".join([
    r"https?://\S", r"\brfc\s?-?\d{3,}",
    r"@(vitest|jest)-environment", r"swift-tools-version", r"webpack(Prefetch|Preload|Mode|Exclude|Include|Exports|ChunkName|Ignore)",
    r"@deno-types", r"tslint:", r"oxlint-", r"stylelint-", r"yamllint", r"cspell", r"codespell", r"NOSONAR",
    r"eslint-", r"^\W*eslint\s", r"^\W*global\s+\w", r"jshint", r"@ts-(ignore|expect-error|nocheck|check)",
    r"prettier-ignore", r"biome-ignore", r"deno-lint", r"(istanbul|c8|v8)\s+ignore",
    r"\bnoqa\b", r"^\W*type:\s", r"pyright:", r"mypy:", r"pylint:", r"ruff:", r"isort:", r"^\W*fmt:\s*(on|off|skip)",
    r"\bpragma\b", r"\bnosec\b", r"noinspection", r"@jsx", r"@refresh\b", r"@vite-ignore", r"sourceMappingURL", r"@flow\b",
    r"-\*-\s*coding", r"coding[:=]\s*utf", r"vim:", r"shellcheck", r"@generated", r"^\W*go:\w", r"\+build", r"nolint",
    r"__PURE__", r"__NO_SIDE_EFFECTS__", r"^\W*/\s*<reference", r"^\W*#requires",
]), re.I)


API_TARGET = re.compile(r"^(export\b|declare\b|\s+((readonly|static|public|async|get|set)\s+)*[\w$#]+[?!]?\s*[:(<=])")


def next_code(lines: list[str], start: int) -> str:
    return next((l for l in lines[start:] if l.strip()), "")


def classify(lines: list[str], token: str) -> list[str]:
    kind = ["code"] * len(lines)
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            kind[i] = "blank"
            i += 1
            continue
        if token == "#" and line[:3] in ('"""', "'''"):
            q, j = line[:3], i
            if q not in line[3:]:
                j += 1
                while j < len(lines) and q not in lines[j]:
                    j += 1
            for k in range(i, min(j, len(lines) - 1) + 1):
                kind[k] = "doc"
            i = j + 1
            continue
        if line.startswith("/*"):
            j = i
            while j < len(lines) and "*/" not in lines[j]:
                j += 1
            is_api = (line.startswith("/**") and (j == i or bool(API_TARGET.match(next_code(lines, j + 1))))) or any(
                API_DOC.search(l) for l in lines[i:j + 1])
            for k in range(i, min(j, len(lines) - 1) + 1):
                kind[k] = "doc" if is_api else "comment"
            i = j + 1
            continue
        if line.startswith(token) and not line.startswith("#!"):
            kind[i] = "comment"
        i += 1
    return kind


def stray_comments(lines: list[str], token: str) -> list[str]:
    kind = classify(lines, token)
    stray: list[str] = []
    i = 0
    while i < len(lines):
        if kind[i] != "comment":
            i += 1
            continue
        j = i
        while j < len(lines) and kind[j] == "comment":
            j += 1
        if not any(LICENSE.search(l) for l in lines[i:j]):
            stray += [l.strip() for l in lines[i:j] if l.strip() and not (MARK.search(l) or KEEP.search(l))]
        i = j
    return stray


def added_stray(before: str, after: str, token: str) -> list[str]:
    seen: dict[str, int] = {}
    for l in stray_comments(re.split(r"\r?\n", before), token):
        seen[l] = seen.get(l, 0) + 1
    added = []
    for l in stray_comments(re.split(r"\r?\n", after), token):
        if seen.get(l, 0) > 0:
            seen[l] -= 1
        else:
            added.append(l)
    return added


def apply_edit(content: str, old: str, new: str, replace_all: bool) -> str | None:
    if not old or old not in content:
        return None
    return content.replace(old, new) if replace_all else content.replace(old, new, 1)


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
try:
    from record_component import record
except Exception:
    def record(**_: object) -> None:
        return None


def main() -> None:
    if os.environ.get("CLAUDE_COMMENT_BUDGET", "").lower() == "off":
        return
    payload = json.load(sys.stdin)
    tool_name = payload.get("tool_name")
    if tool_name not in ("Edit", "Write"):
        return
    tool_input = payload.get("tool_input") or {}
    file_path = (tool_input.get("file_path") or "").replace("\\", "/")
    token = TOKENS.get(os.path.splitext(file_path)[1].lower())
    if not token or re.search(r"(^|/)docs(/|$)", file_path, re.IGNORECASE):
        return
    text = tool_input.get("content") if tool_input.get("content") is not None else tool_input.get("new_string")
    if not text:
        return
    try:
        with open(tool_input.get("file_path") or "", "r", encoding="utf-8") as fh:
            before = fh.read()
    except (OSError, ValueError):
        before = ""
    after = text
    if tool_name == "Edit":
        after = apply_edit(before, tool_input.get("old_string") or "", text, tool_input.get("replace_all") is True)
        if after is None:
            before, after = tool_input.get("old_string") or "", text
    added = added_stray(before, after, token)
    if not added:
        return
    reason = (
        f"comment-budget-guard: {file_path} gains {len(added)} comment line(s) outside the keep list, "
        f'first: "{added[0][:100]}". Code carries no comments (rules/coding-standards.md): delete it, or put '
        "the reason in a name, a type or a test. Kept: license blocks, lint/type/tool directives, SHORTCUT: and "
        "SAFETY: lines, a link to the issue, RFC or vendor doc behind a limit, and API doc blocks. A stale comment "
        "gets deleted, never reworded."
    )
    record(kind="hook", name=os.path.basename(__file__), session_id=payload.get("session_id"),
           cwd=payload.get("cwd"), blocked=True, notes=reason)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
