# CLI team architecture review evidence — 2026-10-12

Scope: combined user request; latest instruction asks architecture first with repeated critique/revision. Phone setup secondary. Design approval is separate from implemented native runtime or app acceptance.

## Actual discovery

Bounded PATH/known executable bins found13 CLI entrypoints: codex, claude, agy, opencode, mimo, mcode, minimax, gemini, kimi, qwen, hermes, lms, omniroute. Manager metadata:54 client records/41 installed hints; these are not runnable CLI proof. Known roots/public executable metadata only, no credential contents. Completeness outside those discovery surfaces is not claimed.

- MiMo `--pure models`:7 actual native IDs, including MiMo2.5/2.6 variants.
- MCode ACP initialize/session-new in empty temp workspace (no prompt): configOptions exposes M3.1-Flash-Preview, M3, M2.7/highspeed and thinking variants; native thought levels default/low/medium/high/xhigh/max.
- Kimi ACP configOptions: K2.8 Preview, K2.7 Code Highspeed, K3-256k, K3; thought levels low/high/max and native plan modes. Initial parser expecting only models.availableModels found no entries; diagnostic public configOptions parsing recovered the actual catalog. Account/quota remains unverified.
- AGY native models: actual Flash/Pro and other IDs; metadata is not task access.
- Old minimax.cmd points to an absent daemon/cli.js; MCode is a separate working npm CLI. No launcher deletion/replacement.
- LM Studio lms exists; ls failed because daemon is unavailable, no local model eligibility claimed.
- OmniRoute is already installed. Only public help read; no setup/config/account changes or proxy invocation. Native credentials are never forwarded.

Ignored local evidence: .factory/runs/system-cli-scan-20261012.json, intake-20261012-new.json, acp-metadata-20261012.json, acp-options-20261012.json. These include private local installation paths and are not shipped.

## Native independent critique loop

| Attempt | Actual native model/effort | Reported input/output | Result |
|---|---|---|---|
| Bounded source mapping | gpt-5.6-luna / low |36105 /453| Typed task report COMPLETED; read-only snapshots, no implementation |
| Architecture v1 critic | gpt-5.6-sol / high |20540 /2502| Useful ranked source critique; typed report gate UNVERIFIED because evidence contained objects instead of strings |
| Architecture v2 fresh critic | gpt-6-astra / high |22836 /2759| Typed COMPLETED; four concrete target-design blockers |
| Architecture v3 fresh final critic | gpt-5.6-sol / high |22882 /3568| Typed COMPLETED, blockers=[]; design gates closed, runtime gates explicitly future |
| Bounded diff source reviewer | gpt-5.6-terra / medium |22540 /1260| Typed COMPLETED, blockers=[]; parent matched exact diff and reran110tests |

Every attempt used official forced ChatGPT CLI, selected model/effort, native quota refresh, source-only handoff and no paid API fallback. None was a host-native collaboration agent. Source mapping's broad input is a measured inefficiency; serialized context-range guard added rather than claiming lightweight model guarantees low token use. Native output budgets were soft instructions: reported output exceeded them in strong reviews. Hidden/system overhead and reasoning inclusion are not independently known; no hard output-cap or savings percentage claimed.

V1 findings: fail-closed billing, bounded discovery completeness, one authority across native/CLI, suitability rubric, crash/generation ownership, quota/resume limits and GUI/artifact controls. Supervisor checked source critique manually and revised v2; malformed report was never accepted as a valid runtime task report. V2 findings: separate API authorities and env isolation; durable spawn/identity handshake; CALIBRATING bootstrap; atomic shared-bucket admission and soft reserve. V3 incorporated all four and final critic found no remaining design contradiction.

V3 reviewed source SHA256: 20ff4c0dd010069e71292a7bafd87f6f2bbdda8fbdb293971e9466f2e1f62eae. Parent independently matched that full-file hash immediately before finalizing. After review only the document's status label became HEDEF TASARIM plus a runtime-pending disclaimer; no design behavior changed. Saved immutable v2/v3 inputs and raw reports stay in ignored .factory/runs. The final critic never claims it ran the implementation or observed UI.

Native account window evidence before/after: remaining five-hour88% ->70%, weekly53% ->50% (sampled before the last bounded-source review). These are shared-account observations, not attribution to this task. Coordinator attempt-specific token totals and other-account/child coverage unknown; table is only the five measured subprocess attempts, not complete cost/account usage. No currency price inferred from subscription counters.

## Concrete decisions and follow-up

Two skills retained: one project Brain owns plan/acceptance; Store Automation owns dispatch/control, no second supervisor by default. No merged skill or speculative third library now. OmniRoute optional metadata candidate, native CLI path default. Mandatory managed assignment/acceptance; lowest sufficient risk-aware model; native permission/billing/quota gates; deterministic reset observers; contained generation-bound handoff; actual intervention and artifact evidence.

PB027 finishes already-started input/metadata correction. PB031 authority/enrollment/report gates; PB032 ACP/native metadata+account controls; PB033 quota/admission/reset; PB034 safe launch/handoff/director takeover; PB035 Codex live transport; PB036 second native transport; PB028 rendered console/artifacts; PB029 verified installed distribution/existing remote integration. Existing provider/account/Codex-binding gates remain explicit; no unavailable route is enabled by this design.

Configured stdlib suite:110 tests PASS before final documented architecture label; py_compile PASS. Regression source review recorded separately under PB027. Existing unknown takeover logs, app repositories, accounts and published2.2.0 installations preserved. No screenshot/emulator/native GUI acceptance or remote phone pairing is claimed.
