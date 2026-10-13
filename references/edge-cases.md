# Edge cases

Read only the heading you need. SKILL.md and plan.md win on conflict. Universal rule:
**observe → reconcile → replan → continue**; observation over assumption, preservation over cleanup.

## Dirty genesis
Plan introduced into a repo with uncommitted work: list `git diff --name-only`, `git diff --cached
--name-only`, `git ls-files --others --exclude-standard`; classify each path as user / generated /
unknown and leave them alone. Stage only `.store-automation/` (and the AGENTS.md pointer if that file had
no user edits). If the index already holds user-staged files, `git commit --only -- .store-automation`.

## Missing checkpoints
No `SA-Current-Checkpoint` trailer yet (fresh adoption, squash stripped it): boot falls back to the last
commit touching current.md. Spot-check the domains your task needs and checkpoint them at your next
commit. Never rewrite old commits to add trailers. WIP checkpoints are ignored.

## History modes
Squash merges: the surviving commit must carry `SA-Tasks: <all ids>`, `SA-Verification`,
`SA-Current-Checkpoint`; move rationale that lives only in intermediate commits into an ADR first.
Rewrite-prone history: task IDs are identity, SHAs are temporary.

## Branch change
Branch differs from the one you last worked on: plan files present and the branch descends from the
genesis commit (`git merge-base --is-ancestor`) → `SA changed`, reconcile, continue. Unrelated branch →
separate context; never copy task state across.

## Detached HEAD
Read-only work is safe. Before implementation commits create a branch if policy allows
(`git switch -c sa/<task>`); otherwise work read-only and report.

## Conflicts
Merge/rebase/cherry-pick/revert in progress: inspect each conflicted file; resolve only conflicts whose
intent you understand from both sides, otherwise BLOCKED with the file list. Never start an unrelated
task mid-operation. Afterwards `SA changed`, reconcile, re-run checks (old evidence is stale by digest),
checkpoint. A clean Git merge is not semantic verification.

## History rewrite
Force-pushed or rebased remote, missing checkpoint commit: task IDs, current.md, product.md, constraints
and ADRs carry the meaning. `git log --grep=SA-Task` for surviving history; verify the domains you need.

## Shallow
A shallow clone cannot prove that a task or checkpoint never existed. Work from the plan files.
`git fetch --deepen=<n>` only when history is truly needed and policy allows; `new` may reuse a hidden ID.

## Sparse
Hidden paths may hold architecture: scope current.md claims to visible domains, mark others UNKNOWN.

## Worktrees
Each worktree has its own HEAD, index and dirty state; never use another worktree's uncommitted files.
One agent per worktree, disjoint Areas, fetch before checkpointing long work, reconcile before merging.

## Remote divergence
Before pushing: `git fetch`, compare with upstream. Remote advanced → inspect, integrate per repo policy,
re-verify, then push. Never force-push to make local history win.

## No remote
`git remote` is empty: commits are local checkpoints only and boot says so. Do not create a remote or
change `git.push`; say "local only" in the stop report. Another machine cannot resume until the user adds
a remote.

## Abandoned owner
IN_PROGRESS or REVIEW task owned by another agent. Evidence it stopped: its session ended, the user says
so, or no commits and no file changes in its Areas for a long time (check `git log -1` and file times).
Then `SA start <task> --owner <you> --takeover "<evidence>"`; verify everything inherited (rerun checks,
read the diff) before building on it. If it may still be running, work on something else.

## Push failure
The local commit is still a valid local checkpoint, just not durable. Do not retry destructive remote
operations. Note "not pushed" in the stop report; if continuity depends on the remote, BLOCKED.

## CI failure
Local success is not CI success. Infrastructure or flaky → note it, not a code bug; platform difference,
missing generated artifact, dependency resolution → fix task; real regression → P1 task. Revoke completion
claims whose evidence CI invalidated; never edit current.md because CI infrastructure failed.

## Submodules
Each submodule is a separate repository with its own plan. The parent records only the pointer.

## Monorepo
One `### domain` per package in current.md with its own Sources globs; checkpoint per domain
(`SA-Current-Checkpoint: api,mobile`). Respect nested AGENTS/CLAUDE/GEMINI.md rules.

## Generated files
Architecture comes from source, never from generated, vendored, lockfile, LFS or binary content.
Lockfile changes must be intentional, visible in the diff review and verified.

## No Git
Plan files still work; boot says NO_GIT. Keep finished tasks as `Status: DONE` with Evidence; do not
delete them (IDs and dependencies stay visible). Never `git init` unasked. Takeover is weaker: say so.

## Corrupt plan
Malformed config.json, duplicate/cyclic IDs, several IN_PROGRESS, current.md contradicting code widely:
`SA validate`; `git log --oneline -10 -- .store-automation` to find the last good version; keep every
piece of user intent that still parses; rebuild only demonstrably invalid state from code and Git;
repair tasks for what you cannot fix now; commit `docs(plan): repair`.

## Crash recovery
| Found | Do |
|---|---|
| clean tree at a checkpoint | normal boot |
| `SA-WIP` commit | resume from the task's Resume; re-run checks (evidence may be stale) |
| dirty, task IN_PROGRESS | boot says INTERRUPTED/DIRTY; compare `git diff` with Resume |
| task REVIEW | strong model reviews; weaker model takes other work |
| task DONE with Evidence, uncommitted | commit it with the trailers `accept` printed |
| deleted task with no completion evidence | deletion is not completion; recover the spec from Git |
| `*.md.tmp` beside a task | an interrupted write; the `.md` file is the last complete version; delete the tmp |
| External line `sent` or `response_unknown` | READBACK_FIRST: read the remote state before any retry |
| half-written source file | check syntax; restore that one file from `git show HEAD:<path>` only if it is yours |
| `.git/index.lock` | no git process running (check) → delete the lock |

## Migrations
Persistent-state changes are HIGH risk: up and down migration, rollback, old/new app compatibility
during rollout, deploy order, existing data, destructive transforms. Run them where an environment
exists; static review alone is not completion.

## Security
Auth, authorization, sessions, crypto, secrets, permissions, data exposure, payments → HIGH risk, full
verification, independent review, escalate unless the user explicitly requested that change. Never
write credentials into plan files, tasks, trailers, ADRs or notes.

## Unknown situation
Stop changing things; preserve coherent work (WIP commit if needed); observe (`git status`,
`git log --oneline -5`, `SA boot`); reconcile the plan with what you saw; tasks for the gaps; continue.
