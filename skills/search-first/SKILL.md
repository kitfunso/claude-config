---
name: search-first
description: Research-before-coding workflow. Use BEFORE implementing any significant feature to check for existing libraries, MCP servers, patterns, or solutions. Prevents reinventing the wheel. Use when adding new dependencies, building integrations, or starting features that might have existing solutions.
---

# Search First

Research before coding. Check for existing solutions before writing custom code.

## Workflow

### 1. Need Analysis
- What functionality is needed?
- What are the constraints (size, license, dependencies)?
- Is this a solved problem?

### 2. Search Sources (in order)
1. **Package registries** — npm, PyPI, crates.io for the relevant language
2. **MCP servers** — Check if an MCP integration exists
3. **GitHub** — Search for existing implementations
4. **Existing codebase** — Check if something similar already exists in the project

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
