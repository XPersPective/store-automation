---
name: app-factory
description: Sequential Flutter App Factory using validated contracts, existing napp template, one Project Brain and evidence gates
---

Use `docs/architecture.md` for decision rationale and `docs/roadmap.md` only when
planning a phase. Do not load all references into every task.

1. Boot existing Brain with `python tool/factory.py brain boot`; verify real Git diff.
2. Extract app spec: purpose/platform/locales/package/quality/device budget. Always
   offer completely free mode. Production monetization requires user decision.
3. Pick local napp starter; record source commit and kit ref. Reuse its generator.
4. Select backend only for actual capabilities. `docs/services.md` provides current
   official source links; verify free quota/terms/region on the selection date and
   save ADR. No automatic provider migration or paid escalation.
5. PB new creates the canonical task. Write complete JSON contract using
   `contracts/delegation-smoke.json` as the full format example. Run `contract` check.
6. For write-enabled work call `python tool/factory.py run` with validated contract,
   provider, prompt-file and new output path; the wrapper applies exact edit scope.
   For read-only work direct native task is allowed. Dispatch one factory-worker,
   then
   deterministic test/build evidence; never consider worker text completion.
7. Dispatch fresh factory-reviewer after machine checks. Missing screenshots,
   store verifier, account or Xcode is BLOCKED. Use `gate` to reject stale evidence.
8. Supervisor accepts only verified work; Brain reconcile/validate/checkpoint.
9. On quota/timeout/crash: checkpoint, boot, verify source/tests, switch to another
   allowed free model or official Codex CLI, continue first unchecked acceptance.
10. Release preparation loads factory-release. Production is a separate approval.

Minimum UI contract: light/dark, phone/tablet/landscape, 48dp targets, text scale
1.3/2, 4.5:1 contrast, loading/empty/error, screen-reader and actual screenshots.
Code contract: fatal analysis, meaningful tests, no scope creep, source-linked build.
Every result names failure class and next action. Never fabricate evidence.
