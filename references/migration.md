# Upgrades and adoption

4.0.0 keeps the plan and resume state in the project, in git (`.store-automation/`). Project Brain is no
longer needed: its plan, resume and map mechanics are part of this skill. The 3.x JSON flow (`task`,
`prepare`, `finish`, `record`, `snapshot`, `gate`, `handoff`, `usage`) was removed; the task file plus
`start/check/evidence/review/accept` replace it ([runtime](runtime.md)). Never route an old command name
silently to a command that does something else.

## Removing old state: `legacy`

Any foreign planning or state system (Project Brain of any schema or `PROJECT_BRAIN.md`, Task Master, a
memory bank, Kiro specs, Store Automation 2.x `.factory`, or a path you identify) is taken over the same
way: a strong model extracts its goal, decisions, current state, open work, blockers and pending external
operations into the plan with a trace of every open item ([plan](plan.md) §6a); `SA legacy --apply`
then moves it out of the project (it refuses while plan content is not extracted, or when a path is
linked, open or in use) and drops its ignore lines and known pointer blocks; after the adoption commit
`SA legacy --drop-archive` deletes the archive. Tracked files remain in Git history. Old receipts and
PASS claims never become evidence.

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
