# Existing projects and release maintenance

Use the selected project's Brain, source, Git history and publishing mapping. Never import another project's task, user data or credential. Reuse a shared package repair through an explicit compatible immutable ref; record the originating issue/commit and rerun this app's checks. Similar symptoms in another app are a lead, not proof that its patch is safe here.

## Resume or reassess

Ordinary continue preserves the current Brain. For an existing project first adopted into this workflow, explain two choices in the user's language: preserve/resume the plan, or archive it and audit the whole product. Ask only this missing project choice, unless the user already chose. A complete audit can retain the current Brain; a fresh plan is optional.

`store-automation adopt --rebaseline` is read-only preview. After the explicit fresh-plan choice use `store-automation adopt --rebaseline --apply`. It moves this project's Brain/legacy file into ignored `.factory/brain-backups/<unique>/`, creates a fresh DRAFT skeleton and preserves source and Git history. Links are rejected, archives never overwritten, and failed initialization restores the previous plan. Do not delete archives. The supervisor audits actual callers/manifests/tests/history, records the user goal and constraints, and creates prioritized canonical tasks with exact checks. Old tasks are historical evidence, never automatically copied as new work. Follow the canonical Project Brain Genesis/audit protocol; a skeleton alone is not a completed reassessment.

## Maintenance run

1. Boot this project's Brain; check branch/dirty state and preserve unknown edits. Reconcile unfinished work before dependency changes. Use native inventory (`flutter pub outdated`, existing CI and store version/status) before dispatching models. Never read credential values.
2. Compare current authoritative SDK/API/security/store requirements and deadlines with actual direct/transitive dependencies, merged manifests, privacy behavior and supported devices. Look up prior verified shared fixes by issue/commit. Record date, source links, impact and a concrete task; no speculative bulk upgrades.
3. Choose the smallest compatible fix, detailed task persona and sufficient verified model. Implement one task at a time, run meaningful regressions and fresh independent review. API failure is not automatically quota failure; no blind retry/account rotation or paid fallback.
4. Verify affected Android and [free-only iOS evidence](ios-ci.md), user flows, permissions/denials, accessibility, screenshots and compatibility. Source-only review cannot accept a visual change. Tests do not prove signing, receipts or store compliance.
5. For a release candidate compare remote version/build numbers, choose the next version, write truthful localized release notes from the final diff, and run canonical AppPublishing/Fastlane preparation. Follow [publishing](publishing.md) and fresh official store gates. Never fabricate Console answers, health claims or completed review.
6. Exact prior app/account/track/operation authorization persists. Missing signing/account/declarations/production destination is a recorded blocker; generic installation does not select a production rollout. After an authorized remote write read back version, track and status. Resume from that checkpoint after interruption; avoid duplicate uploads and assumed store approval.

When periodic maintenance is requested, use the host's native recurring-task facility for explicitly selected repositories. Keep unchanged state quiet; notify meaningful changes, failures, login needs or completion. Retain project isolation and free-only policy. Do not install a second daemon or schedule arbitrary repositories just because they exist on disk.
