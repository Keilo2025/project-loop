# Phase 2 — Build

Roles: **Architect** cuts tasks, **Worker** executes them. Output: source code plus
`/loop-project/2-build/`. Exit: gate **G2**, though in practice Phase 2 and Phase 3 interleave per task.

The build order is fixed and it is not negotiable: **foundation first, then experience.** Building
a beautiful screen on top of an unsettled data model produces work that has to be thrown away, and
worse, it produces the *feeling* of progress while the risk is untouched. Ship the boring layers
first.

---

## 2.1 Cutting tasks

A task is the unit the Judge accepts or rejects, so its scope determines how expensive a rejection
is. Cut too large and every rework re-examines everything; cut too small and coordination
overhead eats the savings.

**Right-sizing.** One task should be completable in a single focused pass, touch fewer than about
eight files, and close between one and three acceptance criteria. If a task needs a mid-flight
decision that is not already in the spec, it is too large — split it, or send the decision back to
Phase 1.

**Every task card declares four things.** Template: `templates/task.md`.

1. **Scope** — what is being built, in one paragraph, plus what is explicitly out of scope.
2. **Read-set** — the exact files this Worker may read. Typically the card itself,
   `1-spec/interfaces.md`, `1-spec/conventions.md`, the relevant section of `1-spec/security.md`,
   and the source files it will modify. Not the BRD. Not the PRD in full. Not other task cards.
   `conventions.md` is always in the read-set — it is the only thing standing between twenty tasks
   and twenty personal styles.

   **Name the contracts this task must satisfy, and only those.** With every specialist role
   enabled there are six contracts in `1-spec/`, and putting all six in every read-set turns them
   into a tax paid on every task. A UI task cites `design-contract.md`, `ux-contract.md` and
   `content-contract.md`; a page template or metadata task cites `seo-contract.md` and
   `ai-readiness.md`; a background job cites none of them. Choosing well is the Architect's job —
   a Worker that has to guess which contract applies will either read all of them or none.
3. **Write-set** — the exact paths this Worker may create or modify. Enforced mechanically at
   verification; anything outside is a scope violation regardless of how good the change was.
4. **Acceptance** — the `AC-###` items this task closes, each with the test or procedure that
   proves it.

**Dependencies.** Record which tasks must complete first. Do not run two tasks whose write-sets
intersect, ever — not in parallel, not "carefully." One writer per file.

**Ordering.** Foundation tasks in the order set in `architecture.md`. Then experience tasks. Within
experience work, build the shell and shared components before the screens that consume them.

---

## 2.2 Executing a task as Worker

The Worker's contract is narrow on purpose. Narrow scope is what makes the REPORT trustworthy,
and the REPORT is what the whole verification stage runs on.

**Search before you build.** Before creating any component, hook, utility, service, type or
endpoint:

```bash
python3 scripts/loop.py reuse "currency format"
```

Import what fits. Extend what nearly fits, if extending keeps it single-purpose. Build only when
neither does — and record in the REPORT's `Reuse` section what you searched for and why nothing
found was suitable. Then add the registry line to `conventions.md` immediately, not at the end.

The second time a pattern appears, extract it. Not the first — an abstraction with one caller is a
guess about the future. Not the third — by then three call sites have diverged and it is a
refactor rather than a move.

**Do:**

- Load only the read-set. If something is missing from it, say so and stop — that is a spec defect
  and it routes back to the Architect, not around it.
- Build the smallest change that satisfies the acceptance criteria.
- Write the tests named in the acceptance rows. Where the QA strategy asks for tests first, write
  them first and watch them fail before making them pass — a test that has never failed has proven
  nothing.
- Run the full test suite, not only the new tests. Capture the exact command and the exact output.
- Write the REPORT before saying anything to anyone.

**Do not:**

- Touch files outside the write-set. If the change genuinely requires it, stop and request a scope
  amendment. The Architect can widen the write-set in seconds; an unrecorded out-of-scope edit
  costs a rework cycle and undermines every subsequent verdict.
- Modify, weaken, skip, or delete an existing test to make the suite pass. This is detected
  automatically and is an immediate Sev-1. If a test is genuinely wrong, say so in the REPORT under
  `Blocked` and let the Judge rule on it.
