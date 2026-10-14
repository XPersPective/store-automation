# Runtime reference

`SA` = `python "<skill>/store.py" --project "<app root>"`. Python 3.11+ standard library and git; no
network, no paid API, no other skill. Plan commands print short text lines; `doctor`, `legacy` and
`release-readback` print JSON. Exit codes: 0 ok, 1 warnings / UNVERIFIED / REVIEW_PENDING / WAITING_USER /
a FAIL `check` / a readback that is not MATCHED, 2 errors or accept BLOCKED, 3 the command needs a plan and
there is none (`new`, `validate`). `boot` always exits 0 when it can report a state, including NO_PLAN.
`doctor` prints the interpreter path; use the same one for every `SA` call.

## Commands

| Command | Does |
|---|---|
| `doctor` | Python, interpreter path, git, plan presence, legacy state, skill path |
| `boot` | STATE (NO_PLAN, LEGACY, RESUME, INTERRUPTED, DIRTY, ADVANCED, CONFLICTED, READBACK_FIRST, NO_GIT), git line, product status, EXTERNAL, FIX (review BLOCKED), REVIEW queue, QUESTIONS, PLAN, FOCUS with criterion ids, RECENT, STALE, LOAD, CMDS, MODE, NEXT. INTERRUPTED = the IN_PROGRESS task has uncommitted changes in its Areas; a clean one is RESUME |
| `map` | File tree summary, root/doc files, legacy markers, detected commands |
| `init` | Creates the plan skeleton (never overwrites) and the AGENTS.md pointer; refuses if `.store-automation/` is gitignored |
| `new "title" [--priority] [--tier] [--risk] [--milestone] [--depends]` | Next SA-NNN as a PLANNED scaffold; IDs are never reused (history of every local branch checked; fetch first so remote branches count) |
| `start SA-NNN --owner <id> [--takeover "reason"]` | READY or unblocked BLOCKED → IN_PROGRESS under a checkout lock (`runs/writer.lock`): refuses a second writer, a non-executable or malformed spec, dependencies without completion evidence, and a MEDIUM/HIGH or security/integration/remote task without a `- ready by <id>:` Notes line; another owner's IN_PROGRESS/REVIEW task only with `--takeover`. Writes `- start by <owner> \| risk=<R> \| contract=<hex>` to Notes |
| `check SA-NNN --as <id> [--timeout s]` | Runs each Verify line in a contained process tree with an empty Python bytecode cache, full log to `runs/` ending in a verdict footer, writes `[machine]` evidence; source changing during the run → FAIL. On REVIEW any named agent may check (a reviewer reruns Verify) |
| `evidence SA-NNN --as <id> --kind K --note "..." [--criterion ID]... [--file F]...` | Writes a non-machine observation for the named criteria (default: the only item of that kind); `visual` needs a screenshot/recording file; `machine` is refused |
| `review SA-NNN --reviewer <id> --verdict PASS\|BLOCKED [--finding "..."]...` | The reviewer must not be anyone who started the task; review is bound to digest and contract |
| `accept SA-NNN --as <id>` | DONE / REVIEW_PENDING / WAITING_USER / UNVERIFIED / BLOCKED; on DONE sets Status and prints commit trailers |
| `changed` | Files changed since the applicable current.md checkpoints, by domain |
| `validate` | FAIL: grammar, statuses, Owner, kind tags, External lines, a missing RA-1 probe, dependency cycles. WARN: Verify shell use or files outside Areas, a HIGH-risk subject under lower Risk, UI work without visual+interaction+accessibility items, a risky task without `ready by`, ADR shape, budgets |
| `legacy [--apply] [--path P]... [--drop-archive [--confirm-untracked]]` | Finds foreign planning/state systems (Project Brain, Task Master, memory bank, Kiro specs, 2.x factory, or `--path`); `--path` refuses infrastructure in any spelling (`.git`, `.store-automation`, `.github`, AGENTS/CLAUDE/GEMINI.md, `.gitignore`) and any folder holding program source. `--apply` refuses until a valid plan exists (trace completeness is the strong model's duty) and while tracked foreign files have uncommitted edits, then moves them to `../store-automation-legacy-archive/<project>-<path hash>-<time>/` with `ADOPTION.json` and drops their ignore lines and pointers. `--drop-archive` deletes only this project's archives, only after a commit carries `SA-Legacy-Adoption: <archive name>`, and only with `--confirm-untracked` when they hold files that were never in Git; without git it never deletes |
| `release-readback --request file.json` | Compares `{expected, observed}` release objects; every text value is one printable line of at most 500 characters |

## Task file grammar

Header lines before the first `## ` heading, one per line: `Status`, `Priority`, `Tier`, `Risk`,
`Milestone`, `Depends`, `Owner`, `Areas` (backticked globs), `Domains`, `Blocked`. Sections: Objective,
Steps, Acceptance, Verify, Escalate if, External, Evidence, Review, Resume, Notes.

- Acceptance: `- [ ] [kind] text` / `- [x] [kind] text`.
- Verify: `` - `command args` `` — split like a POSIX shell, run without a shell. Windows resolves
  `npm`, `flutter`, `npx` (.cmd/.bat) from PATH; `./gradlew` style paths resolve from the project root.
  Arguments to a .cmd/.bat containing `& | < > ^ % ! "` are refused (cmd.exe would execute them).
  Secret-looking environment variables (TOKEN, SECRET, PASSWORD, API_KEY, `*_KEY`, `*_PAT`, DSN,
  DATABASE_URL, AUTH, COOKIE…) are removed. POSIX: a descendant that starts its own session escapes the
  process-group kill; Windows jobs contain every descendant.
- External: `- <operation> | not_started|sent|confirmed|response_unknown | readback: <how>`.
- Resume: `Next:`, `Failing:`, `Dirty:` lines.
- Evidence and Review lines are tool-written (a hand-written or edited line is refused by `accept`):
  `- [machine] check `cmd` | PASS | exit=0 | 3.1s | by=<id> | digest=<16 hex> | contract=<16 hex> | log=runs/<file>.log@<16 hex>`,
  `- [visual] note | criterion=<6 hex>[,...] | files=shot.png@<16 hex> | by=<id> | digest=<16 hex> | contract=<16 hex>`,
  `- review by <id> | PASS | digest=<16 hex> | contract=<16 hex>` followed by
  `- finding BLOCKER|MAJOR|QUALITY|MINOR: text [| accepted: reason | owner: user|SA-NNN]`.
- Criterion id: the first 6 hex of sha256(`kind|text`) of an Acceptance item; `boot` and `accept` print it.
- `[interaction]` evidence needs `--file` (recording, trace) or a note of the real steps: `step -> step -> result`.
- Agent ids (`--owner`, `--as`, `--reviewer`): letters, digits, spaces and `. : @ / + - _`, at most 80 characters.
- `runs/` is pruned on every `check`: logs an open task cites stay; others go after 14 days, and the oldest
  beyond 200 at once. Evidence files that must survive belong in `.store-automation/evidence/<task>/`.
- Contract: digest of Objective, Steps, typed Acceptance (not the ticks), Verify, Escalate if, Areas, Risk
  and Tier. Priority, Owner, Status and the working sections are not part of it.

`--as` names the acting agent: on IN_PROGRESS only the Owner may act; on REVIEW the Owner or the latest
reviewer (any named agent may `check`). Anyone else must `start --takeover` first.

## Acceptance rules (`accept`)

0. The task grammar is valid (what `validate` fails on: Status, Risk, kind tags, External states, a
   backticked Verify, Areas, Owner); otherwise BLOCKED.
1. Every Acceptance box ticked; open boxes are listed as missing with their criterion ids.
2. Each Verify command's latest check is PASS on the current digest and contract, and its log exists in
   this checkout with the recorded hash and a matching verdict footer (log missing → UNVERIFIED, rerun
   `check`; log different → BLOCKED).
3. Each ticked non-machine item has its own evidence line naming its criterion, on the current digest and
   contract; referenced files still hash the same (changed file → BLOCKED).
4. External operations are not `sent` / `response_unknown`.
5. Effective risk = the highest of the current Risk and every Risk `start` recorded. MEDIUM/HIGH: latest
   review on the current digest and contract, by an agent that never started the task, verdict PASS;
   BLOCKER/MAJOR findings block; QUALITY blocks unless `accepted: <reason> | owner: user`; MINOR needs
   `accepted: <reason> | owner: user|SA-NNN` (an open follow-up task). Only the review missing → Status
   REVIEW and REVIEW_PENDING.
6. Only `user_feedback` items open (review aside) → Status BLOCKED, `Blocked: user feedback: <item>`, Owner
   cleared, WAITING_USER; boot lists it under QUESTIONS.
7. All satisfied → Status DONE, an `accept: DONE` evidence line and the trailers to commit. A pre-commit hook
   that rewrites staged files makes the evidence stale: `check` and `accept` again.

The digest covers public files matched by Areas (tracked and untracked, ignored excluded; private names
such as `.env`, `key.properties`, `*.jks` skipped; linked paths refused; CRLF hashed as LF so another
`core.autocrlf` keeps the evidence). Files outside Areas do not invalidate evidence: write Areas to include
every source and test the Verify depends on (`validate` warns when a Verify argument names a file outside).
`boot` recomputes the digest of the newest DONE commit from its committed bytes and warns when it differs
from the accepted one (a hook rewrote files, or Areas files were left out of the commit).
`**/x` globs also match `x` at the root.

## Trust boundary

Evidence proves the recorded command ran on those bytes; it does not prove the condition is the right
one. Owner, reviewer and `SA-Agent` are declared identities: the rules stop honest mistakes and casual
self-review, not a forger running as the same OS user. `release-readback` compares what the supervisor
observed with the real store tool; it never contacts a store. Instructions are not an OS sandbox.
