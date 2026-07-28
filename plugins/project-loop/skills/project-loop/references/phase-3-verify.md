# Phase 3 — Verify

Roles: **Tester**, then **Judge**. Output: `/loop-project/3-verify/`. Exit: gate **G3**, the only exit
the loop has.

This is the phase that makes the other three worth doing. It runs in two passes with a hard wall
between them: the Tester finds and reproduces, the Judge decides. Neither fixes anything. The
moment a verifier starts fixing, it has acquired an interest in the outcome and its verdict stops
being worth reading.

---

## 3.1 Tester pass → `3-verify/qa/QA-###.md`

Read-set: the task card, the REPORT, `1-spec/qa-strategy.md`, and the relevant acceptance rows.
The Tester deliberately does **not** read the Worker's reasoning beyond the REPORT — the point is
to check the artifact, not to be talked through it.

**Run things. Do not read code and imagine outcomes.** The Tester's authority comes entirely from
having executed something. Start with the commands in `qa-strategy.md`, verbatim.

Then attack, in roughly this order of yield:

1. **Acceptance criteria, directly.** For each `AC-###` this task claims to close, execute the
   named proof independently. A test the Worker says passes is not evidence until it passes for
   someone else.
2. **The unwanted-behaviour requirements** from the PRD. Expired tokens, duplicate submissions,
   empty inputs, oversized inputs, wrong types, missing fields, concurrent writes, dropped
   connections mid-request. This is where most real defects live, because it is where Workers are
   least motivated to look.
3. **Boundaries.** Zero, one, many. Empty string, maximum length, off-by-one on pagination.
   Unicode, right-to-left text, emoji in name fields.
4. **Authorisation, per resource.** Not "does a logged-out user get blocked" but "can user A read
   user B's record by changing an id in the URL." This single check finds more real vulnerabilities
   than any other, and passes silently when nobody runs it.
5. **The security contract's blocking rules,** each one, with the check it declares.
6. **The craft contract.** Was anything rebuilt that already existed? Does the code read like the
   rest of the codebase, or like a different author? Check `conventions.md` and confirm the new
   code follows it and that new reusables were registered.
7. **The design contract,** if UI: every required state rendered, keyboard-only traversal, visible
   focus, contrast measured not eyeballed, behaviour at the narrowest supported width, and with
   reduced motion enabled.
8. **Every other enabled contract, by the check the rule declares.** The UX contract's numeric bars —
   count the steps and the required fields, do not estimate them. The content contract's string table
   and character ceilings. The SEO contract's blocking rules. The AI-readiness contract's blocking
   rules, including whether `robots.txt` matches the recorded crawler decision. You grade against the
   stated check, never against your own view of what good would look like.
9. **Regression.** Full suite. Anything that was green before must still be green.

When the Adversary is enabled it owns step 5 and reports separately. When the UI Critic is enabled it
owns the judgement half of step 7 — you still verify the contract's stated rules mechanically, and it
judges whether the result looks decided. Run what is yours and leave theirs alone; two roles covering
the same ground produce two half-passes.

**Every finding must be reproducible.** The bar is: someone else, on a clean checkout, following
your steps, sees what you saw. A finding you cannot reproduce is not a finding — record it as an
observation under a separate heading and move on. Unreproducible bugs sent to a Judge produce
rework orders that Workers cannot satisfy, which is how loops start spinning.

Finding format:

```markdown
### QA-003-02 — Sev-2 — Session survives password change
Steps:
1. Log in as user A in browser 1, keep the session
2. Change A's password from browser 2
3. Reload browser 1
Expected: session invalidated, redirect to login (FR-014)
Actual: session still authorised, full access
Evidence: response 200 with user payload; log excerpt below
Trace: AC-009, security contract rule SEC-04
```

**Severity, applied consistently:**

| Sev | Meaning |
|---|---|
| 1 | Security failure, data loss or corruption, or a Must-have acceptance criterion fails |
| 2 | Core journey broken or wrong, no clean workaround |
| 3 | Wrong behaviour with a workaround, or a design- or craft-contract violation |
| 4 | Cosmetic, or a nice-to-have gap |

