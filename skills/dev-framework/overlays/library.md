# Library Overlay

For npm packages, PyPI libraries, crates — reusable code with semver and a CHANGELOG.

## Detection signals
- `package.json` with `main`/`module`/`exports` but no `bin`
- `pyproject.toml` with `[project]` but no scripts
- `Cargo.toml` with `[[lib]]` only (no `[[bin]]`)
- `CHANGELOG.md` exists

## Required additions per phase

### SCAFFOLD
- `CHANGELOG.md` REQUIRED (Keep a Changelog format)
- Public API documented in README with install + usage examples
- Semver discipline stated in CLAUDE.md
- License chosen and added

### PLAN
- Breaking change detection plan
- Migration path for users if breaking change
- Deprecation policy (how long before removal)

### EXECUTE
- API surface minimal — don't export internal helpers
- Public types stable, internal types flexible
- TypeScript: types collocated with source
- Python: typed function signatures (per `python-standards`)

### VERIFY
- `/benchmark` for performance regressions vs published version
- Multi-version dependency matrix test if applicable
- TypeScript: type tests for the public API (`tsd` or `expect-type`)
- README examples actually compile/run
- Cross-platform test if applicable (Windows path separators, line endings)

### REVIEW
- API surface diff vs published version
- Semver impact assessment (patch/minor/major)
- CHANGELOG entry matches actual changes
- README examples still work
- Tree-shaking preserved (no default-only exports if multi-export library)

### SHIP
- **`/publish-repo` REQUIRED** — bumps version, updates CHANGELOG/README/manifests, builds, tests, commits, tags, npm publishes, pushes, creates GitHub Release
- Version bump matches semver impact (don't ship breaking as minor)
- CHANGELOG voice matches prior entries

### DEPLOY
- `npm install <pkg>@latest` smoke test in a fresh project
- Watch downloads / install stats for anomalies first 48h
- Watch GitHub Issues for regression reports

### LEARN
- Breaking change retro if any
- Migration guide if needed (separate doc, linked from CHANGELOG)
- `/document-release` to sync README to shipped reality

## Per-project notes

**hippo**:
- Per `feedback_hippo_release_workflow`: `/self-review` → `/review` → `/ship-check` → `/publish-repo` chain MANDATORY
- Adaptive decay, XDG/HIPPO_HOME, auto-share, multi-project scan are shipped features (per memory `session-2026-04-08`)
- Physics branch (`feat/physics-local-testing`) has pending local validation

## Tools

- `/publish-repo` skill — full release flow
- `/document-release` skill — sync README to shipped state
- `/benchmark` skill — performance regression detection

## Anti-patterns

- Re-exporting internals (locks API surface unintentionally)
- Breaking change shipped without major bump
- CHANGELOG missing or stale
- README examples that don't compile
- Default exports without explicit name (breaks tree-shaking)
- `peerDependencies` undeclared (silently breaks consumers)
- Bundling deps that should be peer
- Forgetting to bump version (publish fails or skips silently)
