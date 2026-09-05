# Agent & Skill Routing

Reference tables for picking a specialized agent or skill. Reached from the global
CLAUDE.md pointer; read it when routing, not from memory.

## Agents

Applies on a box that has `~/.claude/agents/` definitions. Where that directory is
absent, use the injected agent-types list instead.

| Agent | Use Case |
|-------|----------|
| `python-backend-engineer` | Backend, API, database |
| `fastapi-pro` | FastAPI endpoints, Pydantic |
| `quant-analyst` | Financial modeling, risk analytics |
| `frontend-developer` | React/Next.js, UI |
| `typescript-pro` | TypeScript, frontend architecture |
| `debugger` | Errors, test failures |
| `senior-code-reviewer` | Code quality, security review |
| `data-engineer` | Pipelines, ETL |
| `database-optimizer` | Query optimization, indexing |

The five Quantamental agents (`commodity-backtest`, `signal-validator`, `data-auditor`,
`model-diff`, `smoke-test-frontend`) and its four skills (`model-improve`, `roll-check`,
`smoke-test`, `quant-report`) moved to `quantamental/.claude/` on 2026-09-05, the day
after the project was paused. They load only inside that repo.

## Skills

The injected available-skills list is the authority on what is installed and what
each skill does. Only the rows below add something that list does not carry, either
because the skill is user-invoked (absent from the model's list) or because its
injected description is empty.

| Skill | Trigger |
|-------|---------|
| `/standards-check` | Codebase audit scorecard, six 0-10 dimensions |
| `/hippo-feature` | One hippo feature via the micro-eval TDD loop |
| `/git-commit-helper` | Writing commit messages |
| `/unfreeze` | Remove the edit restrictions `/freeze` set |
