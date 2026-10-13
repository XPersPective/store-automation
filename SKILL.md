---
name: store-automation
description: Plan, build, verify and release applications with a git-native plan any agent can resume. A strong model shapes the product, architecture and risk-ordered milestones; smaller models execute fully specified tasks; acceptance needs current evidence and independent review. Use for app ideas, existing app projects, continue/resume/devam et/kaldığın yerden, plans and roadmaps, adoption, release preparation and maintenance.
metadata:
  version: "4.0.0"
---

# Store Automation

**One plan, many agents, honest "done".** Any session can stop at any moment; the next agent, maybe a
smaller model from another vendor with no chat history, continues from the repository alone. State lives
in `.store-automation/` files and commits, never only in chat. Talk to the user in their language; plan
file headings and field names stay English, their content in the user's language.
`SA` = `python "<directory of this SKILL.md>/store.py" --project "<app root>"`. Python 3.11+ and git.

## 1. Start every session

1. `SA boot`. Read its output and the LOAD files before writes or tests. Route the user's message (§2).
2. Act on STATE: **NO_PLAN** → small request: just do it; multi-session work, new product, plan request or
   adoption → Genesis ([plan](references/plan.md) §6). **READBACK_FIRST** → read back every listed external
   operation with the existing tool before anything else; never resend first. **INTERRUPTED** → compare the
   diff with Resume; another owner's task needs `start --takeover "<reason>"`. **ADVANCED** → map the
   listed files in current.md and checkpoint. **CONFLICTED / DIRTY** → [edge cases](references/edge-cases.md).
   **QUESTIONS** → ask the user those first when present. **RESUME** → §2.
3. `SA doctor` shows `legacy` → 2.x or Project Brain state exists: `SA legacy` (preview), then
   `SA legacy --apply` before planning ([migration](references/migration.md)).
4. Takeover check once per session: run the configured test command; red → find the cause first.
   Trust nothing unverified, including your predecessor.

## 2. Route the message

| Message | Action |
|---|---|
| Question | Answer from current.md Map + targeted reads. No writes. |
| Trivial: ≤1 file, ≤20 lines, no behavior/API/data/security change | Do → verify → commit with `[SA]` in the subject. No task. |
| "continue", "devam", empty | Work the queue ([plan](references/plan.md) §3) until empty or all BLOCKED. |
| New feature, bug, refactor | `SA new` per independently verifiable piece; write it for a weaker model; then work it. |
| Product or flow feedback | Wrong goal/flow → goal change gate; visual/detail → edit the affected task; new scope → new task ([plan](references/plan.md) §5). |
| Plan, roadmap, audit | [plan](references/plan.md) §6–7. |
| Release | [release](references/release.md) with the existing AppPublishing/Fastlane setup. |

Keep the user's words: a short quote goes into the task Objective or the product Goal. Nothing the user
asked lives only in chat.

## 3. Roles and models

- **Strong model (tier H):** Genesis interview, product.md, architecture, milestones, writing executable
  task specs, plan changes, ADRs, and the REVIEW queue.
- **Smaller model (tier L/M):** READY tasks only. A task that needs invented design is not READY: stop,
  write Resume, leave it for a strong model.
- `SA start <task> --owner <your model id>` before implementing. Never review your own work.

## 4. Work a task

`start` → implement Steps → `SA check <task> --as <id>` (runs Verify, writes machine evidence) → for each
interaction/visual/accessibility/security/integration/remote item observe it for real and record it with
`SA evidence <task> --as <id> --kind <k> --note "..." [--file shot.png]` → tick an Acceptance box only with
that evidence → `SA accept <task> --as <id>`. Results: **DONE** (commit with the printed trailers, push, delete the task
file in the next commit), **REVIEW_PENDING** (MEDIUM/HIGH: a different, stronger agent runs
`SA review <task> --reviewer <id> --verdict PASS|BLOCKED [--finding "..."]`, then `accept`),
**WAITING_USER** (only a user_feedback item is open: the task becomes BLOCKED with the question; other
work continues), **UNVERIFIED** (missing evidence listed) or **BLOCKED** (failing check, blocking finding,
stale artifact).

Evidence is bound to the content of the task's Areas: changing code after a check makes it stale. A
finished command, a COMPLETED report, passing tests, a screenshot and an upload each prove only themselves.

## 5. Before you stop

Write `## Resume` (Next / Failing / Dirty) in the active task, record any external operation in
`## External` as `- <op> | not_started|sent|confirmed|response_unknown | readback: <how>`, commit
(`SA-WIP: true` if unverified) and push per config. Report in ≤8 lines: done, blocked with what is
needed, next, commits. Never `git reset --hard`, `clean`, `stash`, `checkout --` or force-push on work
you did not create; preserve unknown user edits.

## 6. Product quality and boundaries

Show the riskiest assumption and the first working journey early; do not finish every screen on an
unverified assumption. For new products, flows, visual direction or architecture, generate 2–3 genuinely
different options with trade-offs before converging; guardrails protect existing decisions, not the
ambition of new ones. Quality lists are a floor, not a ceiling ([product quality](references/product-quality.md)).
No paid APIs, no reading or moving credential contents, no automatic billing/signing changes, no
production release without the selected destination and existing authority. Instructions are not an OS
sandbox; identities in Owner/reviewer/trailers are declared, not authenticated.

## References

[plan](references/plan.md) Genesis, specs, loop, audits · [edge cases](references/edge-cases.md) ·
[runtime](references/runtime.md) commands and formats · [product quality](references/product-quality.md) ·
[release](references/release.md) · [execution](references/execution.md) · [migration](references/migration.md)
