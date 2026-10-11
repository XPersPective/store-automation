# Existing projects and release maintenance

Use the selected project's Brain, source, Git history and publishing mapping. Never import another project's task, user data or credential. Reuse a shared package repair through an explicit compatible immutable ref; record the originating issue/commit and rerun this app's checks. Similar symptoms in another app are a lead, not proof that its patch is safe here.

## Resume or reassess

Ask only missing choices: preserve/resume versus audit (archive needs an explicit choice), Windows/Web/Android/iOS targets and store intent, template/theme reuse, ads/subscription. Confirmed choices persist. Windows-only with no ads/store is valid. An unanswered optional preference preserves existing source, style and Brain; it does not authorize replacement or archival. Starter/core GitHub repositories/cache remain outside the installed skill. Once per session when network is available, use `sources --check-updates` to inspect configured dirty state/revision/upstream HEAD; select a compatible immutable ref per app, never blindly pull dirty sources or upgrade existing apps.

Ordinary continue preserves the current Brain. For an existing project first adopted into this workflow, explain two choices in the user's language: preserve/resume the plan, or archive it and audit the whole product. Ask only this missing project choice, unless the user already chose. A complete audit can retain the current Brain; a fresh plan is optional.

`store-automation adopt --rebaseline` is read-only preview. After the explicit fresh-plan choice use `store-automation adopt --rebaseline --apply`. It moves this project's Brain/legacy file into ignored `.factory/brain-backups/<unique>/`, creates a fresh DRAFT skeleton and preserves source and Git history. Links are rejected, archives never overwritten, and failed initialization restores the previous plan. Do not delete archives. The supervisor audits actual callers/manifests/tests/history, records the user goal and constraints, and creates prioritized canonical tasks with exact checks. Old tasks are historical evidence, never automatically copied as new work. Follow the canonical Project Brain Genesis/audit protocol; a skeleton alone is not a completed reassessment.

## Product intake and stages

Before generation, ask the missing required choices together and record answers in the project's target/constraints. Already supplied answers need no confirmation. Optional aesthetics may keep the existing theme; unresolved platform, money, license, data or exclusions block the affected step.

- Product: purpose, users, core flows, locales, app/package identity; new project or adoption and its exact directory.
- Delivery: Windows/web/Android/iOS individually, store versus private/local distribution, selected destinations and supported devices. Host Windows does not imply Windows-only output.
- Monetization: free or paid download; no ads or explicit banner/rewarded/app-open/interstitial placements; lifetime/monthly/both or no purchase. Separate revenue choices from backend billing. Never add unwanted formats to fill template defaults.
- Source/design: napp starter/core/theme reuse, selected refs, product/source license and compatibility with dependency licenses; required and excluded features (sharing, cross-promotion, cloud sync). Explicit choices override inherited theme/modules/license. Unsupported generator switches become exact application tasks before acceptance, never ignored or silently substituted.
- Data: local-only or actual auth/sync/server/push needs; named provider or researched free candidates, card allowed or forbidden, paid plan/overage allowed or forbidden, required hard ceiling and quota failure behavior. Prefer local when it meets the confirmed need; compare Cloudflare/Firebase and alternatives service by service. No service or billing activation before the applicable choice is recorded.
- Quality/release: accessibility, privacy, native device/screenshot requirements, test/build budget, accounts/signing and exact release operation. Missing access is a concrete blocker, not a passed gate.

Track `Stage`, `Substage`, `Next gate` and evidence references in existing Brain Current; keep planned work in tasks and product decisions in Target/constraints. Do not add another state database. Genesis/adoption traces manifests, callers, source, Git, builds and release evidence to reconstruct stage; completed-looking code alone proves no completed gate. Each resume boots, inspects dirty/source changes, runs the takeover check and rechecks evidence affected since the checkpoint.

| Stage | Substages / exit evidence |
|---|---|
| Definition | intake, constraints, delivery/license/exclusions; confirmed product target |
| Discovery/design | subscriptions/models/effort/limits, backend comparison, external refs, UX; recorded decisions and task contracts |
| Implementation | scaffold, selected modules, core flows, platform integration; exact scoped diff and runnable checks |
| Verification | machine checks, native UX/accessibility/privacy, fresh independent review; source-bound evidence |
| Release preparation | package/version/signing prerequisites, localized listings/screenshots/declarations; canonical publishing preflight |
| Submission | exact authorized account/destination upload; remote readback/build/track and review status |
| Availability | actual published URL/version/store status; submission is not availability |
| Maintenance | monitor applicable policy/dependencies/issues; verified patch and release cycle |

Android/iOS publishing follows canonical AppPublishing/Fastlane, including actual approval/status readback. Windows follows the selected package/installer/portable/store channel and native startup/install/update checks; web follows the selected hosting/build/deploy/readback. The mobile-only `release-preflight` cannot certify Windows/web. All requested delivery work continues through these gates; unavailable signing/account/macOS/host controls stay named blockers with the next action.

## Maintenance run

1. Boot this project's Brain; check branch/dirty state and preserve unknown edits. Reconcile unfinished work before dependency changes. Use native inventory (`flutter pub outdated`, existing CI and store version/status) before dispatching models. Never read credential values.
2. Compare current authoritative SDK/API/security/store requirements and deadlines with actual direct/transitive dependencies, merged manifests, privacy behavior and supported devices. Look up prior verified shared fixes by issue/commit. Record date, source links, impact and a concrete task; no speculative bulk upgrades.
3. Choose the smallest compatible fix, detailed task persona and sufficient verified model. Implement one task at a time, run meaningful regressions and fresh independent review. API failure is not automatically quota failure; no blind retry/account rotation or paid fallback.
4. Verify affected Android and [free-only iOS evidence](ios-ci.md), user flows, permissions/denials, accessibility, screenshots and compatibility. Source-only review cannot accept a visual change. Tests do not prove signing, receipts or store compliance.
5. For a release candidate compare remote version/build numbers, choose the next version, write truthful localized release notes from the final diff, and run canonical AppPublishing/Fastlane preparation. Follow [publishing](publishing.md) and fresh official store gates. Never fabricate Console answers, health claims or completed review.
6. Exact prior app/account/track/operation authorization persists. Missing signing/account/declarations/production destination is a recorded blocker; generic installation does not select a production rollout. After an authorized remote write read back version, track and status. Resume from that checkpoint after interruption; avoid duplicate uploads and assumed store approval.

When periodic maintenance is requested, use the host's native recurring-task facility for explicitly selected repositories. Keep unchanged state quiet; notify meaningful changes, failures, login needs or completion. Retain project isolation and free-only policy. Do not install a second daemon or schedule arbitrary repositories just because they exist on disk.
