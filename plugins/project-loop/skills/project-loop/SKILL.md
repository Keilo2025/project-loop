---
name: project-loop
description: A closed-loop, evidence-gated build system that takes a project from idea to verified completion across four phases (Plan, Spec, Build, Verify), where a Judge role holds the exit gate and issues rework orders until every acceptance criterion is met with evidence. Use this whenever someone wants to build, ship, rebuild, extend, or finish a software project, feature, MVP, app, API, or service and wants it done properly rather than vibe-coded. Trigger on "project loop", "run the loop", "build me a", "let's build", "ship this feature", "plan and build", "spec it then build it", "take this to done", "don't stop until it works", "keep going until it passes", "autonomous build", "agent loop", "QA this", "review my build", "issue rework", "definition of done", "acceptance criteria", or any request implying a multi-step build with tests, security, or a completion bar. Also use to resume an interrupted build whenever a `.loop/` directory exists in the workspace, and when adding a feature to an existing codebase. Prefer this over ad-hoc coding whenever the work is larger than a single-file edit.
license: MIT
---

# Project Loop

Most agent workflows are pipelines: plan, spec, build, declare victory. The failure mode is
always the same — the thing that wrote the code is also the thing that decides the code is done,
so "done" means "the model ran out of ideas."

Project Loop is a control system, not a pipeline. Work flows forward through four phases, but a
separate **Judge** role holds the exit gate and can only be satisfied by evidence. The Judge never
writes code, so it has nothing to protect. The loop closes when the Judge says PASS, and at no
other moment.

## The one rule

**You may not declare the project complete. Only a Judge verdict of `PASS` closes the loop.**

If you find yourself writing "this should now be working" or "the implementation is complete,"
stop. That sentence belongs to the Judge, and the Judge needs a QA report and a Worker REPORT
before it can say anything at all.

## Start here, every session

Run this before anything else. It is cheap and it prevents the single most expensive mistake in
agentic building — restarting work that already exists.

```bash
python3 scripts/loop.py status
```

Resolve `scripts/loop.py` relative to this skill directory. In Claude Code you can use
`${CLAUDE_PLUGIN_ROOT}/skills/project-loop/scripts/loop.py`.

| `status` says | Do this |
|---|---|
| `no loop found` | New project. Go to Phase 0. Read `references/phase-0-plan.md`. |
| `phase: 0` … `3` | Resume at the reported phase and cursor. Read only that phase's reference. |
| `status: BLOCKED` | Do not continue. Present the blocking decision to the human and wait. |
| `status: PASS` | The loop is closed. Do not reopen it without an explicit new request. |

Never reconstruct state by reading the whole repository or scrolling back through conversation.
State lives in `.loop/loop.json`. That is deliberate: it survives context compaction, session
restarts, and a switch to a different agent entirely.

## Artifact tree

The loop writes and reads exactly this. Nothing else is loop state.

```
.loop/
├── loop.json              # machine state: phase, cursor, cycle counts, verdicts
├── ledger.md              # append-only: decisions, deviations, escalations
├── 0-plan/
│   ├── research.md        # what exists, what constrains us, what we chose
│   ├── brd.md             # business requirements — outcomes and success measures
│   ├── prd.md             # product specification — behaviour, EARS requirements
│   ├── plan.md            # milestones with dates, ownership boundaries
│   └── dod.md             # Definition of Done + acceptance checklist (FROZEN at G0)
├── 1-spec/
│   ├── architecture.md    # components, data flow, contracts, ADRs
│   ├── interfaces.md      # the only file Workers read to know how to fit in
│   ├── security.md        # security contract — blocking rules
│   ├── conventions.md     # THE MEMORY: conventions, reuse registry, bound decisions
│   ├── qa-strategy.md     # what gets tested, how, and what counts as proof
│   └── design-contract.md # tokens, states, a11y bar (only if there is a UI)
├── 2-build/
│   ├── tasks/TASK-###.md      # bounded scope, read-set, write-set, acceptance
│   └── reports/TASK-###.report.md
└── 3-verify/
    ├── qa/QA-###.md           # Tester findings, reproducible
    ├── verdicts/V-###.md      # Judge verdict
    └── rework/R-###.md        # numbered rework orders
```

