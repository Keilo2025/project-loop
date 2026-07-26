# How it works

The mechanism, and a worked example. If you only read one section, read the last one — the
mechanism is easier to see running than described.

---

## Why a loop rather than a pipeline

Spec-driven development solved the first problem with agentic coding: without a spec, the agent
improvises an architecture halfway through and you get something that works until it does not.
Writing the spec first fixes that, and every serious framework in the category now does it.

The second problem is subtler. In a pipeline, the agent that writes the code also decides the code
is finished. It has no adversary. Given a goal and no independent check, the cheapest paths to
"done" include reporting success it did not observe, weakening a failing assertion, and quietly
editing files nobody asked about. None of these require bad faith — they are what optimisation
looks like when the only exit condition is the optimiser's own satisfaction.

Project Loop adds an adversary that cannot be persuaded, because it has nothing at stake: a Judge
that reads evidence, cannot write code, and holds the only exit.

---

## The state machine

```
                     ┌──────────── REWORK (cause: code|craft) ─────────┐
                     ▼                                                 │
    [0 Plan] ──G0──> [1 Spec] ──G1──> [2 Build] ──────────────> [3 Verify] ──G3──> PASS
         ▲               ▲                                             │
         │               └──────── REWORK (cause: spec|scope) ─────────┤
         └───────────────────────── BLOCKED (cause: plan) ─────────────┘
```

Three back-edges, and telling them apart is most of the Judge's value:

- **`3 → 2`** — normal rework. The spec was right, the code was not.
- **`3 → 1`** — the code matches the spec and the spec is wrong. Sending this to a Worker produces
  three failed cycles and nothing learned, because no code change can satisfy it.
- **`3 → 0`** — the acceptance criterion itself is untestable or contradicts another. A human
  decision by definition.

The question that separates them: *if the Worker did exactly what the spec says, would this defect
still exist?* If yes, it is not a code defect.

---

## Gates

| Gate | Guards | Human? |
|---|---|---|
| **G0** | Requirements are researched, testable, and the Definition of Done is agreed | Yes, by default |
| **G1** | Every DoD item traces to a component and a named test; contracts exist and carry checks | No |
| **G2** | Every task has a schema-valid REPORT | No |
| **G3** | Judge PASS on everything, DoD unchanged since G0, suite green, no open Sev-1/2 | Configurable |

G0 does one thing the others do not: it takes the SHA-256 of `dod.md` and stores it in
`loop.json`. Every subsequent `status` compares them. An agent that can edit the finish line always
reaches it, so the finish line is nailed down before anyone starts running.

---

## The four contracts

Each is instantiated per project in Phase 1, and each is enforced by a Judge check.

| Contract | Lives in | Guards against |
|---|---|---|
| Interfaces | `1-spec/interfaces.md` | Workers guessing at shapes and producing code that does not fit |
| Security | `1-spec/security.md` | Missing authorisation, unvalidated boundaries, committed secrets |
| Craft | `1-spec/conventions.md` | Duplication, convention drift, slop |
| Design | `1-spec/design-contract.md` | UI that passes every test and is obviously unshippable |

Every rule in every contract must carry a stated check. A rule without one is a wish, and Workers
learn within two tasks to skim a list of wishes.

---

## Memory

`conventions.md` is the only file that grows during the build, and it is the only thing that lets
task 20 look like task 1.

```
## 2. Reuse registry
| Name | Path | Purpose | Created by | Used by |
|------|------|---------|-----------|---------|
| formatCurrency | src/lib/format.ts | AED/USD display with locale | TASK-004 | TASK-007 |
| requireOwner | src/auth/guards.ts | Per-resource ownership guard | TASK-002 | all routes |
```

A Worker about to build something runs `loop.py reuse "currency format"`, which searches the
registry and the working tree. Then it imports what fits, extends what nearly fits, or builds and
registers — recording which of the three happened in the REPORT.

This works only because registration happens at creation. A registry filled in at the end of a
project is an inventory: accurate, and useless, because the duplication it would have prevented
already shipped.

---

## Worked example

A finance team wants expense approvals. Here is one task through the whole machine.

### Phase 0

The Planner researches, then writes requirements in EARS:

> **FR-011** — When an approver rejects an expense, the system shall record the rejection reason
> and notify the submitter within 60 seconds.
> **FR-012** — If an approver attempts to act on an expense outside their department, then the
> system shall refuse the action and return 404.

And the acceptance rows:

