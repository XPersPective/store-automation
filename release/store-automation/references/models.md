# User model pool and selection

The registry is user-owned `~/.store-automation/models.json`, outside project plans and installed skills.
Global `--models-file <absolute path>` selects a different registry. It contains no credentials.
Python stays offline. The agent uses existing native catalogs/quota tools and web research, then imports
public evidence. Never run inference just to discover a model or read credential/config contents.

## Session and refresh procedure

1. `SA models list`. Missing file is an empty advisory pool; an empty/corrupt existing file is an error,
   never a reset. `boot` adds bounded model counts and due research without hiding its project STATE.
2. Discover only hosts the user uses, through their existing supported tools. A Skills Manager deployment
   is not model entitlement. Catalog, access permission, availability and quota are separate observations.
   Save exact version and effort profiles; a mutable `latest` alias needs its current target resolved.
3. Research only `research_due`. A fresh complete profile needs no search. A missing role is not proof
   that its model is weak. Start with relevant coding evidence, then reasoning evidence for plan/review.
   Bound a session to three targeted searches; prioritize the requested role/current model. If a source
   fails, record `research.error` and `retry_after` (normally tomorrow), use a qualified backup or leave
   UNKNOWN. Do not repeat unchanged failed searches or make a new API key to fetch data.
4. Benchmark snapshots/results expire after 30 days. `observed_at` is the snapshot's as-of date, not the
   original model release or evaluation date; do not renew it just because an old web page still opens.
   Recheck cohort, benchmark version, model version, harness and effort. On methodology change create a
   new benchmark key, replace affected results, keep incomparable scores separate. Checking one missing
   model must not rewrite unrelated models. A source not available under existing access stays unknown.
5. Access/catalog/price observations expire after 24 hours; refresh before using a free API. Pool quota
   expires after five minutes and must be refreshed immediately before delegation. All windows must have
   at least 10% left and an unexpired reset time. `windows: []` means unknown, never unlimited. Providers
   that expose no reliable quota remain blocked for automatic selection; the agent explains the limit.
6. Import a project-relative public patch with `SA models merge --file model-update.json --revision <hash>`.
   Use the revision from list. Merge is atomic and locks writers; a changed revision refuses the update.
   Top-level benchmark/pool/model maps merge by id; each supplied entry replaces that whole entry.
   Include its retained fields when updating a model or pool. This does not remove unrelated entries.
7. `SA models select --role plan --tier H [--kind subscription|free_api|paid_api] [--context 200000]
   [--tool shell] [--task-class bugfix] [--metric tokens|usd]`. Show the recommendation, alternatives,
   exclusions and dates when the user asks for the pool. It never switches models or calls a provider.

## Sources and classification

