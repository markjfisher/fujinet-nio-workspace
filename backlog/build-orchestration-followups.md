# Build orchestration follow-ups

Status: `TODO`

## Goal

Finish the optional usability and compatibility cleanup left after the
completed Python build-front-end migration without expanding the public target
surface again.

## Work

- [ ] Add a true non-executing command planner/dry-run mode that resolves task
      dependencies and prints commands, inputs, and outputs without invoking
      repository builds.
- [ ] Add tests proving dry-run planning has no build or filesystem side
      effects beyond explicitly documented transient state.
- [ ] Audit compatibility aliases and artifact-only targets against current
      scripts, CI, and documentation.
- [ ] Remove aliases that have no remaining callers; retain and document any
      artifact target that is still useful for focused debugging.
- [ ] Keep default `--list` output limited to platform workflows and common
      artifacts, with internal/compatibility targets under `--list --all`.
- [ ] Update `docs/build-orchestration.md` and archive this task when the audit
      and planner are complete.

## Exit criteria

Users can inspect a complete build plan without executing it, obsolete aliases
are removed with no known callers, and the public workflow list remains small
and documented.
