---
name: store-automation
description: Develop, inspect, repair and prepare Flutter mobile apps with project-owned Project Brain state, sequential implementation and independent review. Use for the user's app-factory/store-automation workflow in Codex or OpenCode.
---

# Store Automation

Work in the selected application's own directory and Git repository. This skill supplies reusable tools; the tool-development repository is never the application's task store. Existing projects stay where they are. New products normally live beside other projects (for this user, D:/repositories/<app>), not inside store-otomaston. Never move an existing project to adopt the skill.

## Project Brain dependency

Before work load the available `project-brain` skill and run its boot step **in the selected project**. On this host its canonical source is `C:/Users/rubicon/.skills-manager/skills/project-brain/SKILL.md`. If unavailable, report the missing dependency rather than inventing another Brain. For a project without Brain follow that skill's Genesis/adoption workflow; preserve existing plans and user files. A new bootstrap initializes only the Brain skeleton: its target remains DRAFT until the user's product goal is recorded and confirmed. Never copy template or factory tasks into an application.

All application tasks and checkpoints belong to that project's `.project-brain/`. Contracts go in its `contracts/`; local execution evidence goes in its `.factory/runs/` (add an ignore entry if absent). Each project resolves PB task IDs independently. Do not store project progress in this installed skill.

## Host and model selection

The current conversation assistant normally also supervises and reports to the user; do not add a second orchestration model for every task. If the user explicitly chooses another orchestrator, give it planning/routing responsibility and keep this assistant as the reporting interface. Use the current host's native tools: Codex can implement and delegate in Codex; OpenCode can use its supervisor/worker/reviewer. Do not require opening OpenCode from a Codex task. Work sequentially: one implementation task, machine verification, then fresh independent review before acceptance. Workers do not edit Brain or tool policies. If the host cannot provide an independent reviewer, report that gate as unverified; never label self-review independent.

On first use, ask which installed official subscription CLIs/free providers the user authorizes and whether they prefer automatic routing or selection per task. Record the answer in this project's Brain constraints, including any existing session authorization. Do not ask again unless authorization or access changes. Before that answer use the current authorized host for planning/read-only work; do not start external inference.

For current CLI inventory, least-capable routing and account prerequisites read [CLI routing](references/cli-routing.md) only when choosing an external model.

Select the **persona** from the task (implementation, design, security, review); select the **model** separately from approved and verified capabilities. Automatic routing is only among those approved routes. If none can meet a requirement, checkpoint and ask; do not silently use a paid API or another subscription. Confirm the official CLI's documented account/session mode and live access without reading tokens; do not assume a subscription includes API access or that all CLIs expose compatible flags. Claude/Gemini/Qwen/GLM integrations are not verified by this installation. Verify an explicitly approved CLI path before dispatch; do not invent adapters or claim vision support. Abbreviation/provider ambiguity must be resolved before account use.

The bundled wrapper currently supports two measured free OpenCode routes and official Codex ChatGPT snapshot review. Other native-host/CLI work is orchestrated by the skill after authorization, not by pretending those providers exist in the wrapper registry. Official Codex route is read-only source handoff, not implementation. A host-native reviewer uses that host's real logs plus machine evidence; the wrapper's `gate` specifically validates OpenCode native reviewer sessions and cannot certify another host's review.

## Shared tools (optional OpenCode route)

Resolve `<skill>` to the directory containing this SKILL.md. `<cli>` below means `python "<skill>/runtime/tool/factory.py"`. Always run it **from the selected project root**. Installed resources are separate from current working directory; no store-otomaston checkout is required. The runtime's capability registry is measured evidence, not a permanent guarantee of free availability.

- `<cli> open`: launch the three OpenCode roles in the current project. `/factory-start <idea>`, `/factory-resume`, `/factory-audit` are provided in that session. Project/global OpenCode config files are not rewritten.
- `<cli> brain boot`, `<cli> brain new . "task title"`: canonical local task state. Genesis uses the Project Brain skill directly.
- Copy `runtime/contracts/delegation-smoke.json` as a **format example**, replace the old PB ID/persona/scope/evidence with the actual project task, then `<cli> contract contracts/<task>.json`. Write scopes are project-relative app source paths.
- `<cli> run --provider <verified-route> --contract contracts/<task>.json --prompt-file contracts/<task>.txt --output .factory/runs/<unique>.json`: native OpenCode worker scope or official Codex read-only handoff. First-pass implementation and fresh review are separate sessions; supervisor runs the checks.
- `<cli> check --contract contracts/<task>.json --worker-session <real-id> --output .factory/runs/<unique-check>.json`: Flutter format/fatal analysis/tests and, when contracted, Android APK build. Do not use the factory-source test profile for app verification.
- `<cli> gate --contract contracts/<task>.json --evidence .factory/runs/<check>.json --review .factory/runs/<review>.json`: exact source/log/artifact/contract/native-review checks. Other hosts must honestly record their own reviewer provenance rather than fabricate an OpenCode session.
- `<cli> bootstrap D:/repositories/<new-app> --name "App" --package com.example.app --ads no --pro no`: new explicit destination only; existing paths refused. Uses local napp starter/core, strips inherited Brain, initializes new project Brain, runs analyze/tests/APK. Continue work from the new root; no central app registry. A failed generation leaves files for diagnosis, never overwrite-retry.

## Product and release decisions

Ask only unresolved app choices: purpose/platform/locales, monetization (offer entirely free), backend need, package and quality/device budget. Reuse the existing napp template/core when appropriate. For backend selection read `runtime/docs/services.md` and verify current official quotas/terms before selecting a provider. Read `runtime/docs/roadmap.md` for phase planning only. UI work needs real accessibility/device/screenshot evidence; source-only review cannot prove visual acceptance.

No paid AI APIs, token transfers, automatic billing or publication. Signing, account changes and production are separate app-specific authorization. For release preparation read `runtime/.opencode/skills/factory-release/SKILL.md`; existing `D:/AppPublishing/README.md` stays the publishing source of truth. Live receipt/store and iOS/Xcode limits stay in the affected project's Brain; never claim them passed from local Android evidence.
