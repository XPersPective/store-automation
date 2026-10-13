# Specialists, permissions and measurement

The task loop, review and takeover rules live in [plan](plan.md); this file covers how to brief helpers
and what their results mean.

## Briefing a specialist

Start a specialist only for a clear deliverable or an independent review. The brief contains: the user's
goal and context, the expertise needed, the exact task and scope, the relevant sources and callers, the
deliverable, measurable acceptance, expected failure modes, dependencies and contracts, real tool and
write permissions, time/context/output budget, and the next step when blocked. Give task-specific
competence and checks, not a generic "world-class expert" persona. A tier L/M task file is already such a
brief: hand over the task path, not a paraphrase.

Expertise, model and effort are separate decisions. A declared budget is not measured usage; unknown
usage is null. If the host does not reveal the real model or effort, say inherited/unknown; never invent
names. Before starting a helper tell the user briefly: role, job, why this choice, the important limit;
report the result and any blocker afterwards.

Use the existing official subscription and host tools. Catalog access, login, model entitlement, task
capability, quota and permission are different things; listed is not working. Refresh quota from the
existing tool; do not start a new worker on unknown or below-threshold shared quota. No paid API and no
silent quality downgrade. Catalog discovery is not a mandatory ritual before work.

## Permissions and ownership

"Only write this file" in a prompt is not access control. If the host cannot enforce a narrow write
boundary, the safe options are a read-only proposal/patch or a reviewed isolated checkout. A worktree of
the same OS user is not a sandbox against credential access.

One writer per checkout. Isolated disjoint work may run in parallel; work that shares a data or API
contract is not independent even in separate files. The integration owner reviews the diffs and the
merged behaviour. Unknown user edits are preserved.

## Results are different things

- Process finished: transport result only.
- Specialist said COMPLETED: a report to verify.
- Machine checks passed: those commands on that source and environment.
- Journey accepted: the required behaviour/visual/accessibility observations.
- Release result: readback from the remote system; availability is observed separately.

A specialist report must match the task, its Owner and the known real model; unknown state is never
success. A current hash does not make a fake or wrong observation true. Screens and services are
inspected with the right tool for real.

## Interruption and failure

First inspect real running processes and ownership. Access denied does not mean a process died. Stop only
processes you own; never start a replacement writer before the old one has stopped. Partial diffs,
reports, evidence and unknown user work are preserved. Do not confuse quota, access, model and tool
errors. Do not repeat a call that produces no new evidence. No blind fallback or replay after a partial
operation; after a lost response, query the remote state first. Without equivalent permission and
capability the work stays blocked while unrelated authorized work continues.

## Measurement

No new telemetry service: commit times, check durations and task Notes are enough. When needed, add time
stamps for: need received, first useful output, worker start/end, check, feedback, rework, acceptance.
Derive analysis/execution/waiting/rework time only from observed events; never add parallel durations as
wall time. Sum parent/worker/retry token usage only with complete coverage and authoritative counters;
otherwise the total is null or an explicit partial. An account quota change is not this task's usage.
Before/after comparisons need the same task class, the same required quality, a similar source and
environment, and every failed attempt.
