# Agent reporting and recovery

The current conversation is the director and the user-facing reporting surface. No custom agent console, browser dashboard, sidebar attachment, automatic terminal panes or watcher UI is required or launched. Native provider tools may be used explicitly when useful; they do not replace director reports or acceptance evidence.

## Before and after each assignment

Complete selected-project Brain boot and catalogue/account preflight from [CLI routing](cli-routing.md) before investigating the task. The director announces each worker or fresh reviewer before it starts: task and bounded objective, role, provider, exact model/effort, selection reason and quality floor, context/output budgets, quota state and any actual limitation. Keep updates concise and in the user's language. A blocked assignment is reported with its concrete next action; never announce an agent as running before native execution starts.

Each agent returns public status/completion/blockers and the contract's structured report: task, role, provider, model, effort, state, changed_files, evidence, usage, blockers and next_action. No hidden reasoning. Bind reports to the actual attempt/task/route, permissions and source snapshot. A fabricated/mismatched identity, malformed/empty report, ACK or exit zero cannot certify work. The director collects reports explicitly if the native host cannot relay them; do not claim continuous observation or immediate cross-conversation notifications.

One application writer at a time. Deterministic checks need no model. Workers receive task-specific personas and bounded source/caller context, cannot change Brain or tool policies, and cannot exceed exact app write scope. Read-only native snapshot routes stay read-only; unsupported write containment requires a scoped supported worker or a reviewed patch proposal applied by the director. Same-user CLI access is not an OS-enforced read whitelist.

After execution the director inspects the actual diff and runs machine checks. A fresh independent reviewer receives the risk, acceptance, source and real evidence, rather than inheriting the worker's verdict. Same provider/model may review in a genuinely fresh session; the implementation session cannot review itself. The director accepts only when checks and independent review pass. Runtime/device/visual requirements need actual corresponding evidence. Missing reviewer, machine evidence or capability leaves that gate UNVERIFIED and the task open.

## Failure and intervention protocol

| Event | Required action |
|---|---|
| Missing catalogue | One bounded discovery, save, then account/quality gates |
| Corrupt or unsafe catalogue | Fail closed; report exact repair or explicit rescan action |
| Existing catalogue or session restart | Reuse metadata; refresh account fields only |
| Unknown/depleted quota, auth or billing | Block inference, report official status/login/reset action; no paid fallback |
| Unsupported model/tool/write capability | Mark affected route unavailable; choose another fully gated risk-sufficient route or checkpoint |
| Access denied, empty output, timeout or crash | Record failure; inspect actual writes/processes; diagnose before another attempt |
| User changes direction | Stop/pause affected writer using its supported owned control, checkpoint and reconcile contract before resume |
| Reviewer finds a defect | Record failed criterion, return bounded correction to a worker, rerun affected checks and fresh review |
| Review unavailable or conflicting evidence | Keep acceptance UNVERIFIED; director resolves evidence rather than self-certifying |
| Quota reserve reached | Save partial diff and continuation; wait/reset or safely replace with an equally capable fully gated route |

Do not blindly replay mutators or start a concurrent replacement. An optional unanswered model preference uses an approved automatic choice; a required login/permission/account decision remains blocked. Do not repeat expensive failed attempts without new evidence. Completion/reassignment updates name the actual outcome, changed files, verified checks, usage or unknown counters, blockers and next action.

## Takeover and cleanup

Before changing director/provider persist a handoff: selected project, task/contract hash, actual source hashes/diff, first unchecked acceptance, pending reports/checks, worker/session ownership, usage and concrete next action. Use the native supported handoff or `handoff --contract ... --attempt ... --next-action ...`; never transfer tokens or provider session IDs between clients.

The incoming director boots the same Brain, reuses the catalogue, refreshes account gates, verifies real processes and partial work, then reconciles the checkpoint. Recover an owned stale lock only after proving the recorded owner and workers absent; denied process inspection is not proof of death. Stop only owned children and preserve unknown/user edits. An interrupted write cannot be accepted from a prior report or replayed without inspecting its diff.

Optional provider-specific session/message/interrupt/resume controls require real IDs and verified project/permission ownership. Their ACK establishes only receipt; reconcile the changed contract before continuing. Unknown interfaces remain explicit limits. `activity` is sanitized durable attempt evidence, not a UI or acceptance claim.

Keep raw execution evidence ignored in the selected project's `.factory/runs/`. Preserve reports needed for reproducibility and handoff; keep current Brain concise and let Git retain completed history. Never delete unknown evidence, user files or provider session history as routine cleanup. Do not publish prompts/source dumps, credentials, account identities or hidden reasoning. Artifact inspection must bind actual image/build/source/device provenance; manifest registration alone does not prove visual acceptance.
