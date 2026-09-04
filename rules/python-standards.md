# Python Standards

## Style
- Annotate every function signature.
- Match the formatter and linter the repo configures in `pyproject.toml`; do not
  introduce a second one.
- Use `logging` module, never `print()` in production code.

## Patterns
- `@dataclass(frozen=True)` for DTOs and value objects.
- `Protocol` for duck-typing interfaces (not ABC unless needed).
- Context managers for resource management.
- Generators for lazy evaluation of large datasets.

## Testing
- pytest, with `@pytest.fixture` for setup and `tmp_path` for temp files. Mock APIs
  and databases with `unittest.mock`.
