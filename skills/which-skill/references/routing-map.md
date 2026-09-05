# Routing map — task stage → skills

Point-in-time snapshot (2026-08-14). The live available-skills list in context wins on any conflict. Verify a name exists in that list before recommending it. **Bold** = house policy (mandated by global rules or the skill's own trigger), not optional.

## Idea / scoping
| Skill | When |
|---|---|
| **brainstorming** | Required before any creative work — new features, components, behavior changes |
| office-hours | "Is this worth building" brainstorms |
| project-scaffold | New project or repo kickoff (PRD, architecture, CLAUDE.md, plan) |

## Planning
| Skill | When |
|---|---|
| writing-plans | Before any multi-step implementation |
| plan-eng-review | Architecture check before coding |
| plan-ceo-review | Strategy and scope review |
| plan-design-review | Design plan critique before implementation |
| autoplan | Run all plan reviews in one pass with auto-decisions |
| executing-plans | Execute a written plan with review checkpoints |

## Build
| Skill | When |
|---|---|
| test-driven-development / tdd | Any feature or bugfix — test first |
| subagent-driven-development | Plan with independent tasks, current session |
| dispatching-parallel-agents | 2+ independent tasks with no shared state |
| using-git-worktrees | Parallel work needing isolated checkouts |
| frontend-design | Building web UI, pages, components with design quality |
| mcp-builder | Building MCP servers |

## Debug
| Skill | When |
|---|---|
| **investigate** | Any error report, stack trace, "it broke" — no fix without root cause |
| **systematic-debugging** | Before proposing fixes for any bug |
| wtf | Plain-English "what happened / where are we / why do we have this" |

## Verify / review
| Skill | When |
|---|---|
| **verification-before-completion** | Required before claiming done, fixed, or passing |
| self-review | Review this session's changes for mistakes |
| code-review | Review a branch or PR against standards + spec |
| review | Pre-landing PR review (gstack structural checks) |
| codex | Cross-model second opinion or adversarial review |
| simplify | Quality cleanup of changed code (not bug hunting) |
| de-sloppify | Cleanup pass after a large feature or refactor |
| remove-dumb-comments | Strip comments that restate the code |

## Ship / release
| Skill | When |
|---|---|
| commit / git-commit-helper | Commit messages, commit and push |
| ship | Tests → review → version bump → PR → push |
| land-and-deploy | Merge the PR, wait for CI, verify prod |
| finishing-a-development-branch | Merge / PR / cleanup decision when work is done |
| document-release | Post-ship doc sync |
| publish-repo | Version bump, build, npm publish, tag |

`ship` and `land-and-deploy` assume a PR + CI flow. If the repo's CLAUDE.md defines its own deploy path (e.g. push + VM pull for the crude apps), recommend that instead.

## QA / browser
| Skill | When |
|---|---|
| qa | Browser QA + auto-fix loop |
| qa-only | Browser QA, report only, no fixes |
| browse | Headless browser commands (~100ms each) |
| webapp-testing | Frontend checks after deploys |
| benchmark | Page performance, web vitals, bundle size |
| canary | Post-deploy monitoring of the live app |
| devex-review | Live developer-experience audit |

## Design / viz
| Skill | When |
|---|---|
| **dataviz** | Required before writing ANY chart, plot, or dashboard code |
| design-consultation | Create a design system / DESIGN.md |
| design-review | Visual QA audit of a live site, with fixes |
| design-shotgun | Generate multiple design variants to pick from |
| design-html | Turn approved mockups into production HTML/CSS |
| canvas-design / algorithmic-art / theme-factory | Posters, generative art, themes |
| brand-guidelines | Anthropic brand look-and-feel |

## Documents / artifacts
| Skill | When |
|---|---|
| docx / xlsx / pptx / pdf | Create or edit Office and PDF files |
| make-pdf | Markdown file → publication-quality PDF |
| doc-coauthoring | Structured co-writing of specs, proposals, docs |
| internal-comms | Status reports, incident reports, leadership updates |
| artifact-design | Design guidance before building any claude.ai artifact page |
| artifacts-builder / web-artifacts-builder | Multi-component claude.ai artifacts |
| artifact-diagramming | Diagrams inside artifacts |
| artifact-capabilities | Artifacts needing live data, shared state, self-update |

## Content / social
linkedin-thought-leader, twitter-thread-builder, viral-hook-generator, youtube-title-optimizer, creator-style-mimic, framework-content-mixer, platform-voice-adapter, social-brand.
House rule: read the matching `~/.claude/voice/*.md` sample before drafting.

## Safety / guard
| Skill | When |
|---|---|
| careful | Warn before destructive commands |
| freeze / unfreeze | Restrict edits to one directory |
| guard | careful + freeze combined — prod work |
| cso / security-review | Security audits, threat models |

## Quant / desk
| Skill | When |
|---|---|
| **quant-ml-protocol** | Required before any forecasting-model campaign: nulls, holdouts, selection honesty |
| **issue-brief** | Required format for reporting any blocker or side-issue |

## Meta / harness
| Skill | When |
|---|---|
| skill-creator / writing-skills | Create or improve skills |
| **claude-api** | Required read before any Claude / LLM API work |
| update-config | settings.json, hooks, permissions, env vars |
| keybindings-help | Keyboard shortcut customization |
| learn | Review or prune project learnings |
| context-save / context-restore | Save / resume working state across sessions |
| loop | Recurring prompt on an interval |
| schedule | Scheduled cloud agents (cron) |
| click-steps | GUI walkthroughs — "where do I click" |
| fewer-permission-prompts | Reduce permission prompt noise |

## Common chains
- New feature: brainstorming → writing-plans → plan-eng-review → test-driven-development → verification-before-completion → ship (or the repo's own deploy path — see Ship note above)
- Bug report: investigate → test-driven-development (repro test) → verification-before-completion → commit
- UI change: brainstorming → frontend-design (+ dataviz if charts) → design-review → qa
- Post-deploy check: qa-only → canary
- New skill: skill-creator (drafting → evals → description optimization)
