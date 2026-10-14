# Runtime reference

`SA` = `python "<skill>/store.py" --project "<app root>"`. Python 3.11+ standard library and git; no
network, no paid API, no other skill. Plan commands print short text lines; `doctor`, `legacy` and
`release-readback` print JSON. Exit codes: 0 ok, 1 warnings / UNVERIFIED / REVIEW_PENDING / WAITING_USER,
2 errors or BLOCKED, 3 the command needs a plan and there is none (`new`, `validate`). `boot` always exits
0 when it can report a state, including NO_PLAN.

## Commands

| Command | Does |
|---|---|
| `doctor` | Python, git, plan presence, legacy state, skill path |
| `boot` | STATE (NO_PLAN, LEGACY, RESUME, INTERRUPTED, DIRTY, ADVANCED, CONFLICTED, READBACK_FIRST, NO_GIT), git line, product status, EXTERNAL, REVIEW queue, PLAN, FOCUS, RECENT, STALE, LOAD, CMDS, MODE, NEXT |
| `map` | File tree summary, root/doc files, legacy markers, detected commands |
| `init` | Creates the plan skeleton (never overwrites) and the AGENTS.md pointer; refuses if `.store-automation/` is gitignored |
| `new "title" [--priority] [--tier] [--risk] [--milestone] [--depends]` | Next SA-NNN as a PLANNED scaffold; IDs are never reused (Git history checked) |
| `start SA-NNN --owner <id> [--takeover "reason"]` | READY or unblocked BLOCKED → IN_PROGRESS, records Owner; refuses a second writer and non-executable specs; another owner's IN_PROGRESS/REVIEW task only with `--takeover`, recorded in Notes |
| `check SA-NNN --as <id> [--timeout s]` | Runs each Verify line in a contained process tree, full log to `runs/`, writes `[machine]` evidence with the Areas digest; source changing during the run → FAIL |
| `evidence SA-NNN --as <id> --kind K --note "..." [--file F]...` | Writes a non-machine observation with the digest and file hashes; `machine` is refused |
| `review SA-NNN --reviewer <id> --verdict PASS\|BLOCKED [--finding "..."]...` | Reviewer must differ from Owner; review is bound to the digest |
| `accept SA-NNN --as <id>` | DONE / REVIEW_PENDING / WAITING_USER / UNVERIFIED / BLOCKED; on DONE sets Status and prints commit trailers |
| `changed` | Files changed since the applicable current.md checkpoints, by domain |
| `validate` | Grammar, statuses, Owner, kind tags, External lines, Verify shell use, budgets, dependency cycles |
| `legacy [--apply] [--path P]... [--drop-archive]` | Finds foreign planning/state systems (Project Brain, Task Master, memory bank, Kiro specs, 2.x factory, or `--path`); `--apply` refuses until a valid plan exists (trace completeness is the strong model's duty), then moves them to `../store-automation-legacy-archive/<project>-<time>` and drops their ignore lines and pointers; `--drop-archive` deletes the archive after the removal is committed |
| `release-readback --request file.json` | Compares `{expected, observed}` release objects |

## Task file grammar

Header lines before the first `## ` heading, one per line: `Status`, `Priority`, `Tier`, `Risk`,
`Milestone`, `Depends`, `Owner`, `Areas` (backticked globs), `Domains`, `Blocked`. Sections: Objective,
Steps, Acceptance, Verify, Escalate if, External, Evidence, Review, Resume, Notes.

- Acceptance: `- [ ] [kind] text` / `- [x] [kind] text`.
- Verify: `` - `command args` `` — split like a POSIX shell, run without a shell. Windows resolves
  `npm`, `flutter`, `npx` (.cmd/.bat) from PATH; `./gradlew` style paths resolve from the project root.
  Secret-looking environment variables (TOKEN, SECRET, PASSWORD, API_KEY…) are removed.
- External: `- <operation> | not_started|sent|confirmed|response_unknown | readback: <how>`.
- Resume: `Next:`, `Failing:`, `Dirty:` lines.
- Evidence and Review lines are tool-written:
  `- [machine] check `cmd` | PASS | exit=0 | 3.1s | digest=<16 hex> | log=runs/...`,
  `- [visual] note | files=shot.png@<16 hex> | digest=<16 hex>`,
  `- review by <id> | PASS | digest=<16 hex>` followed by `- finding MINOR: text | accepted: reason | owner: who`.

`--as` names the acting agent: on IN_PROGRESS only the Owner may act; on REVIEW the Owner or the latest
reviewer. Anyone else must `start --takeover` first.

## Acceptance rules (`accept`)

1. Every Acceptance box ticked; open boxes are listed as missing.
2. Each Verify command's latest check is PASS on the current Areas digest.
3. Each non-machine kind that is ticked has evidence on the current digest; referenced files still hash
   the same (changed file → BLOCKED).
4. External operations are not `sent` / `response_unknown`.
5. MEDIUM/HIGH: latest review on the current digest, reviewer ≠ Owner, verdict PASS; BLOCKER/MAJOR
   findings block; MINOR needs `accepted: <reason> | owner: user|SA-NNN` (an open follow-up task; `review`
   refuses any other owner). Only the review missing → Status REVIEW and REVIEW_PENDING.
6. Only `user_feedback` items open (review aside) → Status BLOCKED, `Blocked: user feedback: <item>`,
   WAITING_USER; boot lists it under QUESTIONS.
7. All satisfied → Status DONE, an `accept: DONE` evidence line and the trailers to commit.

The digest covers public files matched by Areas (tracked and untracked, ignored excluded; private names
such as `.env`, `key.properties`, `*.jks` skipped). Files outside Areas do not invalidate evidence:
write Areas to include every source and test the Verify depends on.

## Trust boundary

Evidence proves the recorded command ran on those bytes; it does not prove the condition is the right
one. Owner, reviewer and `SA-Agent` are declared identities: the rules stop honest mistakes and casual
self-review, not a forger running as the same OS user. `release-readback` compares what the supervisor
observed with the real store tool; it never contacts a store. Instructions are not an OS sandbox.