Sev-1 and Sev-2 block. Sev-3 blocks only when the DoD says so — typically for accessibility, which
should say so. Sev-4 gets logged and deferred.

Three things are Sev-1 wherever they appear, because each is a misrepresentation rather than a defect:
content served differently to crawlers than to users, markup or metadata describing text a user cannot
see, and a fabricated statistic, quotation or source in shipped content.

---

## 3.1b UI Critic pass → `3-verify/qa/UI-###.md`

Only when that role is enabled, and only after the Tester pass. Read
`references/roles.md` brief 16.

The split with the Tester is worth stating because it is the one people get wrong: **the Tester
verifies that the contract's stated rules pass; the Critic judges what a rule cannot capture.** Both
look at UI and they find different defects. The Critic works from the running interface — anti-generic
bans against what actually rendered, token discipline in the computed styles, zero and a thousand rows,
every required state reached and evidenced, and whether three unrelated screens look like one product.

The Critic's discipline is the same as the Adversary's: evidence attached to every finding, the
contract line it breaches quoted, and **no inventing rules where the contract is silent.** A gap in the
contract is an observation with cause `spec`, routed to the Designer — not a rework order against the
Worker. Reporting nothing is legitimate if it lists what was looked at.

---

## 3.2 Judge pass → `3-verify/verdicts/V-###.md`

Full rubric, ordering, and worked examples: `references/judge-rubric.md`. Read it before your
first verdict.

The Judge's constraints are what give the verdict its weight:

- **Writes no source code, ever.** Not a one-line fix, not a typo, not "while I'm here."
- **Accepts no claim without evidence.** "Implemented" is not evidence. A command and its output
  is evidence. A passing test someone else ran is evidence.
- **Reads deltas, not the world.** `git diff --stat`, then targeted diffs on what the rubric
  flags, then the REPORT and QA report. Never the whole tree — that is both expensive and, oddly,
  worse at finding defects, because attention spread thin finds nothing.
- **Classifies the cause.** Code defect → rework to Worker. Spec defect → back to Phase 1. Getting
  this wrong means Workers repeatedly fail to satisfy an order that no code change can satisfy.

**Check order is cheapest-first, and it fails fast.** Missing REPORT is caught in one second; do
not spend a thousand tokens on a diff you were going to reject anyway.

1. Evidence complete — REPORT present and schema-valid
2. Scope intact — files changed ⊆ write-set
3. No test tampering — no test weakened, skipped, or removed
4. Craft — reuse searched, nothing duplicated, conventions followed, no slop
5. Acceptance — each claimed `AC-###` proven by re-runnable evidence
6. QA findings — no open Sev-1 or Sev-2
7. Security contract — every blocking rule satisfied
8. Design contract — if UI
9. Regression — full suite green

**Verdicts:**

- `PASS` — every check clears. The task is closed.
- `REWORK` — one or more checks fail. Issue numbered orders.
- `BLOCKED` — the loop must stop and a human must decide.

---

## 3.3 Rework orders → `3-verify/rework/R-###.md`

A rework order is an instruction, not a complaint. One defect per order. Vague orders produce
vague fixes and a second cycle.

```markdown
## R-012-01 — Sev-1 — Authorisation missing on GET /api/orders/:id
Finding-ID: missing-order-authorization
Domain: security
DoD-impact: no
Finding: The handler loads the order by id without checking ownership.
Evidence: src/api/orders.ts:42-58 — no ownership check between lookup and response.
          QA-005-01 reproduces cross-account read.
Required: Enforce per-resource ownership server-side before the record is returned.
          Return 404, not 403, so existence is not leaked.
Re-check: New integration test — user A requests user B's order id, expects 404.
          Re-run QA-005-01 and confirm it no longer reproduces.
Cause: code
```

Each order carries a stable finding ID, domain, explicit DoD impact, finding, evidence with file and
line or a reproduction, the required change stated as an outcome rather than an implementation, the
re-check that will close it, and the cause classification. The state machine derives recurrence,
security severity, and frozen-DoD stops from these validated fields; optional command-line labels
cannot suppress a stop. Write the required change as an outcome — Judges that prescribe
implementations end up designing, which is not their role and produces worse code than the Worker
would have written.

