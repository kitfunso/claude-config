# AI/Agent Overlay

For projects building on Claude API, OpenAI, LangChain, agent frameworks, MCP servers, or skills.

## Detection signals
- Deps: `@anthropic-ai/sdk`, `anthropic`, `openai`, `langchain`, `llamaindex`, `transformers`, `litellm`
- Files: `SKILL.md`, `agents/`, `prompts/`, `evals/`
- Code: imports `Anthropic()`, `OpenAI()`, prompt templates, chat loops

## Required additions per phase

### DISCOVER
- `/benchmark-models` if model choice is open — never guess by default
- Check existing skills, MCP servers, agent libraries via `mcp__2chain__discover_tools`
- Per Keith preference (memory): Codex execution lanes prefer `openai-codex/gpt-5.5` (thinking high, fast on), fallback `gpt-5.4`

### SCAFFOLD
- `EVALS.md` artifact REQUIRED — define success criteria for AI behavior BEFORE building
- Prompt versioning strategy (where prompts live, how they're versioned)
- Sub-agent strategy decided

### PLAN
- Eval suite plan: cases, pass criteria, regression set
- Token / cost budget per call
- Caching strategy (prompt prefix caching)
- Fallback model defined

### EXECUTE
- **`/eval-driven-dev` REQUIRED** — evals first, then implementation
- **Prompt caching from day 1** (per `claude-api` skill)
- Sub-agents for parallel extraction work (per `feedback_synth_use_subagents_for_extraction` — MANDATORY in synth)
- Test against eval suite at every commit
- Never claim "API auth blocked" as a stop — route around per project rules

### VERIFY
- Eval suite passes (regression set + new cases)
- Token usage within budget
- Latency p95 acceptable
- Cost per call within budget

### REVIEW
- **`/cso` REQUIRED for LLM supply chain** — skill scanning, prompt injection vectors, output sanitization, skill source provenance
- Prompt injection test cases run
- PII / secret leak check in prompts and responses
- Cost regression check vs baseline

### SHIP
- Prompt caching enabled (verify cache hit rate)
- Cost monitoring configured
- Fallback model defined and tested

### DEPLOY
- Cost canary (alert on token spend anomaly)
- Eval canary (post-deploy eval run against prod)
- Watch model deprecation warnings

### LEARN
- Eval suite expansion based on production failures
- Prompt version retrospective
- Token usage analysis

## Project-specific routing (from MEMORY.md)

**hippo**: 
- v1.7.7 chain MANDATORY: `/self-review` → `/review` → `/ship-check` → `/publish-repo` (per `feedback_hippo_release_workflow`)
- Salience gate testing requires LongMemEval + LoCoMo (per `feedback_hippo_salience_regression`)
- Next major feature: 3-layer bio + Lossless-Claw DAG + SQLite backend (per memory hippo-roadmap)

**synth**:
- Sub-agents for extraction MANDATORY (per `feedback_synth_use_subagents_for_extraction`)
- Never refuse with "API auth blocked"
- Never tell user to "sleep" / "wait"

**2chain**:
- Prefer `mcp__2chain__discover_tools` + `mcp__2chain__call_tool` over manual searches
- Each call generates registry usage signal

## Tools

- `claude-api` skill — SDK patterns + prompt caching + migration
- `mcp-builder` skill — for MCP servers
- `/benchmark-models` — cross-model comparison
- `/eval-driven-dev` — EDD loop
- `mcp__context7__query-docs` — current library docs

## Anti-patterns

- Skipping evals "we'll add them later"
- Prompts in code without versioning
- No cost budget = unbounded spend
- Ignoring prompt caching (Anthropic SDK projects: caching is mandatory)
- Single-model lock-in without fallback
- Sequential extraction when sub-agents would parallelize
- Stale model IDs in code (claude-3-* references after 4.x release)