| ID | Requirement | How it is proven | Evidence |
|---|---|---|---|
| AC-014 | FR-011 rejection records reason and notifies | integration test `reject.spec.ts` | REPORT output |
| AC-015 | FR-012 cross-department action refused with 404 | integration test `authz.spec.ts` | REPORT output |

Human approves at G0. `dod.md` is hashed. From here nobody moves the finish line without saying so.

### Phase 1

The Architect writes the contracts. In `security.md`:

| ID | Rule | Applies to | Check | Blocking |
|---|---|---|---|---|
| SEC-02 | Per-resource authorisation, server-side | all `/api/expenses/*` | cross-department test per route | Yes |

In `conventions.md`: errors throw `AppError` and are handled once at the edge; validation is Zod at
the boundary; the registry already lists `requireOwner` from the auth foundation task.

Then a task card:

```
# TASK-011 — Expense rejection
## Write-set
- src/expenses/**
- tests/integration/reject.spec.ts
## Acceptance
| AC-014 | FR-011 | reject.spec.ts |
| AC-015 | FR-012 | authz.spec.ts |
```

### Phase 2

The Worker searches first:

```
$ loop.py reuse "authorisation guard"
registry (.loop/1-spec/conventions.md)
  | requireOwner | src/auth/guards.ts | Per-resource ownership guard | TASK-002 | all routes |
```

So it imports `requireOwner` rather than writing a department check inline. It builds, writes both
tests, runs the suite, and files a REPORT with the exact commands and output.

Then:

```
$ loop.py verify TASK-011
  PASS  report schema
  PASS  scope intact                  4 changed, 0 outside write-set
  PASS  test integrity                clean
  PASS  no secrets introduced         clean
  PASS  files changed listed          ok
  PASS  no duplicated components      clean
  FAIL  no slop patterns              1 finding(s)     [Sev-3]
    - src/expenses/reject.ts:31 debug output left in source
  PASS  reusables registered          clean
  PASS  reuse search recorded         ok
```

One `console.log` left behind. The Worker removes it before the Tester ever sees the code — which
is the point of the deterministic layer: it catches the cheap things cheaply.

### Phase 3

The Tester runs the acceptance tests independently, then attacks. It finds this:

```
### QA-011-01 — Sev-1 — Approver can reject across departments via the bulk endpoint
Steps:
1. Log in as an approver in Department A
2. POST /api/expenses/bulk-reject with an id belonging to Department B
3. Observe the expense is rejected
Expected: refused with 404 (FR-012, SEC-02)
Actual: 200, rejection recorded
Trace: AC-015, SEC-02
```

`requireOwner` was applied to the single-expense route and not the bulk one. The single-expense
test passes. The acceptance criterion looked satisfied.

The Judge runs the rubric. Checks 1–4 clear. Check 5 flags that AC-015 is proven only for one of
two routes. Check 6 has an open Sev-1. Check 7 fails SEC-02. Verdict: `REWORK`.

```
## R-011-01 — Sev-1 — Bulk reject bypasses per-resource authorisation
Finding: requireOwner is applied to POST /expenses/:id/reject but not to /expenses/bulk-reject.
Evidence: QA-011-01 reproduces on a clean checkout. src/expenses/bulk.ts:22 has no guard.
Required: Every route that mutates an expense enforces per-resource authorisation server-side.
          Refuse with 404, not 403, so existence is not leaked.
Re-check: Extend authz.spec.ts to cover the bulk route. Re-run QA-011-01.
Cause: code
```

Cycle 1. Worker fixes it, Tester re-runs, Judge issues `PASS`.

Had this been a pipeline, `reject.spec.ts` and `authz.spec.ts` would both have been green, the
REPORT would have said "Done," and a cross-department authorisation bypass would have shipped
behind two passing tests.

### Closing

When every task holds a `PASS`, G3 runs: DoD hash unchanged, suite green from a clean clone, no
open Sev-1 or Sev-2, no secrets, README complete. Then the loop closes and reports what was built,
what was deliberately not built, where the evidence lives, and the residual risks.

---

## Reading the state

Everything is in `.loop/`, in Markdown and one JSON file. Commit it.

```bash
loop.py status          # phase, cursor, gates, open tasks, DoD drift warning
cat .loop/ledger.md     # every decision, deviation and escalation, in order
```

A build can start in Claude Code and finish in Codex, or be picked up by a colleague weeks later,
with no conversation history at all. If handing it over requires explaining what was happening, the
loop was being run out of the chat rather than out of the artifacts — and that is worth correcting
before continuing, because it means the state is somewhere that will not survive.