- Refactor, tidy, rename, or improve anything no acceptance criterion depends on. Unasked-for
  changes are the main reason diffs become unreviewable, and unreviewable diffs get rubber-stamped.
- Add a dependency that is not in the spec without recording it in the REPORT with a reason. New
  dependencies are supply-chain surface.
- Invent a convention. If `conventions.md` covers it, follow it. If it does not and the decision
  binds later tasks, add a bound decision rather than choosing silently. Two conventions in one
  codebase is worse than either one consistently.
- Break a bound decision because this case seems different. Stop and request an amendment. That
  instinct — this case is special — is exactly how a codebase acquires its second convention.
- Leave slop. Empty catch blocks, `any` escape hatches, leftover `console.log`, a TODO introduced
  and abandoned in the same commit, a comment restating the line below it, a file called `utils2`.
  All of these are detected mechanically; fixing them after a rework order costs more than not
  writing them.
- Report success you did not observe. "Should work" is not a result. If you could not run
  something, say you could not run it — an honest `Blocked` costs one cycle, a false `Done` costs
  three and burns the Judge's trust in every other line of the report.

---

## 2.3 The REPORT

Every task produces `/loop-project/2-build/reports/TASK-###.report.md`. **No REPORT means automatic
REWORK** — the Judge does not open the code to compensate for a missing report, because doing so
would convert the Judge into a reviewer of intentions rather than evidence.

Full schema and a worked example: `references/report-schema.md`. The shape:

```markdown
# REPORT TASK-007
Status: Done | Partial | Blocked

## Summary
<= 150 words. What changed and why. No adjectives.

## Files changed
- path/to/file.ts (new|modified|deleted) — one line on what and why

## Commands run
$ <exact command>
<output: full if it fits in ~20 lines, otherwise failures verbatim plus the last 20 lines>

## Reuse
What you searched for, what you reused, what you created new and why nothing existing fit.

## Acceptance
| AC | Proven by | Result |
|----|-----------|--------|
| AC-004 | test `auth.spec.ts::rejects expired token` | pass |

## Assumptions
Anything inferred rather than specified. If empty, write "none".

## Risks
What might be wrong, or what you would check first if it broke.

## Blocked
Anything you could not do, and why. If empty, write "none".
```

The sections that people are tempted to leave blank — **Assumptions**, **Risks**, **Blocked** —
are the ones that carry the most signal. A Worker that consistently writes "none" in all three is
either doing trivial work or not looking. Judges are instructed to treat a suspiciously clean
report as a reason to sample the diff more deeply, so there is no advantage in polishing it.

Length discipline: a REPORT over roughly 600 words is usually hiding the important part in the
middle. Trim the prose, keep the command output.

---

## 2.4 Foundation-first, in practice

The foundation is done when a new feature can be added without touching any of it. Concretely:

- Toolchain, formatter, linter, and type checking run clean from a clean clone
- Configuration loads from the environment and fails loudly when something required is missing
- The data layer runs migrations forward and backward
- Auth issues, validates, and revokes a session
- Errors are handled in one place with one shape
- Logging is structured, and carries a correlation identifier
- The test harness runs a single test and the whole suite, both documented
- For UI: tokens, base layout, and one real component that exercises every required state

Only then does experience work start. If a stakeholder is anxious about seeing something, build one
real screen against the real foundation rather than a mock — a demo built on scaffolding creates an
expectation the foundation then has to satisfy backwards.

---

## Gate G2

Per task, before it goes to Phase 3 verification:

- [ ] REPORT exists and validates against the schema
- [ ] Files changed ⊆ declared write-set
- [ ] Every acceptance row has a result, not a promise
- [ ] Full suite was run and its output is in the report
- [ ] No test file was weakened, skipped, or deleted
- [ ] New dependencies are named with a reason
- [ ] Reuse search recorded; new reusables registered in `conventions.md`
- [ ] No near-duplicate of an existing file; no mechanical slop patterns

`python3 scripts/loop.py verify TASK-###` runs all of these mechanically. It is cheap, it runs in
milliseconds, and it catches the majority of REWORK causes before a single model token is spent
judging. Run it always, even when you are confident — especially when you are confident.

Then hand to Phase 3.
