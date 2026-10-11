# Task persona and bounded handoff

Read this when preparing a worker/reviewer contract. Use the existing nine persona fields in `runtime/contracts/delegation-smoke.json`; the example PB ID and architecture assertions are not an application task.

The supervisor writes a task-specific persona before every dispatch:

- **role/expertise:** relevant discipline and concrete subsystem. A cloud security reviewer needs authorization, data boundaries and platform rules; a Flutter UI implementer needs the actual navigation, localization and accessibility context.
- **objective:** observable before/after behavior and user outcome, scoped to the selected Brain task.
- **quality_standard:** applicable invariants, affected callers, error paths and measurable acceptance. Name what evidence proves correctness; source review alone cannot prove runtime or visual quality.
- **tools/permissions/forbidden_actions:** exact allowed files/tools, independent review read-only, no Brain/policy edits by workers, no credential reads, no unselected deployment or dependency changes.
- **common_failure_modes:** risks derived from this task's code, such as stale asynchronous callbacks, locale fallback, dropped pending writes or mismatched store IDs. Replace generic boilerplate with relevant cases.
- **acceptance_criteria:** exact checks, device/viewports where relevant, artifact/source evidence and truthful limitations.

Attach actual relevant source and affected callers, the relevant Brain slice, contract and existing verification commands. Name the failure/checkpoint procedure and first unchecked criterion. Require structured public reports with `task`, `state`, `evidence`, `usage`, `blockers`, `next_action`, plus actual role/provider/model/effort and changed files. Evidence names observed checks/artifacts, not planned checks. Do not request hidden reasoning. Each agent reports completion or blocking to the supervisor; only the supervisor updates Brain and accepts a fresh review.

Every new dispatch requires `delegation: {provider, model, effort, reason, context_budget_chars, output_budget_tokens, checkpoint, report_fields: [task, role, provider, model, effort, state, changed_files, evidence, usage, blockers, next_action]}`. Add this block minimally to older contracts for new dispatch; never rewrite historic evidence. Budgets bound the declared handoff payload/output request, not provider system overhead. Record actual measured usage or null; a declared budget is not evidence of savings.

Model choice is separate: deterministic work uses tools, simple tasks use a verified lightweight route at low effort, standard implementation sufficient medium/high effort, and architecture/security/persistence a strong route at high effort, possibly stronger than the coordinator. Delegate substantive execution to specialists; the supervisor plans, coordinates, machine-checks, requests independent review and accepts. Never lower the task's quality floor for quotas. Record failed acceptance before escalation. At <=10% in any shared quota window start no new job in that bucket; checkpoint actual partial edits and select an equally qualified approved route or await reset. Unknown usage/quota stays null. Denied tools or empty/timed-out responses are UNVERIFIED: stop that approach promptly, without repeated expensive reasoning or permission requests. Inspect interrupted writes and prepare a continuation contract; never blindly replay mutators. Native IDs belong to one provider and one project.
