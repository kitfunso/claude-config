# Coding Standards

## File Organization
- Many small files > few large files. 200-400 lines typical, 800 max.
- Organize by feature/domain, not by type.
- Functions under 50 lines. Nesting under 4 levels.

## Comments (CRITICAL)
- One line. Two at most. A file-header block may run to 3.
- Say WHY a non-obvious choice was made. Never say WHAT the code does.
- Measurements, dates, incident history and "we tried X first" stories go to
  `docs/ARCHITECTURE.md` or `docs/incidents.md`; a comment nobody edits rots in place.
- Mark a deliberate shortcut with one `SHORTCUT:` line naming its ceiling and the
  upgrade path: `# SHORTCUT: global lock, per-account locks if throughput matters`.
  Without it a knowing tradeoff reads as a bug to the next person.
- Applies to every language and every project, including new files.

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
