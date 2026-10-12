# Architecture critique and release review

Run after product intake and real-flow audit, before major implementation. Repeat when evidence changes the architecture, trust boundary or delivery plan. Reuse [task personas](task-personas.md); review is read-only, bounded and independent. Catalogue/account preflight and announced model/effort selection are mandatory. Strong risk-sufficient review covers architecture/security/persistence; a lightweight reviewer may inspect a fully specified low-risk slice.

## Evidence and decisions

Give the reviewer the confirmed outcome/constraints, exact source entry points and affected callers, architecture/data-flow map, dependency/platform facts, proposed diff/decision and actual check results. Include relevant failed cases and known external limits. Exclude credentials, hidden reasoning, unrelated histories and entire repositories. Declare context/output budget and requested maximum findings; split domains when the evidence does not fit rather than silently truncate critical context. Budgets cannot lower the risk floor.

The director records initial findings and a concise ADR: problem/user outcome, observed evidence and limits, existing/simple alternatives, selected smallest solution, why it meets acceptance, tradeoffs/known ceiling and verification/rollback. Use a `ponytail:` source comment only for a deliberate real simplification with a known ceiling and upgrade path. An ADR cannot establish a runtime claim without verification.

Prefer no new component, reuse, stdlib/native features and installed dependencies in that order. Compare a proposed architecture with at least one viable simpler alternative when one exists. Reject speculative abstraction or infrastructure; also reject a small diff that hides cross-caller failure, security weakness or data loss. Identify assumptions needing measurement on real platforms.

## Reusable reviewer prompt

Adapt the following into a complete task persona/contract; replace every bracket with actual task evidence before dispatch:

```text
Role: Independent [discipline] architecture/release reviewer for [task/project].
Outcome: [confirmed user result and observable acceptance].
Scope: Read only [exact source/diff/decision paths and caller entry points].
Constraints: [platforms, data/security, budget, exclusions, license/release scope].
Evidence: [actual commands/results, source/build/device/artifact references].
Unknowns: [explicit gaps; do not infer successful access or verification].
Route: [provider/model/effort, reason and required quality floor].
Budget: [context characters/output tokens]; max [N] findings; prioritize blockers.

Trace the real caller/data flow. Critique correctness, failure recovery, security,
privacy, accessibility, platform behavior, maintainability and operating cost only
where relevant to this outcome. Compare the proposal with the smallest viable
alternative using existing/native components. Explain concrete tradeoffs and a
known ceiling; do not add speculative features. Do not edit files, call paid APIs,
read credentials, publish or claim runtime/visual proof from source alone.

Return each actionable finding with:
- severity: BLOCKER, MAJOR or MINOR; source path/symbol and affected caller;
- evidence and a concrete triggering input/state/failure scenario;
- user/operational consequence and which acceptance criterion it violates;
- the smallest sufficient fix and a runnable regression/observable verification;
- confidence and any missing evidence needed to confirm the finding.
Mark unsupported concerns as questions, not established defects.
Then report: alternative architecture and tradeoffs; release blockers; external
verification gaps; acceptance status PASS/BLOCKED/UNVERIFIED; next action.
Return the contract's required task/role/provider/model/effort/state/changed_files/
evidence/usage/blockers/next_action fields. Empty findings means only that no
supported defect was found in this scope; it never proves a perfect system.
```

Severity follows consequence: BLOCKER prevents safe release or required acceptance (security/data loss/broken core flow/invalid distribution); MAJOR materially impairs a supported journey; MINOR has limited impact. Do not inflate preferences into blockers. The director validates each finding against source/evidence; contradictory reports require a focused reproduction or bounded independent clarification, not majority voting.

## Correction and fresh review loop

1. Triage substantiated findings into exact acceptance/checks. Keep unrelated improvements out of scope; checkpoint real external dependencies.
2. Dispatch the smallest bounded fix with a sufficient model; inspect its diff and personally run affected machine checks. Update the ADR only when evidence changes the decision.
3. Request fresh independent review of the corrected source, checks and prior findings. The implementation session cannot certify itself. Recheck integrated behavior when a fix affects a shared caller/trust boundary.
4. Continue until no release-blocking finding remains and required machine/device/release evidence is present. Report residual accepted limitations explicitly; absence of findings is not a perfection claim.

Do not loop indefinitely. A repeated failure without new evidence ends that approach: save partial work, exact unchecked criterion, attempted checks and the next concrete diagnostic/action. Missing account/device/reviewer/permissions, depleted or unknown quota and unverified platform controls leave the relevant gate BLOCKED or UNVERIFIED. Preserve a safe handoff and continue independent authorized tasks; never spend reserve on identical retries, weaken acceptance, self-review or silently publish around a blocker.

Present-runtime boundary: existing contract/source/machine-evidence validators can check their documented fields. Architectural soundness, real service authorization, accessibility, device behavior, asset licensing and remote publication require the appropriate fresh specialist/tool/human evidence. A PASS from one validator cannot certify those separate gates.