## Roles and why they are separated

Five roles. The separation is not theatre — it is the mechanism that makes the verdict mean
something. Read `references/roles.md` for the full briefs, read-sets, and prohibitions.

| Role | Writes | Never does |
|---|---|---|
| **Planner** | `0-plan/*` | Write code. Estimate by guessing — it researches first. |
| **Architect** | `1-spec/*` | Implement. Leave a contract ambiguous. |
| **Worker** | source code, its own REPORT, registry entries | Touch files outside its write-set. Modify tests to pass. Build without searching first. |
| **Tester** | `3-verify/qa/*` | Fix what it finds. Report a bug it cannot reproduce. |
| **Judge** | `3-verify/verdicts/*`, `rework/*` | Write or edit any source file. Accept a claim without evidence. |

In Claude Code these map to bundled subagents (`project-loop:loop-planner` and so on), which gives
each role a genuinely separate context window. In other agents, or where subagents are
unavailable, run them as sequential roles in one session — announce the role switch explicitly and
load only that role's read-set. The isolation is weaker but the evidence discipline still holds.

## The four phases

Each phase ends at a gate. A gate is a checklist, not a feeling. Read the phase reference when you
enter the phase — not before, and not all four at once.

| Phase | Produces | Gate | Reference |
|---|---|---|---|
| **0 — Plan** | Research, BRD, PRD, milestones, ownership boundaries, frozen DoD | **G0** — human approves scope and DoD | `references/phase-0-plan.md` |
| **1 — Spec** | Architecture, interfaces, security + craft + design contracts, conventions, QA strategy | **G1** — every DoD item traces to a component and a test | `references/phase-1-spec.md` |
| **2 — Build** | Foundation, then experience; one bounded task at a time, each with a REPORT | **G2** — every task has a schema-valid REPORT | `references/phase-2-build.md` |
| **3 — Verify** | QA report, Judge verdict, rework orders | **G3** — Judge PASS | `references/phase-3-verify.md` |

Phases 2 and 3 are not sequential — they interleave. A task is built, then verified, then either
accepted or reworked. The loop back-edge is `3 → 2`, and it is the whole point.

```
                   ┌──────────── REWORK ────────────┐
                   ▼                                │
  [0 Plan] ──G0──> [1 Spec] ──G1──> [2 Build] ──> [3 Verify] ──G3(PASS)──> done
                       ▲                                │
                       └──────── BLOCKED: spec defect ──┘
```

Two back-edges matter. `3 → 2` is a normal rework: the code is wrong. `3 → 1` is rarer and more
important: the code is right and the spec was wrong. Judges are required to distinguish these,
because fixing code against a broken spec is how projects die slowly.

## Freezing the Definition of Done

At G0 the DoD is frozen. Frozen means: after G0, no one adds, removes, or softens an acceptance
criterion without an explicit human decision recorded in `ledger.md`.

This exists because scope drift is the mechanism by which agentic builds quietly fail. An agent
that can edit the finish line always reaches it. If new scope genuinely emerges mid-build, that is
fine — log it, get a human decision, and either defer it to a follow-up loop or re-cut the DoD
deliberately. What must not happen is the finish line moving on its own.

## Memory, consistency and reuse

A loop that forgets produces a codebase with no author. Task 3 handles errors one way, task 7
another; task 9 rebuilds the date formatter task 4 already wrote. Every task passes its own
acceptance criteria and the result is still a mess, because nothing in a per-task contract can see
across tasks.

The fix is a memory file every Worker reads: `.loop/1-spec/conventions.md`. Three sections —
**conventions** (the decisions different Workers would otherwise make differently), a **reuse
registry** (append-only, one line per reusable unit, written the moment it is created), and
**bound decisions** (constraints from earlier tasks that later ones may not quietly break).

Two obligations follow, and both are enforced:

