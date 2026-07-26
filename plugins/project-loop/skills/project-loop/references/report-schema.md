# REPORT schema

Every task produces exactly one REPORT at `loop-project/2-build/reports/TASK-###.report.md`. It is the
only thing the Judge is required to read from the Worker, so it carries the whole weight of the
handoff.

The schema is deliberately rigid. Rigidity is what lets `loop.py verify` check it in milliseconds
instead of a model checking it in thousands of tokens — and a report that fails validation is
rejected before any expensive review begins.

---

## Required sections

All eight headings, in this order, spelled exactly as shown.

```markdown
# REPORT TASK-###
Status: Done | Partial | Blocked

## Summary
## Files changed
## Commands run
## Reuse
## Acceptance
## Assumptions
## Risks
## Blocked
```

Empty is not allowed. Write `none` where a section genuinely has nothing.

---

## Section rules

**Status.** `Done` means every acceptance criterion on the card is closed with evidence.
`Partial` means some are and some are not. `Blocked` means you could not proceed. Choose honestly:
`Blocked` costs one cycle, a false `Done` costs three and devalues everything else you wrote.

**Summary.** 150 words maximum. What changed and why. No adjectives — "robust", "comprehensive",
"clean" carry no information and are read as noise.

**Files changed.** One line per file: path, whether it is new, modified or deleted, and one clause
on what and why. This is cross-checked against the write-set automatically, so it must be complete.
A file changed but not listed is a scope violation whether or not it was intentional.

**Commands run.** The exact commands, with their output. Not paraphrased, not summarised.

Output length rule: if the output fits in about twenty lines, include it whole. If it does not,
include every failure verbatim plus the last twenty lines. Never include thousands of lines of a
passing suite — the tail and the summary line are what carry the information.

```
$ npm test
 PASS  src/auth/session.spec.ts
 PASS  src/api/orders.spec.ts
Tests: 142 passed, 142 total
Time:  8.31 s
```

**Reuse.** What you searched for before building, what you reused, and what you created new. This
is the section that stops task 9 rebuilding task 4's work. Three lines is usually enough:

```
Searched: "currency format" — found src/lib/format.ts, imported formatCurrency.
Searched: "receipt thumbnail" — nothing suitable; the existing <Avatar> is circular and
  fixed-size. Created <ReceiptThumb>, registered in conventions.md.
```

An empty Reuse section on a task that created new files reads as "did not look," and Judges treat
it that way.

**Acceptance.** A table, one row per `AC-###` the task claims to close.

| AC | Proven by | Result |
|----|-----------|--------|
| AC-004 | `auth.spec.ts::rejects expired token` | pass |
| AC-005 | manual: measured with Lighthouse, LCP 1.2s | pass |

"Proven by" must name something re-runnable. "Verified manually" without a procedure is not proof
and will be rejected at check 4.

**Assumptions.** Anything you inferred rather than read in the spec. This is the section that
prevents the most rework, because an assumption surfaced here costs one line and an assumption
discovered in Phase 3 costs a cycle. Write `none` only when it is true.

**Risks.** What might be wrong, or what you would check first if this broke in production. One or
two lines. Judges use this to decide where to sample the diff.

**Blocked.** What you could not do and why. A spec gap, a missing credential, a test you believe
is wrong, a dependency that does not behave as documented. Anything here routes to the Judge for a
ruling — which is the correct path. Working around a block silently is how a build ends up
solving a slightly different problem than the one specified.

---

## Worked example

```markdown
# REPORT TASK-007
Status: Partial

## Summary
Added session invalidation on password change. Password update now revokes all sessions for the
account and forces re-authentication. Added an integration test covering the multi-client case.
The rate limit on the password endpoint (AC-010) is not implemented — the middleware it depends
on lands in TASK-009.

## Files changed
- src/auth/password.ts (modified) — revoke sessions after hash update
- src/auth/session-store.ts (modified) — added revokeAllForUser
- src/auth/session-store.spec.ts (new) — unit tests for revocation
- tests/integration/password-change.spec.ts (new) — multi-client integration test

## Reuse
Searched "session revoke" — found session-store.ts, extended it with revokeAllForUser rather
than adding a parallel module. Registered the new export in conventions.md.

## Commands run
$ npm run typecheck
tsc --noEmit — 0 errors

$ npm test
 PASS  src/auth/session-store.spec.ts
 PASS  tests/integration/password-change.spec.ts
Tests: 148 passed, 148 total
Time:  9.02 s

$ npm run lint
0 problems

## Acceptance
| AC | Proven by | Result |
|----|-----------|--------|
| AC-009 | `password-change.spec.ts::invalidates other sessions` | pass |
| AC-010 | rate limit middleware — not available | not done |

## Assumptions
Revocation is immediate rather than deferred to token expiry. The PRD says "invalidated" without
specifying timing; immediate is the safer reading.

## Risks
revokeAllForUser scans by user id. On a large session table this will need an index — fine at
current scale, worth checking before launch.

## Blocked
AC-010 depends on rate limit middleware from TASK-009, which is not merged. Left unimplemented
rather than duplicating the middleware locally.
```

That report will draw a `REWORK` on AC-010, and it should — but it draws a cheap one. The Judge
knows exactly what is missing, why, and what unblocks it, without opening a single source file.
That is what a good report buys.

---

## Validation

`python3 scripts/loop.py verify TASK-###` checks:

| # | Check |
|---|---|
| 1 | All eight headings present, in order |
| 2 | `Status` is one of Done, Partial, Blocked |
| 3 | Summary is non-empty and under 150 words |
| 4 | Files-changed list matches `git diff --name-only` for the task |
| 5 | Every changed file is inside the declared write-set |
| 6 | At least one command with output is present |
| 7 | Acceptance table has a row per claimed `AC-###`, each with a result |
| 8 | Assumptions, Risks and Blocked are present (`none` counts) |
| 9 | No test file weakened, skipped, or deleted |
| 10 | No plausible secret introduced |
| 11 | Reuse section has content |
| 12 | No new file near-duplicating an existing one |
| 13 | New reusable units registered in `conventions.md` |
| 14 | No mechanical slop patterns |

Failures 1–8 and 11 are report defects: fix the report. Failures 9 and 10 are Sev-1 and go straight
to the Judge. Failures 12–14 are craft findings, Sev-2 for duplication of a registered component
and Sev-3 otherwise.
