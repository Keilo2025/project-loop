# Token budget

Multi-agent build frameworks have a reputation for being expensive, and it is deserved. The cost
does not come from having several roles — it comes from every role carrying the entire project
context into every turn, and from models re-deriving in prose what a script could assert in
milliseconds.

Project Loop is designed against both. The rules below are not optimisations to apply if you
remember; they are how the loop is meant to run.

---

## 1. Read-sets are binding

Every role and every task declares the exact files it may read. This is the largest single saving,
because the default behaviour of a capable agent is to read broadly "for context" — which feels
diligent and mostly buys noise.

| Role | Reads | Does not read |
|---|---|---|
| Analyst | the request, the repo if brownfield, the web | — |
| Planner | the request, `research.md`, the repo if brownfield | — |
| Architect | `prd.md`, `dod.md`, `research.md` | `brd.md` — rationale does not move component boundaries |
| Designer | `prd.md`, the UI acceptance rows, `architecture.md` | the BRD, source code |
| Security Architect | `architecture.md`, `interfaces.md`, `prd.md`, `research.md` | task cards, source code |
| Worker | its task card, `interfaces.md`, `conventions.md`, relevant `security.md` section, `design-contract.md` if UI | BRD, PRD, other task cards, other reports |
| Integrator | its task card, `architecture.md`, `interfaces.md`, `conventions.md`, existing build and CI config | application source, the PRD |
| Scribe | `README.md`, `interfaces.md`, merged task cards and REPORTs | application source internals, the BRD |
| Tester | task card, REPORT, `qa-strategy.md`, acceptance rows | architecture, the Worker's reasoning |
| Adversary | `security.md`, `interfaces.md`, task card, the running system | the Worker's reasoning, the BRD |
| Judge | task card, REPORT, QA and SEC reports, DoD rows in scope, `git diff --stat`, targeted diffs | the whole tree |
| Product Owner | `brd.md`, `dod.md`, the Judge's verdicts, the running system | the diff, task cards, REPORTs |

A Worker building a single endpoint does not need to know why the business wants it. If the
endpoint's purpose genuinely changes how it is built, that belongs in the task card — which is
where it can be read for a few hundred tokens instead of several thousand.

**Adding roles does not multiply the read cost, because read-sets partition rather than overlap.**
A Designer reading the UI acceptance rows is reading rows the Architect would otherwise have read
itself. The cost of a larger roster is turns and handoffs, not context — which is why the honest
argument against a role is "its output changes no verdict," never "it reads too much."

---

## 2. Handoff by artifact, never by conversation

Never re-paste a spec into a prompt. Point at the path and let the reader load what it needs.

This is not only about cost. Artifact handoff is what makes the loop survive context compaction, a
crashed session, a switch to a different model, or a human picking it up three weeks later. A loop
whose state lives in a conversation dies with the conversation.

---

## 3. Deterministic checks run in code

`scripts/loop.py` performs, without a model:

- REPORT schema validation
- Write-set enforcement against `git diff --name-only`
- Test-tampering detection (skipped, deleted, or weakened tests)
- Secret scanning
- Near-duplicate detection by name and by normalised body
- Reuse-registry enforcement and the mechanical slop patterns
- DoD hash comparison against the value frozen at G0
- Cycle counting and stop-condition evaluation

Each of these would cost hundreds to thousands of tokens to do by reading, and the script does
them more reliably. Run `loop.py verify TASK-###` before every judgement pass — including the ones
you are sure will pass, because those are exactly the ones where a model skims.

---

## 4. The Judge reads deltas

`git diff --stat` first. It is one screen and it tells you scope, size, and whether test files
moved. Then open only the files the rubric flags. Reading the whole tree is expensive *and* worse
at finding defects, because attention spread thin finds nothing.

---

## 5. Progressive disclosure of the skill itself

`SKILL.md` is a router. Load exactly one phase reference when you enter that phase. Loading all
four costs roughly four times as much and gives no advantage — you cannot act on Phase 3 guidance
while cutting Phase 0 requirements.

Same rule for references: read `security-contract.md` when writing or judging security rules, not
at session start.

---

## 6. Bound the output too

Output tokens cost more than input tokens on most models, and long artifacts get re-read later.

| Artifact | Ceiling |
|---|---|
| REPORT summary | 150 words |
| REPORT total | ~600 words plus command output |
| Rework order | 120 words |
| Verdict | the checks table plus orders — no essay |
| Research notes | two pages |
| Design contract | one page |
| `conventions.md` | two pages — it loads on every task, so a bloated one is a tax paid dozens of times |
| REPORT Reuse section | three lines |

Command output follows the trim rule: whole if it fits in about twenty lines, otherwise every
failure verbatim plus the last twenty lines.

---

## 7. Stable prefixes for cache reuse

Where the runtime supports prompt caching, order every role invocation as **role brief → contracts
→ variable content**. The brief and the contracts are identical across every task, so they cache;
the task card and diff are the only parts that change. Shuffling that order defeats the cache
across an entire build.

---

## 8. No speculative work

A Worker that finishes early stops. It does not refactor an adjacent module, add a test for
something no criterion covers, or improve an unrelated type. Speculative work costs tokens to
write, tokens to review, and it inflates the diff so that real defects hide inside it.

The same applies to research: if a search would not change a decision already made, skip it.

---

## Rough shape of a well-run loop

Indicative, for a small feature — three tasks, one rework cycle:

| Stage | Share of total |
|---|---|
| Phase 0 planning | 20% |
| Phase 1 spec | 20% |
| Phase 2 build | 40% |
| Phase 3 verify and rework | 20% |

If verification is eating more than a third, the tasks are cut too large or the spec is too vague —
both are Phase 0/1 problems that keep charging rent in Phase 3. If planning is under 10%, expect
to pay for it later at a worse exchange rate.

The general principle: **spend early, where a clarifying question costs one line, rather than
late, where the same ambiguity costs a rework cycle.** Rework is roughly an order of magnitude
more expensive than the question that would have prevented it.
