# Python Standards

## Style
- PEP 8 compliance. Type annotations on all function signatures.
- Format: black. Imports: isort. Lint: ruff.
- Use `logging` module, never `print()` in production code.

## Patterns
- `@dataclass(frozen=True)` for DTOs and value objects.
- `Protocol` for duck-typing interfaces (not ABC unless needed).
- Context managers for resource management.
- Generators for lazy evaluation of large datasets.

## Anti-Patterns to Avoid
- Mutable default arguments: `def f(x=[])` — use `None` + conditional.
- Bare except: `except: pass` — always catch specific exceptions.
- `from module import *` — explicit imports only.
- `value == None` — use `is None`.
- Shadowing builtins (`list`, `dict`, `str`, `id`, `type`).

## Testing
- pytest for all tests. 80%+ coverage target.
- Use `@pytest.fixture` for setup, `tmp_path` for temp files.
- Mock external dependencies (APIs, databases) with `unittest.mock`.

## Performance
- Use ProcessPoolExecutor for CPU-bound parallel work.
- Profile before optimizing: `cProfile`, `line_profiler`.
(GPU defaults are in global CLAUDE.md.)
