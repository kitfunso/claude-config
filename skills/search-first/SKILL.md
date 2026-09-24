---
name: search-first
description: Research-before-coding workflow. Use before adding any capability (feature, helper, integration) or dependency, and whenever the user asks whether a package or library exists for something, how to add it, or whether to build, reuse or adopt it, even when the answer looks obvious, since what the project already has changes the answer. Checks the project's own code and declared dependencies first, then libraries, MCP servers, or patterns.
---

# Search First

Research before coding. Check for existing solutions before writing custom code.

## Workflow

### 1. Need Analysis
- What functionality is needed?
- What are the constraints (size, license, dependencies)?
- Is this a solved problem?

### 2. Search Sources (in order)
1. **Existing codebase**: grep for a helper that already does this, and read the dependency file (pyproject.toml, package.json) for a library that is already installed
2. **Package registries** — npm, PyPI, crates.io for the relevant language
3. **MCP servers** — Check if an MCP integration exists
4. **GitHub** — Search for existing implementations

### 3. Evaluate Candidates
Score on: functionality match, maintenance status, community size, documentation quality, license compatibility, dependency footprint.

### 4. Decision Matrix

| Situation | Action |
|---|---|
| Exact match, well-maintained, MIT/Apache | **ADOPT** as-is |
| Partial match, good foundation | **EXTEND** with wrapper |
| Multiple weak matches | **COMPOSE** from pieces |
| Nothing suitable | **BUILD** custom (but informed) |

### 5. Implement
- If adopting: install, configure, write thin wrapper if needed
- If building: use discovered patterns as reference, not starting from scratch

If the user asked a question rather than for the change (should I build this, is there a package, how should I do this), answer it: the verdict first, then the evidence (file and line, or the dependency entry), then a short usage sketch. Edit or create files only once they ask for the change.

## Common Shortcuts

| Domain | Go-to libraries |
|---|---|
| HTTP clients | httpx (Python), got/ky (Node) |
| Validation | pydantic (Python), zod (TypeScript) |
| Data processing | pandas, polars |
| AI/LLM | anthropic SDK, langchain (if needed) |
| Testing | pytest, vitest |
| CLI | click/typer (Python), commander (Node) |

## Anti-Pattern
Writing 200 lines of custom code for something that `pip install X` solves in 3 lines. Always check first.
