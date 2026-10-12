# Current Architecture
## Runtime
- Python3.11 stdlib portable skill/CLI on Windows; selected cwd owns project state. Official native clients retain authentication.
- Globally managed Skills Manager library plus extra owned CLI roots and user PATH launcher; versions/resources are verified at distribution, never inferred from host presence.
## Map
- `tool/factory.py` — selected-project adopt/boot, cached model catalogue, contracts, Codex read-only snapshots, routing, evidence gates, bootstrap.
- `tool/subscriptions.py` — official bounded discovery, separate volatile Codex/AGY account observations, assessed risk/effort selection and measured usage coverage.
- `tool/dispatch.py` — public immutable assignment/announcement, shared-bucket admission, safe handoff and stale-controller reconciliation.
- `tool/sessions.py`, `tool/native_agents.py` — contained native processes/RPC, ownership, cleanup and optional provider-specific controls.
- `tool/artifacts.py` — explicit public image manifest and byte/source provenance; no HTTP server.
- `tool/release.py`, `tool/ios-evidence.py` — canonical AppPublishing public preflight and bounded iOS image-log extraction.
- `tool/install-skill.py` — owned-manifest upgrade, safe retired-resource removal and launcher.
- `skills/store-automation/` — single entry; routing/persona/lifecycle/product-delivery/architecture-review/publishing references.
- `contracts/`, `.opencode/`, `opencode.json` — task format, measured capability policy and native personas.
- `tests/`, `.github/workflows/checks.yml` — stdlib boundary/lifecycle/regression checks; Windows/Linux CI.
- `docs/evidence/`, `docs/report.json` — public verification/limits; raw runs ignored.
- `.project-brain/` — repository-owned state; selected applications own separate Brains.
## Domains
### factory
Status: VERIFIED
Sources: `tool/**`, `tests/**`, `.opencode/**`, `contracts/**`, `opencode.json`, `docs/**`, `README.md`, `AGENTS.md`, `.gitignore`, `skills/**`, `.github/**`
- 2.4.0 source: mandatory selected-project boot and cached catalogue preflight before supported Codex inference. Project `.factory/model-catalogue.json` created if absent, replaced only by explicit scan; invalid cache fails closed. Cached model pool and capture time remain separate from fresh auth/quota.
- Codex quota refresh omits model/list. Successfully listed models survive quota outage. Shared 10% reserve/unknown checks and risk floor gate automatic selection; known own-model family participates, unsupported models remain unassessed.
- Custom browser console/team and native-terminal UI launch removed. Director reports actual assignment/task/role/provider/model/effort/reason/budget and completion. Native containment/ownership primitives remain reusable; no automatic panel/panes.
- Supported automatic source handoff is official Codex ChatGPT read-only snapshots. Other routes lacking verified billing/quota/quality are blocked. Writes require verified host scope or director-applied reviewed patch.
- Installer validates all targets before writes/removals; deletes only unchanged previously-owned obsolete resources. Modified/unowned files preserved. Public screenshots retain exact-byte manifests.
- Full product protocol covers conditional backend, accessible frontend, store/marketing assets, scoped publication/readback and maintenance. Architecture prompt requires evidence, smallest solution and fresh independent correction review; prose cannot certify external outcomes.
- 130 stdlib tests PASS on final runtime; syntax/native config PASS. Final evidence in docs/evidence/release-240.md.
## Known Unknowns
- Generic provider billing/quota/capability and contained app-write adapters, automatic equivalent-worker replacement, quota-reset transport and active-chat model switching are not universally implemented. Open tasks retain these limits.
- Real store receipt/backend/account/signing, iOS/macOS/device acceptance and selected app publication need app-specific tools/access/evidence. No app store/backend production action performed here.
- Marketing strategy/text/asset production is specialist/tool protocol, not a universal media generator or guaranteed outcome. Licensing/factuality and actual publication require evidence.
- Same-user full-access AI cannot be isolated from private files by skill text; strict isolation requires separate OS identity/broker. Credentials stay native.
- Separate medication app remains in D:/repositories/ilac-vakti with its own Brain; unrelated pending work and unknown takeover logs preserved.

- Published store-automation-v2.4.0 in existing private GitHub repository; ZIP digest matches uploaded asset. Hosted Windows+Ubuntu run38249226813 SUCCESS.41 Skills Manager+4extra destinations match28resources; retired UI absent.