- **Search before building.** `loop.py reuse "<what you are about to build>"` searches the registry
  and the working tree. Import what fits, extend what nearly fits, build only when neither does —
  and say in the REPORT what you searched for and why it did not fit.
- **Register on creation.** A new component, hook, utility, service or guard gets its registry line
  immediately. A registry written at the end of a project is an inventory, not a memory.

`loop.py verify` checks for near-duplicate names and bodies, unregistered reusables, and the
mechanical slop patterns — empty catch blocks, `any` escape hatches, leftover debug output, TODOs
introduced and abandoned in the same commit, comments that restate the line below them, and names
like `utils2` that tell a reader nothing. The judgement-level rules are check 4 in the Judge
rubric. Full contract: `references/craft-contract.md`.

## Token discipline

The loop is designed to be cheap. Comparable multi-agent frameworks burn tokens by carrying the
whole specification into every turn; this one does not. Full rules in
`references/token-budget.md`. The four that matter most:

1. **Read-sets are binding.** Each role and each task declares the exact files it may read. A
   Worker building a payment endpoint reads its task card, `interfaces.md`, and the relevant
   section of `security.md`. It does not read the BRD. It does not read other tasks.
2. **Handoff is by artifact, not by conversation.** Never re-paste a spec into a prompt. Point at
   the path. This is also what makes the loop survive compaction.
3. **Deterministic checks run in code, not in the model.** Report schema validation, write-set
   enforcement, test-tampering detection, and secret scanning are all `loop.py` subcommands. Do
   not spend model tokens re-deriving what a script can assert.
4. **The Judge reads deltas.** `git diff --stat`, then targeted diffs of flagged files, then the
   REPORT and QA report. Never the whole tree.

A useful instinct: before any large read, ask what verdict it could change. If the answer is
"none," skip it.

## Escalation, and refusing to spin

Loops that cannot stop are worse than pipelines that stop too early. Three hard limits:

- **Same finding fails 3 rework cycles** → verdict `BLOCKED`. Write the decision the human needs
  to make into `ledger.md` and stop.
- **Total cycles on one task exceed 5** → `BLOCKED`. The task was scoped wrong; that is a Planner
  problem, not a Worker problem.
- **A rework order would require changing the DoD** → `BLOCKED`. That is a human decision by
  definition.

`BLOCKED` is a success state for the loop, not a failure. It means the system detected that more
autonomy would destroy value, and handed back control with a specific question. Present the
question plainly and wait.

## Working with an existing codebase

Brownfield is the common case, and the honest answer is that Phase 0 gets shorter and Phase 1 gets
longer. Run `loop.py init --brownfield`, which seeds `research.md` with a repository survey
instead of a blank page. In Phase 1, `interfaces.md` documents what already exists before it
documents what you are adding, and the security contract inherits existing controls rather than
inventing parallel ones. Do not refactor anything that no acceptance criterion depends on.

## Router — read next

Load one of these when you reach the relevant point. Loading all of them defeats the purpose.

| File | Read it when |
|---|---|
| `references/phase-0-plan.md` | Entering Phase 0, or writing BRD/PRD/DoD |
| `references/phase-1-spec.md` | Entering Phase 1, or writing architecture/QA strategy |
| `references/phase-2-build.md` | Entering Phase 2, cutting tasks, or building |
| `references/phase-3-verify.md` | Entering Phase 3, testing, or judging |
| `references/roles.md` | Switching roles, or spawning a subagent |
| `references/report-schema.md` | Writing or validating a Worker REPORT |
| `references/judge-rubric.md` | Rendering a verdict or writing rework orders |
| `references/security-contract.md` | Writing `security.md`, or judging a security finding |
| `references/craft-contract.md` | Writing `conventions.md`, judging craft, or before building anything new |
| `references/design-contract.md` | Any task that produces UI |
| `references/token-budget.md` | The loop feels expensive, or you are about to do a large read |
| `references/portability.md` | Running outside Claude Code, or without subagents |

Templates for every artifact live in `templates/`. Copy them rather than inventing structure —
the Judge's checks assume these shapes.
