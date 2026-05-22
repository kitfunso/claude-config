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
