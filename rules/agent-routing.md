# Agent & Skill Routing

Reference tables for picking specialized agents and skills. Loaded on demand by the global CLAUDE.md "Agents / Skills" pointer — not into every prompt.

## Agents
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
| `commodity-backtest` | Run model -> validate -> sync (full pipeline) |
| `signal-validator` | Quick output health check (no model run) |
| `data-auditor` | Cache freshness, source health diagnosis |
| `model-diff` | Compare production vs candidate model versions |
| `smoke-test-frontend` | Playwright smoke tests after deploys |

## Skills
| Skill | Trigger |
|-------|---------|
| `/writing-plans` | Before multi-step implementation |
| `/systematic-debugging` | Before proposing fixes for any bug |
| `/verification-before-completion` | Before claiming work is complete |
| `/git-commit-helper` | Writing commit messages |
| `/test-driven-development` | Implementing features or bugfixes |
| `/quant-report` | Presenting validation, backtest, pipeline, or signal results |
| `/smoke-test` | Verifying frontend after deploys |
| `/roll-check` | Check and fix futures contract roll adjustments |
| `/publish-repo` | Bump version, update docs, build, test, npm publish, tag, push |

## gstack Skills (Dev Workflow)
| Skill | Trigger |
|-------|---------|
| `/office-hours` | Brainstorming new ideas, "is this worth building" |
| `/plan-ceo-review` | Strategy/scope review, "think bigger" |
| `/plan-eng-review` | Architecture validation before coding |
| `/plan-design-review` | Design plan critique before implementation |
| `/design-consultation` | Create design system / DESIGN.md |
| `/design-review` | Visual QA audit with iterative fixes |
| `/investigate` | Root-cause debugging (no fix without cause) |
| `/review` | Pre-landing PR code review |
| `/codex` | Cross-model second opinion / adversarial review |
| `/qa` | Browser QA testing + auto-fix loop |
| `/qa-only` | Browser QA testing, report only (no fixes) |
| `/ship` | Tests -> review -> version bump -> PR -> push |
| `/document-release` | Post-ship doc updates |
| `/retro` | Weekly engineering retrospective |
| `/browse` | Headless browser commands (~100ms each) |
| `/careful` | Warn before destructive operations |
| `/freeze` | Restrict edits to a specific directory |
| `/guard` | Maximum safety: careful + freeze combined |
| `/unfreeze` | Remove edit restrictions |
| `/setup-browser-cookies` | Import real browser cookies for auth |
| `/gstack-upgrade` | Update gstack to latest version |
