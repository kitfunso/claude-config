# Per-Stage Invocation Contract (used by `/dev-framework-rl`)

When this skill is invoked by the experiential-RL orchestrator (`/dev-framework-rl`), it operates in a different mode: one stage per call, with machine-readable JSON sidecars so the orchestrator can run critics between stages and tally trajectory data.

## Invocation modes

- **Normal**: `/dev-framework` with no stage argument. Claude walks all 9 stages interactively, as documented in `SKILL.md`. No manifests written. Existing behaviour, unchanged.
- **Per-stage**: `/dev-framework <stage>` with `<episode-id>` in the orchestrator's context. Run only the named stage; emit `trajectories/<episode-id>/<stage>.manifest.json` at completion.

Valid stages: `brainstorm`, `discover`, `scaffold`, `plan`, `execute`, `verify`, `review`, `ship`, `deploy`, `learn`.

## Stage-plan emission

At the end of the `discover` stage (per-stage mode only), also emit:
- `trajectories/<episode-id>/stage-plan.json`

Contains the ordered list of stages that will actually run for the detected `project_type`. (Library projects may skip `verify` runtime evidence; CLI may skip `deploy`; etc.) The orchestrator iterates this list, not the hardcoded 9.

## Stage-manifest emission

At the end of each stage (per-stage mode):
- `trajectories/<episode-id>/<stage>.manifest.json`: status, summary, artifacts, optional cost and skill prompt hash.

## Schemas (orchestrator validates against these)

- `~/.claude/dev-framework/schemas/stage-manifest.schema.json`
- `~/.claude/dev-framework/schemas/stage-plan.schema.json`

Both are JSON Schema 2020-12. Sidecars that fail validation cause the stage to be recorded as `critic_status=error` and escalated to a human. Validator: `python ~/.claude/dev-framework/scripts/validate_manifest.py {manifest|plan} <path>`.

## Backward compatibility

The contract is opt-in. If `<episode-id>` is not in the invocation context, this entire contract is a no-op and the skill behaves exactly as documented in `SKILL.md`. `/dev-framework-rl` is the only caller that triggers per-stage mode.
