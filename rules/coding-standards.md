# Coding Standards

## File Organization
- Many small files > few large files. 200-400 lines typical, 800 max.
- Organize by feature/domain, not by type.
- Functions under 50 lines. Nesting under 4 levels.

## Comments (CRITICAL)
No comments in code (Keith, 2026-11-24, the pstack `/no-comments` approach). Put the
reason in a name, a type, a test or `docs/`; a comment nobody edits rots in place.
- Keep only: license blocks; lint, type and tool directives (`eslint-disable`,
  `@ts-expect-error`, `noqa`, `@vitest-environment`, pragmas); doc blocks on a
  published API; a link to the issue, RFC or vendor doc behind a limit the code
  cannot show; text that code reads at run time.
- `SHORTCUT:` marks a deliberate shortcut, with its ceiling and upgrade path:
  `# SHORTCUT: global lock, per-account locks if throughput matters`.
  `SAFETY:` explains a cast or `unsafe` block that a lint rule requires a reason for.
  One line each.
- A comment on code you change gets deleted, never reworded. Strip a whole repo only
  through `/no-comments`.
- Applies to every language and every project, including new files. Backstop:
  `scripts/hooks/comment-budget-guard.js` (home) and `comment_budget_guard.py` (work).

## Immutability
- Python: use `@dataclass(frozen=True)`, `NamedTuple`, `tuple` over `list` for fixed collections.
- TypeScript: use `readonly`, `as const`, spread operators.

## Error Handling
- Surface every error; a bare `except` / `catch` that swallows is the one banned
  shape. Detailed context server-side, plain messages in the UI.

## Dependencies & Compatibility
- Internal / unshipped code: do not preserve backward compatibility. Replace the old
  path and delete it: no shims, no deprecated re-exports, no _v2 suffixes.
- Published surfaces keep compat: npm packages (hippo), live APIs (RamSky), DB
  schemas, locked signal files. Breaking changes there need explicit sign-off
  (semver major / migration path).
