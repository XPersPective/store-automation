# Subscription CLI routing

Verified locally 2026-10-11; recheck before dispatch. CLI presence/auth/listing/inference are separate evidence levels. A subscription authorization does not verify entitlement, remaining quota or free overage behavior. Keep personal account names/tokens out of task logs.

## Routing rule

| Task | First choice | Upgrade trigger |
|---|---|---|
| Format, hash, search, fixed validation/build | Existing script/stdlib/tool; no inference | Human judgment actually needed |
| Small bounded edit or summary | Approved lightweight model, low effort, minimal source slice | Concrete failed acceptance after correcting context |
| Normal feature/debugging | Approved standard coding model, task persona | Cross-module ambiguity or unresolved failure |
| Architecture/security/difficult diagnosis | Strong approved model with relevant persona | Use only for the complex slice |
| Independent review | Fresh session capable of checking the task risk | Never self-certify implementation or unavailable visual proof |

Use the existing assistant for quick local actions; no extra orchestrator hop. Budget the context to contract + affected callers, not entire histories. Before upgrading record the failed acceptance and reason in the project task. On quota/auth/timeouts checkpoint and check the real diff; do not restart partial writes blindly. Do not escalate every failure to a more expensive model. Respect project preferences; an explicit per-task model request wins. Current host model cannot necessarily be changed mid-turn: reduce unnecessary calls or dispatch an approved lighter CLI instead of pretending it changed.

## Installed routes and limits

Fresh discovery uses official help/auth/models/quota/overage, never credential files or token bridges. `providers --scan --output .factory/runs/inventory.json` reads Antigravity models, zero-inference `-p /usage` / `-p /credits` and public Claude/Codex auth. `route --contract <contract> --inventory <inventory> --complexity SIMPLE|STANDARD|COMPLEX|SPECIALIZED` requires inventory <=5 minutes old and returns `CANDIDATES_REQUIRE_GATES`, not access proof. Lightweight low effort fits simple tasks; standard tasks need sufficient medium/high, architecture/security/persistence strong high, possibly stronger than the coordinator. Never trade quality for quota.

Qwen is excluded. User reports Claude/Opus lacks tokens: exclude Claude until fresh specific-model access evidence and user availability both exist. Shared Antigravity Claude/GPT quota does not prove entitlement; older route notes below are historical evidence, not dispatch authorization. Unknown quota/usage stays null; fractions are not remaining token counts. Count shared buckets once. Track coordinator, all children and retries via repeated `usage --record <attempt> --expected <expected-attempts.json>`; totals are incomplete without full manifest coverage. At <=10% remaining in any shared window, start no new bucket job; checkpoint actual partial edits, select an equally qualified approved route or await reset. Denied tools or empty/timed-out responses are UNVERIFIED: stop that approach promptly, without repeated expensive reasoning/permission requests or blind mutator replay. An unanswered optional preference uses automatic approved routing; login stays user-owned with a concrete official command.

Antigravity measured 2026-10-11 Gemini remaining ~81% five-hour/~96% weekly, shared Claude/GPT 100%, `/credits` 0. These dated values do not prove model access. Source-read denial and subsequent empty timeout leave execution UNVERIFIED; counters stay null unless authoritative. Current official flags include `--model`, `--effort`, `--conversation`, `--prompt-interactive`, duration-valued `--print-timeout` (e.g. `30s`, not bare `120`). Fresh quota and specific-model tool-free access precede work; generic Gemini auth/extra-usage remains unknown. Declared handoff/output budgets do not cap system overhead or prove savings.

- Codex 0.153.4: official CLI reports ChatGPT login. Bundled wrapper supports read-only source-snapshot handoff; this does not prove every account/model is available. Keep one active official account context. User switches accounts through official login; no token copying or automatic account rotation.
- Claude Code 2.1.272: official public auth reports logged in; subscription tier/overage not measured. Currently excluded as above. Before any later inference verify subscription-only session and extra-usage policy. API-key environment variables must not silently override subscription mode. Use current CLI help for flags.
- Gemini CLI 0.63.0: installed from official `@google/gemini-cli`; isolated headless probe returned auth-required, no inference. User must run `gemini` and select **Login with Google**, using the subscribed account. Do not solve this by adding a Gemini API key or enabling Vertex billing. Current help supports `--prompt`, `--model`, `--approval-mode plan`, JSON output. Plan mode may revert to default in an untrusted folder: verify actual effective mode before any delegated work.
- Antigravity CLI 1.1.9 (`agy`): official installed CLI returned a live model list including flash/standard/strong choices. A low-effort Flash inference probe subsequently timed out with empty output; live inference remains UNVERIFIED and token counters unknown. Listing is not inference proof or quota proof. Preserve normal permissions; `--dangerously-skip-permissions` is not an automation prerequisite. Prefer observed low-effort Flash choice for an eligible trivial task, not Opus/Pro by default.
- Qwen Code 0.21.3: installed but excluded by current user availability. No inference or paid/API fallback; presence and historical OAuth documentation do not authorize access.
- MiniMax Code: old `minimax` desktop shim fails with MODULE_NOT_FOUND. Preserved it and installed official `@minimax-ai/code` as separate `mcode` 0.6.8. Version/help verified; account/inference unverified. Official login for a Global account: `mcode login --region global`, then `/status` in the official TUI. Default user data may be shared with older installs; do not move/delete it or silently change providers. `mcode exec` supports cwd/model/effort/output/max-steps/timeout; permissions and managed subscription route must be verified before task execution.
- GLM/Z.ai: no verified standalone official CLI route found here. Official ZCode supports account-based Coding Plan login; that desktop route is not automatically a headless CLI. Do not install an unofficial client or borrow another app's tokens. A Coding Plan key endpoint and general metered API endpoint are distinct; configuring either requires verifying the authorized plan route without reading credentials. Keep blocked until a supported official path is selected.
- OpenCode: bundled wrapper keeps its measured free allowlist. Free availability is temporary; revalidate on errors. This route is optional; other hosts are not required to funnel through OpenCode.

## Evidence and sources

Provider tools are distinct adapters with different authentication, permissions and result formats; do not manufacture a common CLI flag set. Use a tiny non-mutating access probe in an isolated directory only after the route is authorized and its billing mode is established. Record actual provider/model/role/source/check outcomes in the application's evidence. Treat unverified login or tool isolation as blocked, not successful.

Official sources checked 2026-10-11:
- [Gemini CLI installation](https://github.com/google-gemini/gemini-cli) and [Google subscription login](https://google-gemini.github.io/gemini-cli/docs/get-started/authentication.html).
- [Claude subscription use](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) and [CLI/auth reference](https://code.claude.com/docs/en/cli-reference).
- [Qwen authentication quickstart](https://github.com/QwenLM/qwen-code/blob/main/docs/users/quickstart.md).
- [MiniMax official CLI](https://github.com/MiniMax-AI/minimax-code) and [installation/accounts](https://github.com/MiniMax-AI/minimax-code/blob/main/docs/installation.md).
- [Antigravity CLI](https://www.antigravity.google/docs/cli/reference/).
- [Z.ai account-based model connection](https://zcode.z.ai/en/docs/configuration).
