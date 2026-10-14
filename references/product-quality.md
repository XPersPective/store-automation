# Product quality and early feedback

Use this for product, flow and interface work. Do not open every product phase for a small technical
task. Existing product decisions and visual language are the starting point; do not replace them for a
template unless the user's goal changes. These lists are a floor, not a ceiling; the premium bar below is
what review holds every output to.

## Premium bar

"Works" is not done. Each rule becomes concrete Acceptance in the task that touches it; a reviewer reports
a miss as QUALITY ([plan](plan.md) §8), which blocks until fixed or the user accepts it.

- **Design foundation first.** A product with UI gets, in its first UI milestone, a foundation task: color,
  type, spacing, radius, elevation and motion tokens; 2–3 rendered visual directions with a screenshot
  each; the choice in an ADR. Later UI uses only those tokens (`[visual]` item: "no value outside the
  tokens"). An existing design system is the foundation; extend it, never fork it.
- **Visual review rubric.** `[visual]` evidence shows the named narrow and wide viewports, and the reviewer
  answers yes to each: the primary action is clear at a glance; something is specific to this product
  (color, iconography, language), not a template; empty, loading, error, success, offline and permission
  states each have their own render where they apply; long text and the user's locale do not break; dark
  mode where the platform has it; touch targets ≥44 px (48 dp on Android).
- **Errors speak the user's language.** Every visible error says what happened and what to do, in the
  user's language; never a raw exception or transport message (`Failed to fetch`, stack traces). Input is
  kept on error and retry works. Acceptance example: `[interaction] server stopped → submit shows a
  <language> message, input kept, retry succeeds after restart`.
- **No duplicate work.** Repeated taps, lost responses and retries create one record:
  `[interaction] three fast taps on Save → one record (read back from the API)` and
  `[machine] same id with different content → 409 (test name)`.
- **API contract.** Per endpoint: path, method, request/response shape, error body
  `{"error": {"code", "message"}}`, idempotency key, limits and pagination, timeout. An unexpected exception
  returns a JSON 500 and a log line without secrets or personal data; validation and authorization happen
  at the boundary; versioning is decided once in an ADR.
- **Performance budget.** List endpoints are bounded (pagination) with a constant number of queries (no
  N+1, proven by a test); the task names its latency and payload budget for the real path at realistic
  size (web default: first load ≤200 KB JS+CSS, interactive <1 s locally) as a `[machine]` item, or says
  why none applies.
- **Security checklist** (HIGH tasks; the reviewer ticks each in its review): bind address (127.0.0.1
  unless serving others), request size limits, output escaping (XSS), path traversal, CSRF/origin checks
  for state-changing requests, authorization per actor and resource, no secret or personal data in logs,
  commits or plan files.
- **Observability.** Failures leave a structured log line with a correlation id; a background or offline
  queue shows its state to the user.

## Shape of the work

| Work | Smallest useful delivery | Grows when |
|---|---|---|
| Small defect | Reproduction + shared root-cause fix + relevant check | Security, data loss, a shared flow or platform impact |
| Flow feature | Affected journey + early demo + real working slice | Several roles, services, migrations or a new product decision |
| New product | Goal and scope + risk probe + first real task | The core experience is accepted, then the remaining flows |
| Adoption | Source/test/design/release map + verified baseline | Contradictions in an old plan; change limited by its reason |
| Design feedback | Concrete difference + affected components + new representative output | A wrong need or new scope → the related product decision |

## Quality per phase

| Phase / expertise | Input → output | Measure and verification | User decision / loop back |
|---|---|---|---|
| Product owner | Need, existing work → short goal, user, journey, out of scope | Observable success; a sample task for the main need | Misunderstanding or conflict → fix the goal |
| Research / domain | The unknown that changes a decision → an evidenced answer | Date/source, feasibility, limits of the unknown | A result that changes cost, data or product choice |
| UX designer | Main task and states → flow/prototype | The user understands the start, next step and result and completes the task; observed friction recorded | Show the usage logic early; back to the flow |
| Visual / UI designer | Flow and existing language → representative screen/component | Real render; consistent type, spacing, alignment, hierarchy; no overflow | Show the visual direction before spreading it to every screen |
| Architect / engineer | Flow, platform, data → ownership and boundaries | A narrow probe of the riskiest assumption; comparison with existing/native options | Cost, data or permission scope changes → decision |
| Frontend | Screen and state → working interaction | Valid/invalid input, keyboard/focus, waiting/error/empty/success, back/cancel | Fix shared components and sibling screens together |
| Backend, when needed | Data/permission contract → real behaviour | Isolation, input validation, timeout/retry, migration/rollback, data-loss checks | Contract changes → align both sides; no backend if not needed |
| Integration owner | Client + real storage/service → the whole journey | A UI action produces and reads back the right persistent result; errors and recovery work | Show the first working journey before broad scope |
| Independent verification | Final source/package → bounded acceptance | Relevant tests, device interaction, visual, accessibility, security evidence | Return to the phase of the failing criterion |
| Material / content | Final product + target → store text and images | Real features, correct language, licenses, current formats, candidate match | Show the presentation; regenerate stale material |
| Release owner | Candidate + full authority → remote result | Account/app/channel/version readback; real availability separately | Back on rejection or missing info; never repeat an uncertain upload |

This table does not require separate documents. Acceptance is written once in the task; tests and
observations refer to it. When research no longer changes a decision, implement. If a critical
uncertainty remains, say what the next experiment resolves; do not repeat the same analysis.

## Concrete UI and interaction checks

- At the selected small/large viewports, long text/locale and required orientations: no clipping, overlap
  or unreachable primary action. Breakpoints and target devices are named in the task; there is no
  universal device matrix.
- The task stays completable with enlarged text. For web targets verify WCAG 2.2 AA: normal text contrast
  4.5:1, large text 3:1, 200% resize, with their exceptions; this alone is not an accessibility
  certification. Choose native criteria from the platform guidelines.
- Typography, spacing, radius and color come from shared tokens; exceptions have a reason. Check on screen
  that the visual hierarchy makes the task clear.
- Dialogs: clear purpose; understandable fields and validation; primary and cancel actions distinct; narrow
  screens and the keyboard do not hide content; focus correct on open and close; input kept on error;
  repeated triggering while pending is handled.
- Empty, loading, error and success states are seen in the real flow. Permission denial, back, retry,
  cancel and undo (when present) are consistent. Advanced options do not complicate the basic task.
- Screenshot review and interaction checks are separate evidence. Screen reader, keyboard, reduced motion
  and touch targets are tried per target platform. Reading source is not visual acceptance.

Official references: [WCAG resize text](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html),
[contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Re-verify version- and
platform-specific claims in the app.

## Applying feedback

Visual preference → design token/component; usability → interaction/copy; flow → transitions/states;
misunderstood need → goal; defect → shared root cause; new scope → separate work with cost/data impact.
Record feedback briefly: the concrete problem said, the decision that changes, the affected
source/test/material, the evidence needed again. No separate feedback database. Silence is not approval.
Work on already-authorized details does not stop; work outside a blocked critical choice continues.

## Frontend and backend accepted together

Naming, data ownership, state transitions, validation and error shape are shared. "Saved" appears only
after the required persistence happened. Double clicks, lost responses or retries must not duplicate work;
choose idempotency or conflict behaviour for the product's need. Offline/sync, log privacy,
delete/export and migration enter the contract only when relevant. A demo that passes against a mock
service is not presented as real service acceptance.
