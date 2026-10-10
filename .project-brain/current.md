# Current Architecture
## Runtime
- Python stdlib factory CLI; OpenCode global1.17.18 preserved, isolated factory1.18.0 runtime installed.
- Flutter3.47.2/Dart3.13.2 and Fastlane2.239.0 installed; Windows Android host, no Xcode.
## Map
- `opencode.json` — native three roles, free provider/model whitelist and scoped permissions.
- `.opencode/prompts/` — supervisor, worker and fresh read-only reviewer instructions.
- `.opencode/skills/` — lazy workflow and existing publishing integration.
- `contracts/` — validated persona/task examples and capability registry.
- `tool/factory.py` — validation, routing/dispatch, exact scope, source snapshots, fixed checks, evidence gate, bootstrap.
- `tool/start-factory.ps1` — isolated native launch with sanitized/restored environment.
- `tests/test_factory.py` — stdlib boundary/negative checks independent of live Brain task state.
- `tests/fastlane/` — local no-store smoke lane.
- `docs/architecture.md` — completed three critiques/final architecture.
- `docs/roadmap.md`, `docs/services.md`, `docs/skill-audit.md` — phase/service/context policies.
- `.factory/runs/` — local actual run evidence; ignored, hashes summarized in docs/evidence.
- `.factory/workspaces/` — isolated generated probes; no user app overwritten.
- `.project-brain/` — canonical unfinished state and external blockers.
## Domains
### factory
Status: VERIFIED
Sources: `tool/**`, `tests/**`, `.opencode/**`, `contracts/**`, `opencode.json`, `docs/**`, `README.md`, `AGENTS.md`, `.gitignore`
- Three native roles discovered; native worker→fresh reviewer read smoke passed on free model.
- Another free model resumed same native session on1.18; source-read recovery, no duplicate implementation.
- Official Codex ChatGPT snapshot handoff worked; host read-only shell blocked, not filesystem execution proof.
- Seventeen stdlib tests pass. Independent review found gate/fallback/serialization/audit defects; fixes verified, fresh native re-review PASS and exported-session machine gate ACCEPTABLE.
- Native write-scope regression corrected per v1.18; actual bounded write and fresh read-only review passed (docs/evidence/native-write.json).
- Safe Fastlane local smoke passed; existing AppPublishing and StorePublishMatic files unchanged.
- Global skills preserved; irrelevant factory skills scoped deny. No new MCP/provider adapters.
## Known Unknowns
- Seven generated modes analyze/test passed; shared workspace 141 tests and fatal analysis passed. Free/monthly release APKs built; free Android emulator screenshot inspected.
- Live receipt/backend/store and iOS/Xcode are PB-002 blockers. Remote HEAD readback succeeded; audited source changes are locally committed and both source working trees clean. Remote release tags remain unpublished.

- Source-repository queues closed with preserved specs/evidence in Git; full archive bootstrap passed generator/fatal analyze/tests/release APK. Android placeholder and archived-helper lint regressions corrected in both source repos.

- Final installer checkpoint: 17 stdlib tests, fresh v4 native review PASS and exported-session gate ACCEPTABLE. Generated-app partial writes now block model fallback. PB-001 complete; PB-002 is the remaining external acceptance task. docs/report.json and docs/evidence/final-review.json preserve exact local evidence and limits.
