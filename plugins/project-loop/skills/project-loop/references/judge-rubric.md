# Judge rubric

The rubric is ordered by cost, not by importance. Each check is cheaper than the one after it, and
the first failure ends the pass. There is no value in a thorough review of work that was going to
be rejected on its first line.

Run `python3 scripts/loop.py verify TASK-###` before reading anything. It performs checks 1 through 4, in their mechanical half,
deterministically in milliseconds and reports which of the remaining checks need attention. A
Judge that re-derives by hand what a script already asserted is burning tokens for no additional
confidence.

---

## Check 1 — Evidence completeness

`loop-project/2-build/reports/TASK-###.report.md` exists and validates against
`references/report-schema.md`.

Fail → `REWORK`, order: "Produce a schema-valid REPORT." Do not open the diff. Do not infer what
the Worker probably did. The absence of a report is itself the finding, and reconstructing the
report on the Worker's behalf teaches the loop that reports are optional.

## Check 2 — Scope integrity

Files changed ⊆ the write-set declared on the task card.

Fail → `REWORK`, Sev-2. State every out-of-scope path. A useful improvement made outside scope is
still a scope violation: it was not reviewed against a contract, it may collide with another task,
and accepting it once makes write-sets advisory. If the change was genuinely needed, the fix is a
recorded scope amendment, not retrospective forgiveness.

## Check 3 — Test integrity

Diff the test paths separately. Flag any of:

- A test file deleted, or a test case removed
- `skip`, `only`, `xit`, `pending`, `@Disabled`, `#[ignore]`, or equivalent added
- An assertion weakened — a tightened tolerance loosened, a specific expectation replaced by a
  truthiness check, an exact match replaced by a substring match
- A test's expected value edited to match observed output rather than the specification
- Timeouts raised without a stated reason

Any of these → `REWORK`, **Sev-1**. This is the highest-leverage check in the rubric, because it
is the one failure mode that makes every other check unreliable. Do not accept "the test was
wrong" as a Worker's unilateral conclusion — if the test really was wrong, that is a finding for
the Judge to rule on, recorded in the ledger, not a change to be made quietly.

## Check 4 — Craft: reuse, consistency, slop

`loop.py verify` covers the mechanical half: near-duplicate names and bodies, unregistered
reusables, empty catch blocks, `any` escape hatches, leftover debug output, TODOs introduced by
this task, comments restating the line below, and names that carry no information.

Your half is judgement, and it is the half that compounds:

- **Was something rebuilt that already existed?** Check the `Reuse` section of the REPORT against
  the registry in `conventions.md`. An empty Reuse section on a task that created new files means
  the Worker did not look.
- **Does this read like the rest of the codebase?** Open one existing file in the same layer and
  compare. Different error shapes, different naming, a second way of doing something already
  decided in `conventions.md` — each is defensible alone and corrosive in aggregate.
- **Defensive noise.** Null checks on values that cannot be null, try/catch around code that does
  not throw, validation repeated at three layers. Each looks careful; together they hide where the
  real boundary is.
- **Abstraction with one caller.** A base class or generic helper introduced for a single use.
- **Copy-paste with variation.** Two blocks differing in one identifier.
- **Dead scaffolding.** Exports nobody imports, parameters nobody passes.

Fail → `REWORK`. Sev-2 when something in the registry was duplicated or a bound decision was
broken; Sev-3 otherwise. Sev-3 blocks only where `qa-strategy.md` says craft rules are blocking —
which it should, on anything with a maintenance life beyond this quarter.

One thing not to do: do not order a Worker to clean up slop it did not write. The craft contract
governs what this task produced, not what it found nearby. Pre-existing problems become their own
task, or they stay.

## Check 5 — Acceptance

For each `AC-###` the task claims to close: is there evidence a third party could re-run, and does
that evidence actually demonstrate the criterion?

Watch for the near-miss. A test named `rejects expired token` that asserts only that the response
is not 200 does not prove the criterion "shall return 401 with no body." Read what the test
asserts, not what it is called.

Fail → `REWORK`, Sev-1 for a Must-have, Sev-2 otherwise.

## Check 6 — QA findings

Any open Sev-1 or Sev-2 in the QA report → `REWORK`. Sev-3 blocks only where the DoD says so.
Sev-4 is logged and deferred without blocking.

If the Tester recorded observations it could not reproduce, do not convert them into rework
orders. Note them in the verdict so they are not lost, and move on.

