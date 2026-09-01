# Coding Standards

## File Organization
- Many small files > few large files. 200-400 lines typical, 800 max.
- Organize by feature/domain, not by type.
- Functions under 50 lines. Nesting under 4 levels.

## Comments (CRITICAL — Keith 2026-08-30, all projects)
- One line. Two at most. A file-header block may run to 3.
- Say WHY a non-obvious choice was made. Never say WHAT the code does.
- Measurement notes, dates, benchmark numbers, incident history, and "we tried X
  first" stories go in `docs/ARCHITECTURE.md` or the project `CLAUDE.md`. Never in
  a source file. They bury the code and rot in place — nobody edits a comment when
  they change the line under it.
- Over 20% comment lines in a file means cut. Delete the story, keep the sentence.
- Mark a deliberate shortcut with one `SHORTCUT:` line naming its ceiling and the
  upgrade path: `# SHORTCUT: global lock, per-account locks if throughput matters`.
  Without it a knowing tradeoff reads as a bug to the next person. One line, no
  story. (Convention from github.com/dietrichgebert/ponytail, adopted 2026-09-01.)
- Applies to every language and every project, including new files.
- Deterministic backstop: `scripts/hooks/comment-budget-guard.js` (PreToolUse on
  `Edit|Write`, registered in `settings.json`) denies a payload with more than 3
  comment lines in a row, or over 20% comment density across 15+ lines. It skips
  markdown/JSON/config, `docs/`, Python docstrings, and JSDoc carrying `@param` /
  `@returns`. `CLAUDE_COMMENT_BUDGET=off` disables it. Incident: aura
  `src/decide.js`, 53 comment lines out of 106; a one-line change carried a 12-line
  comment block.

## Immutability
- Prefer immutable data structures. Return new copies with changes.
- Python: use `@dataclass(frozen=True)`, `NamedTuple`, `tuple` over `list` for fixed collections.
- TypeScript: use `readonly`, `as const`, spread operators.

## Error Handling
- Handle errors explicitly at every level. Never silently swallow.
- User-friendly messages in UI code, detailed context server-side.
- Fail fast with clear messages at system boundaries.

## Naming
- Functions: verb_noun (`calculate_pnl`, `fetch_prices`)
- Booleans: is/has/should prefix (`is_valid`, `has_data`)
- Constants: UPPER_SNAKE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- No abbreviations except well-known ones (URL, API, ID)

## Dependencies & Compatibility (probation — added 2026-07-31, no incident yet)
- Prefer established, well-maintained libraries over custom implementations.
  Hand-roll only when the dependency is heavier than the problem.
- Internal / unshipped code: do not preserve backward compatibility. Replace
  the old path and delete it — no shims, no deprecated re-exports, no _v2 suffixes.
- Published surfaces keep compat: npm packages (hippo), live APIs (RamSky),
  DB schemas, locked signal files. Breaking changes there need explicit
  sign-off (semver major / migration path).
