# Upgrades and adoption

4.0.0 keeps the plan and resume state in the project, in git (`.store-automation/`). Project Brain is no
longer needed: its plan, resume and map mechanics are part of this skill. The 3.x JSON flow (`task`,
`prepare`, `finish`, `record`, `snapshot`, `gate`, `handoff`, `usage`) was removed; the task file plus
`start/check/evidence/review/accept` replace it ([runtime](runtime.md)). Never route an old command name
silently to a command that does something else.

## Removing old state: `legacy`

When `SA doctor` shows `legacy`, before planning:

1. `SA legacy` previews: 2.x `.factory/` and `.factory-bootstrap.json`, Project Brain `.project-brain/`
   (schema 4 only), file count/size, old handoff names, `.gitignore` lines to remove, plan files to
   convert, the archive path.
2. If old handoffs or Brain tasks hold open work, read the preview; after conversion summarize it in the
   matching task's Resume.
3. `SA legacy --apply`:
   - moves old directories in one same-volume rename each to `store-automation-legacy-archive/<project>-<time>`
     beside the project; nothing is deleted;
   - converts a Brain plan: `target.md` → `product.md` (missing Users / Core Journeys / Platforms / Riskiest
     Assumptions sections are added as UNKNOWN), `PB-NNN` → `SA-NNN`, dependencies on tasks that are no
     longer open are removed with a Notes line, `config.yaml` → `config.json`, the AGENTS.md Brain pointer
     is replaced by this skill's pointer;
   - removes `.factory` and whole-`.store-automation/` ignore lines (the plan must be tracked; only
     `runs/` stays ignored through its own `.gitignore`).
4. It moves nothing when 2.x files are tracked by git, a path is linked, a file is open or a process
   runs inside, or both a Brain and a new plan exist.
5. Untagged Acceptance items in converted tasks fail `validate`; a strong model adds each item's evidence
   kind deliberately, never by guessing. UNKNOWN product.md sections are filled in the adoption interview.
6. Record it in one commit (`chore(plan): adopt store-automation 4`, `SA-Current-Checkpoint: all`).
   Tracked `.project-brain` files show as deleted in that commit; git history keeps them. Delete the
   archive once nothing needs it.

Old receipts, Brain evidence and 3.x `.store-automation/runs/*.json` records never become PASS; they are
history. Acceptance is produced again with `check/evidence/review` on current source.

## Adopting an existing app

Follow [plan](plan.md) §6, plus:

1. Inspect git state, relevant sources and callers, tests, design and release setup. The short inventory
   goes into current.md: run/build/test commands with real results, target platforms, data stores and
   schemas, design token/component source, release lanes. Note only the existence and location of
   secrets, never their content.
2. If no check runs at all, add the smallest real smoke check before any change and put it in config.json.
3. Preserve unknown diffs. Never start a writer over one not known to have stopped. With an uncertain
   upload, read back from the existing release tool before any replay.
4. Keep compatible source, napp/Fastlane, design and tests. No new folders or backend just for a template.

## Upgrading the skill package

Source and installed package are separate. package.py copies only SKILL.md, store.py, runtime Python and
reference Markdown files into a new empty directory with a hash manifest and refuses to overwrite. Test the
package in its own directory with doctor and the test suite.

With a Skills Manager record, update the source keeping the same id/tags/preset/deployments; never
remove+install. After the update, confirm with `skills status` that no agent deployment dropped and check
the installed hashes against the manifest. Unmanaged copies are replaced only when they are byte-identical
to the previous release.

Rollback: move the new source and installs aside, restore the backup. Keep git history, unknown diffs and
the Skills Manager metadata backup. Never migrate another app's data schema automatically.
