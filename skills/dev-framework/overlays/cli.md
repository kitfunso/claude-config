# CLI Overlay

For command-line tools (npm `bin`, pyproject `[project.scripts]`, Cargo `[[bin]]`).

## Detection signals
- `package.json` with `bin` field
- `pyproject.toml` with `[project.scripts]`
- `Cargo.toml` with `[[bin]]`
- Directories: `bin/`, `cmd/`

## Required additions per phase

### SCAFFOLD
- `--help` output structured (synopsis, options, examples)
- Subcommand structure if applicable
- Exit code conventions documented (0=success, 1=user error, 2=system error, etc.)
- Output mode plan (TTY vs piped — different defaults)

### PLAN
- Argument parsing library decided: clap (Rust), click/typer (Python), commander/yargs (Node)
- Configuration file location strategy (XDG / `--config` / env vars)
- Logging strategy (stderr for diagnostics, stdout for output)

### EXECUTE
- Help text reads like documentation, not code dump
- Error messages name the FIX, not just the error
- Stderr for errors, stdout for output (pipe-able)
- `--version`, `--help` always work, even on error
- Color detection (honor `NO_COLOR` env var)
- Detect TTY: enable color/spinners only when interactive
- Cross-platform path handling (no `/` assumptions on Windows)

### VERIFY
- `/run` skill — actually execute the CLI
- Test on Windows AND Unix (path separators, line endings, env var format)
- Test piping output through `| jq`, `| less`, `| grep`
- Test `-h`, `--help`, `<cmd> help` all work
- Test `--version` returns sensible string

### REVIEW
- Help text quality review (reads like a man page?)
- Error UX review (does the error tell the user what to do?)
- Cross-platform paths checked
- Exit codes consistent across commands

### SHIP
- If npm bin: `/publish-repo`
- If PyPI: `python -m build && twine upload`
- Installation instructions in README current

### DEPLOY
- Smoke test: install fresh, run `--version`, run main command
- Test on clean system (Docker / VM)

### LEARN
- Help text updates if commands changed
- Document any breaking flag changes in CHANGELOG

## Tools

- `/run` skill for execution
- Argument parsing libs: clap (Rust), click/typer (Python), commander (Node)
- Output formatting: `tabulate`/`rich` (Python), `cli-table` (Node)

## Anti-patterns

- Help text dumps code, not user-facing description
- Errors print stack traces by default (only with `--verbose` / `--debug`)
- Output mixed stdout/stderr (breaks piping)
- Color codes when piped (detect TTY)
- Windows path assumptions (`/` only)
- Logging to stdout (should be stderr)
- Subcommand-level help missing (`<cmd> <sub> --help` should work)
- `--version` doing more than printing version
- Crash on `Ctrl+C` (catch SIGINT and exit cleanly)
- Missing `--no-color`, `--quiet`, `--verbose` flags