Primary coding source: [SWE-bench official results](https://www.swebench.com/) with the same harness;
cross-language tasks may use its Multilingual view. Alternate coding source:
[Terminal-Bench](https://www.tbench.ai/), with its current version and agent configuration recorded.
General reasoning and consumption priors: [Artificial Analysis](https://artificialanalysis.ai/methodology).
These are source families, not pinned benchmark versions. Check which version is current during refresh.
Provider model cards are a fallback discovery source; manufacturer-only results are provisional and never
establish a benchmark tier (`independent: false`). Search snippets alone do not establish scores.

Every benchmark defines a transparent, reviewable external reference and its own H/M thresholds with a
rationale. They are policy estimates, not benchmark-author certifications. Compare scores only within
that benchmark/version/harness/effort. Never normalize across unrelated tests or compute a blended score.
The user's pool size cannot change thresholds. A possible initial policy is 90%/70% of a documented
strong external reference, with its limits explained; use no universal hardcoded score or model-name rule.
All values must be higher-is-better on the same nonnegative scale; transform other metrics explicitly
before importing and explain the transformation in `rationale`.

`implement` needs independent current coding evidence. `plan` and `review` additionally need reasoning
evidence; the lowest tier among qualifying evidence is used. Evidence measured at a different effort
does not transfer. Missing/stale evidence yields UNKNOWN, not L. Planning and review ratings remain
estimates: public coding/general tests do not directly certify product judgment or review diligence.
Local acceptance and independent review still determine whether work is done.

An explicit user override per role may set H/M/L with a reason and date; it expires in 30 days and is
displayed as `user_override`. Only add one after the user actually requests it. Registry provenance and
identity remain declared; a same-OS-user forger can edit this file. URLs and `independent` flags record
the agent's checked evidence, not authenticated third-party attestations.

## Cost and authority

First filter quality, permission, availability, fresh quota, tools, context and free price. Both access
and pool must be allowed; paid API pools are false unless the user explicitly authorizes them. Do not
silently enable extra subscription usage, switch billing or fall back to a paid endpoint.
Separate pools represent shared accounts: all models using one account reference that same pool.
Quota percentages from different providers are not interchangeable and are not per-task token counts.
For request-based free quotas, remaining is the observed fraction of the real request allowance.

Rank consumption only from complete observations of the requested task class, at least three samples,
within 30 days. `tokens_per_accepted` and `usd_per_accepted` include failures, retries, checks and rework
until acceptance; they require authoritative counters and full coverage. Keep partial data `complete:
false`, missing values null. Benchmark task costs are priors and must not be entered as local accepted
work measurements. Input/output prices alone cannot estimate subscription consumption. Do not add
reasoning tokens twice when they are already included in the provider's output counter.

Candidates sort by known comparable consumption, then stable ids. When consumption is unknown the
first candidate is only a deterministic eligible suggestion, not a proven cheapest model. Use `--kind`
to express an access preference instead of inventing a money/quota conversion. Context/tool requirements
must be passed from the task; without them the CLI cannot infer capability needs from prose.

Default `enforce: false` preserves existing projects and adds advisory selection. An explicit registry
patch `{"enforce": true}` enables shared runtime guards on start/review/accept: implementers meet task
Tier; Tier H uses the plan role; risky READY approvers and independent reviewers meet H. Accept rechecks
the latest reviewer's qualification. Aliases cannot turn an implementer into an independent reviewer.
Unknown/stale evidence blocks that role; no quiet downgrade. Disabling enforcement requires an explicit
user choice. The registry does not evaluate the text of an approval or authenticate the running model.

## Schema 1 (illustrative values, never import as real evidence)

`SA models list` returns a compact authorized pool, derived assessments, research queues and a revision.
`SA models list --details` includes all raw maps (also unauthorized catalog entries) for editing. A merge patch can
contain any subset of `benchmarks`, `pools`, `models`, `enforce`; unknown fields are rejected. The stored
document also has `schema: 1`. A new model can have empty results/accesses while research is pending.

```json
{
  "benchmarks": {
    "coding-v1-high": {
      "name": "Example coding benchmark", "version": "1", "harness": "same-agent",
      "effort": "high", "dimension": "coding", "source": "https://example.org/results",
      "checked_at": "2026-10-14T08:00:00Z", "observed_at": "2026-10-14T08:00:00Z",
      "reference_model": "external-strong-model-high", "reference_score": 100,
      "h_min": 90, "m_min": 70, "rationale": "Illustrative policy only", "independent": true
    }
  },
  "pools": {
    "account-a": {
      "kind": "subscription", "allowed": true, "checked_at": "2026-10-14T08:00:00Z",
      "source": "native quota tool", "windows": [
        {"remaining": 50, "resets_at": "2026-10-14T13:00:00Z"}
      ]
    }
  },
  "models": {
    "example-model@high": {
      "effort": "high", "aliases": ["example-high"],
      "results": {"coding-v1-high": {
        "score": 95, "source": "https://example.org/model-result", "checked_at": "2026-10-14T08:00:00Z"
      }},
      "accesses": [{
        "id": "host-example-high", "pool": "account-a", "host": "existing-host", "effort": "high",
        "allowed": true, "available": true, "checked_at": "2026-10-14T08:00:00Z",
        "source": "native model catalog", "context": null, "tools": ["shell"],
        "input_price": null, "output_price": null
      }]
    }
  }
}
```

Optional model `overrides`: `{"plan":{"tier":"H","reason":"user's decision","checked_at":"..."}}`.
Optional model `research`: `{"error":"source unavailable","retry_after":"..."}`.
Optional model `usage_estimate`: `{"workload":"AA-index-version","output_tokens_per_task":13000,
"usd_per_task":0.32,"source":"https://example.org/results","checked_at":"..."}`. These benchmark
priors appear separately in selection output and never rank local accepted-work cost. They are dated,
not quota predictions. Profiles whose accesses are all unauthorized are listed but not researched
automatically; enable an access only when the user authorizes it.
Optional access `metrics`: `{"task_class":"bugfix","samples":3,"complete":true,"checked_at":"...",
"source":"native full counters","tokens_per_accepted":2000,"usd_per_accepted":null}`.
All timestamps are timezone-aware ISO 8601. Observation/check timestamps cannot be future; reset/retry
times may be. No duplicate aliases/JSON keys, NaN, negative numbers, linked paths or credential URLs.
The file/patch ceiling is 4 MB; each top-level map has at most 2000 entries. Keep this user-specific
registry out of release packages, backups sent to others and project git history.
