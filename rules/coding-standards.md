# Coding Standards

## File Organization
- Many small files > few large files. 200-400 lines typical, 800 max.
- Organize by feature/domain, not by type.
- Functions under 50 lines. Nesting under 4 levels.

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