## Check 7 — Security contract

Each blocking rule in `1-spec/security.md`, checked by the method the rule declares. Any failure
→ `REWORK`, Sev-1, regardless of everything else.

Give particular attention to the ones that pass silently: per-resource authorisation on new
routes, validation at every new trust boundary, and secrets that reached a log or a fixture.

## Check 8 — Design contract

UI tasks only. Every required state present, keyboard traversal complete, focus visible, contrast
measured, behaviour correct at the narrowest supported width, motion respecting the reduced-motion
preference, tokens used instead of literal values.

Fail → `REWORK`, Sev-3 by default, Sev-2 where the DoD makes accessibility blocking. It usually
should.

## Check 9 — Regression

Full suite green, from the output in the REPORT and confirmed by the Tester. Any test that was
passing before and is not now → `REWORK`, Sev-1.

---

## Cause classification

Every rework order names a cause, and it changes where the work goes:

| Cause | Meaning | Routes to |
|---|---|---|
| `code` | The spec was right, the implementation was not | Worker |
| `craft` | Correct behaviour, duplicated or inconsistent construction | Worker |
| `spec` | The implementation matches the spec; the spec is wrong or incomplete | Architect, Phase 1 |
| `scope` | The task was cut wrong — too large, or overlapping another | Architect, re-cut |
| `plan` | The acceptance criterion is untestable or contradicts another | Human, Phase 0 |

Getting this wrong is the main way loops spin. A Worker cannot satisfy a `spec` defect with a code
change, so it will try something plausible, fail, and try again — three cycles later you are
`BLOCKED` with nothing learned. Ask a simple question before assigning cause: *if the Worker did
exactly what the spec says, would this defect still exist?* If yes, the cause is `spec`.

---

## Verdict format

```markdown
# VERDICT V-008 — TASK-007 — cycle 2
Date: 2026-07-26
Verdict: REWORK

## Checks
| # | Check | Result | Note |
|---|-------|--------|------|
| 1 | Evidence complete | pass | |
| 2 | Scope intact | pass | 6 files, all in write-set |
| 3 | Test integrity | pass | |
| 4 | Craft | fail | rebuilt `formatCurrency`, already in registry |
| 5 | Acceptance | fail | AC-009 not proven |
| 6 | QA findings | fail | 1 open Sev-2 |
| 7 | Security contract | pass | |
| 8 | Design contract | n/a | no UI |
| 9 | Regression | pass | 142 passed, 0 failed |

## Orders
R-008-01 (Sev-2, cause: code)
R-008-02 (Sev-2, cause: code)

## Observations
QA noted intermittent slowness on the orders list; not reproducible, not blocking. Logged.

## Loop state
Cycle 2 of 5 for TASK-007. No finding has recurred. Continue.
```

## Rework order format

```markdown
## R-008-01 — Sev-2 — Session survives password change
Finding: Changing a password does not invalidate existing sessions.
Evidence: QA-005-02 reproduces on a clean checkout, steps 1-3.
          src/auth/password.ts:88 updates the hash and returns; no session revocation.
Required: Invalidate all existing sessions for the account when its password changes.
          Behaviour is specified by FR-014 and security rule SEC-04.
Re-check: Integration test — log in, change password from a second client, confirm the first
          session returns 401. Then re-run QA-005-02 and confirm it no longer reproduces.
Cause: code
```

State the required change as an **outcome**. "Invalidate all existing sessions" is an outcome;
"add a `sessionVersion` column and increment it" is a design decision, and it is not the Judge's
to make. Judges that prescribe implementations end up designing badly at the wrong moment, and
Workers stop thinking.

---

## Termination

Increment the cycle counter on every REWORK: `loop.py cycle TASK-###`.

| Condition | Verdict |
|---|---|
| All eight checks pass | `PASS` — task closed |
| Any check fails, within limits | `REWORK` — issue orders |
| Same finding fails 3 cycles | `BLOCKED` |
| Task exceeds 5 total cycles | `BLOCKED` |
| An order would require changing the frozen DoD | `BLOCKED` |
| A Sev-1 security finding recurs after being fixed | `BLOCKED` |

On `BLOCKED`, write to `ledger.md`: what happened, what was tried across the cycles, two or three
options with their trade-offs, and a recommendation. Then stop.

A Judge that never blocks is not being rigorous, it is being agreeable — and an agreeable Judge is
the exact failure this whole design exists to prevent.