Send the orders back to a Worker with a read-set containing the order, the original task card, and
`interfaces.md`. Nothing else. The Worker re-runs the task, updates the REPORT, and the cycle
repeats.

---

## 3.4 Loop control

The Judge owns termination. Record the typed outcome through the state machine; do not edit
`loop.json` by hand:

```bash
# PASS: all three independent evidence artifacts are required
loop.py verdict TASK-### pass --qa loop-project/3-verify/qa/QA-###.md \
  --file loop-project/3-verify/verdicts/V-###.md

# REWORK: repeat --order for every numbered order
loop.py verdict TASK-### rework --file loop-project/3-verify/verdicts/V-###.md \
  --order loop-project/3-verify/rework/R-###-01.md

# BLOCKED: state the decision the human must make
loop.py verdict TASK-### blocked --file loop-project/3-verify/verdicts/V-###.md \
  --reason "<specific decision needed>"
```

REWORK increments the task cycle counter atomically with recording its verdict and evidence. Every
order cited by the Judge must have exactly one schema-valid artifact with `Finding-ID`, `Domain`,
`DoD-impact`, severity, evidence, required outcome, re-check, and cause. The old `loop.py cycle`
command is retired because it advanced state without verdict evidence.

**Stop conditions, all hard:**

- The same finding survives 3 rework cycles → `BLOCKED`. Three attempts means the order is wrong,
  the spec is wrong, or the approach is wrong — and none of those are fixed by a fourth attempt.
- A task exceeds 5 total cycles → `BLOCKED`. The task was cut wrong. That is a Phase 0/1 defect.
- A rework order would require changing the frozen DoD → `BLOCKED` immediately. Only a human moves
  the finish line.
- A Sev-1 security finding recurs after being fixed once → `BLOCKED`. Recurrence means the fix was
  local and the cause is structural.

On `BLOCKED`, write the decision the human needs into `ledger.md`: what happened, what was tried,
the two or three options, and your recommendation with its trade-off. Then stop and present it.
Do not keep working around a block — working around a block is how a loop delivers something that
passes every check and solves the wrong problem.

---

## Gate G3 — closing the loop

The whole-project gate. Reached only when every task has a `PASS` verdict.

- [ ] Every Must-have `FR-###` implemented and verified
- [ ] Every `AC-###` in the frozen DoD marked satisfied with named evidence
- [ ] `dod.md` hash matches the value frozen at G0 — no drift
- [ ] Full suite green from a clean clone; no skipped or disabled tests
- [ ] No open Sev-1 or Sev-2
- [ ] Every security contract blocking rule satisfied
- [ ] Craft contract satisfied: registry current, conventions followed, no duplicated components
- [ ] Design contract satisfied, if applicable
- [ ] Secrets absent from the repository and its history
- [ ] README covers install, run, test, deploy
- [ ] `ledger.md` records every deviation and escalation

`python3 scripts/loop.py gate g3 --check` runs the mechanical subset. When all of it clears:
`loop.py gate g3 --pass`.

G3 does not trust the `PASS` string in `loop.json`. It independently validates every task's Worker
task card, REPORT, Tester QA, and Judge verdict, and compares each artifact to the SHA-256 captured
when PASS was recorded. The task, REPORT, and QA must name exactly the same `AC-###` set. It checks
the stored mechanical-verification receipt, every frozen DoD acceptance row's independent passing
QA coverage, and the SHA-256 snapshot of the exact paths delivered by that task. This immutable
per-task boundary includes relevant file mode bits and lets a later task change unrelated files
without invalidating an earlier PASS. G3 also compares every final Git delta to the union of PASS
manifests; a path owned by no passing task blocks closure.
When the Adversary or UI Critic is enabled, every task needs a schema-valid `SEC-###` or `UI-###`
report respectively. An enabled Product Owner needs a `PO-###` PASS that names a `BR-###` and
records observed outcome evidence. Missing, moved, edited, placeholder, path-escaped, or forged
evidence blocks closure.

Then, and only then, tell the human the loop is closed. Report what was built, what was
deliberately not built (the `Won't` list from the BRD, plus anything deferred), where the evidence
lives, and the residual risks worth knowing about. That last part is not padding — a completion
report with no residual risks is a completion report that did not look.
