# Task persona and bounded handoff

Read this when preparing a worker/reviewer contract. Use the existing nine persona fields in `runtime/contracts/delegation-smoke.json`; the example PB ID and architecture assertions are not an application task.

The supervisor writes a task-specific persona before every dispatch:

- **role/expertise:** relevant discipline and concrete subsystem. A cloud security reviewer needs authorization, data boundaries and platform rules; a Flutter UI implementer needs the actual navigation, localization and accessibility context.
- **objective:** observable before/after behavior and user outcome, scoped to the selected Brain task.
- **quality_standard:** applicable invariants, affected callers, error paths and measurable acceptance. Name what evidence proves correctness; source review alone cannot prove runtime or visual quality.
- **tools/permissions/forbidden_actions:** exact allowed files/tools, independent review read-only, no Brain/policy edits by workers, no credential reads, no unselected deployment or dependency changes.
- **common_failure_modes:** risks derived from this task's code, such as stale asynchronous callbacks, locale fallback, dropped pending writes or mismatched store IDs. Replace generic boilerplate with relevant cases.
- **acceptance_criteria:** exact checks, device/viewports where relevant, artifact/source evidence and truthful limitations.

Attach only the relevant Brain slice, contract, source map/callers and existing verification commands. Require structured public updates: task, role, provider/model, state, completed evidence, blocker and next action. Do not request hidden reasoning. Each agent reports completion or blocking to the supervisor; only the supervisor updates Brain and accepts a fresh review.

Model choice is separate: deterministic work uses tools, bounded tasks use a verified lightweight route, normal implementation a capable coding route, and architecture/security ambiguity a stronger route. Never lower the task's quality floor to save tokens. Record the failed acceptance before escalation. Unknown usage/quota stays unknown. For interrupted partial writes, inspect the actual diff, checkpoint and prepare a continuation contract; never blindly replay on another provider. Native IDs belong to one provider and one project.
