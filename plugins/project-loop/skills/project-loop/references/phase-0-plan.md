# Phase 0 — Plan

Role: **Planner**. Output: `/loop-project/0-plan/`. Exit: gate **G0**, which requires a human.

Phase 0 exists to make the rest of the loop cheap. Every ambiguity left here becomes a rework
cycle later, and rework cycles cost roughly ten times what a clarifying question costs. The
Planner's job is to be expensive once so that Phases 1–3 are cheap repeatedly.

Order matters: choose the team, then research, then business requirements, then product
specification, then milestones and boundaries, then the Definition of Done last — because the DoD
is derived from everything above it, and freezing it is the gate.

---

## 0.0 Choose the role set

Before any research, decide who is running this loop. Eighteen roles are available across four
authority classes; five are enabled by default. Full roster and briefs: `references/roles.md`.

```bash
python3 scripts/loop.py roles --recommend
```

The recommendation reads the shape of the project — UI files or UI language, a named audience, auth
and personal data, a public surface, regulated-vertical language, a deployment target, how many
business requirements exist — and proposes a set with the signal that argued for each one. **It is a recommendation, not a decision.** Present it to the
human with the trade stated plainly:

> More roles catch more and cost more. Fewer roles do not skip the work — the core role in the
> same class absorbs it, with less specialisation and a wider context.

Then apply what they choose:

```bash
python3 scripts/loop.py roles --preset growth             # core 5 | standard 8 | product 12 | growth 15 | full 18
python3 scripts/loop.py roles --enable designer,adversary
python3 scripts/loop.py roles --enable domain-analyst --vertical proptech
python3 scripts/loop.py roles --confirm                   # the core five are right here
```

The test for enabling an optional role is whether its output would change a verdict. A Designer
earns its place when the design contract is a gate somebody will actually fail against; it does not
earn its place on a CLI tool. A role whose artifact nobody gates on makes the loop slower and more
expensive without making it more correct.

Enabling a role has teeth: with the Designer on, G1 requires `design-contract.md`; with the UX
Researcher on, G1 requires numeric completion bars; with the SEO or LLM Specialist on, G1 requires a
stated check against every selected rule; with the Domain Analyst on, G0 requires a vertical and a
dated domain brief; with the Adversary or UI Critic on, G3 requires their report; with the Product
Owner on, G3 requires business acceptance. That is the point — an optional role that changed no gate
would be ceremony.

Two caveats to state honestly when presenting the set. **The Domain Analyst needs a vertical**
(`--vertical list` shows them); without one it is a second Analyst at the same cost. **The SEO and
LLM Specialists are unabsorbed** — no other role picks their work up, so leaving them off removes it
rather than moving it.

G0 will not pass until the set has been confirmed. The choice and its reason go into `ledger.md`
automatically. Changing the roster later is allowed and is another ledger entry, not a silent edit.

---

## 0.1 Research → `research.md`

Owned by the **Analyst** when that role is enabled, by the Planner when it is not.

Do not skip this because the request seems clear. The most common cause of a failed build is not
misunderstanding the request; it is missing a constraint that was knowable.

Establish, in this order:

- **What already exists.** For brownfield: survey the repo — languages, frameworks and versions,
  build and test commands, existing auth, existing data model, CI. For greenfield: what the user
  already has (accounts, infra, design system, domain).
- **Hard constraints.** Runtime, hosting, budget, deadline, compliance regime, data residency,
  team skill, existing vendor contracts. These are not preferences; they eliminate options.
- **Prior art.** What do comparable products do, and where do they fail? Where the choice is
  non-obvious or the ecosystem moves fast (frameworks, libraries, APIs, pricing, regulation), use
  web search rather than recall. Record what you verified and when.
- **Decisions taken, with alternatives rejected.** Each decision gets one line of rationale. This
  is what stops the loop relitigating choices in Phase 2.

Write it short. Research notes that nobody reads are a token tax with no payoff. Two pages is
usually right; five means you are writing an essay.

**Ask the human when you genuinely cannot infer.** Batch the questions — three at once, not one
per turn. Good candidates: target users, non-negotiable deadline, budget ceiling, compliance
regime, whether this replaces something existing, and what "good enough to ship" means to them.

---

## 0.2 Business requirements → `brd.md`

The BRD answers *why*, in the language of outcomes, not features. `loop.py init` seeds this file in `/loop-project/0-plan/`.

Each business requirement is `BR-###` and must state:

- The outcome, phrased as a change in the world, not a thing that exists.
  Poor: "a dashboard showing signups." Good: "operations can see within one hour that signups
  have stalled, instead of finding out at month end."
- Who it is for, specifically enough to be falsifiable.
- How success is measured, with a number and a date where possible.
- What happens if it is not delivered. If the answer is "nothing," cut it.

Then rank: **Must / Should / Could / Won't-this-cycle**. The `Won't` list is the most valuable
part of a BRD, because it is the only place scope gets actively closed. Write it down.

---

## 0.3 Product specification → `prd.md`

The PRD answers *what the system does*. `loop.py init` seeds this file in `/loop-project/0-plan/`.

Write functional requirements in **EARS** notation. EARS constrains natural language into six
patterns, each of which collapses to a single testable claim — which is exactly what a Judge
needs, and exactly what a vague sentence cannot provide.

| Pattern | Template | Use for |
|---|---|---|
| Ubiquitous | The `<system>` shall `<response>` | Always-true properties |
| Event-driven | When `<trigger>`, the `<system>` shall `<response>` | Reactions to something happening |
| State-driven | While `<state>`, the `<system>` shall `<response>` | Behaviour that holds in a mode |
| Unwanted behaviour | If `<condition>`, then the `<system>` shall `<response>` | Errors, failures, abuse |
| Optional feature | Where `<feature is included>`, the `<system>` shall `<response>` | Configurable capability |
| Complex | Combinations of the above | Only when genuinely irreducible |

Rules that keep EARS honest:

- One `shall` per requirement. If you need "and" between two actions, that is two requirements.
- `shall` for mandatory, `may` for optional. Never `should`, `could`, or `might` — those are how
  requirements become opinions.
- Active voice with a named actor: "the system shall display," not "the error is displayed."
- The response must be measurable: a quantity, a time limit, a format, a status code.
- Every `FR-###` traces to at least one `BR-###`. An untraced requirement is scope creep that got
  through the door early.

Cover the unwanted-behaviour cases deliberately. Agents systematically under-specify failure: what
happens on a dropped connection, a duplicate submission, an expired token, a partial write, an
empty result set, a hostile input. Half your rework cycles will come from this section, so spend
the time here instead.

Also record explicit **non-goals**. Anything a reasonable reader might assume is included but is
not.

---

## 0.4 Milestones, dates, ownership → `plan.md`

`loop.py init` seeds this file in `/loop-project/0-plan/`.

**Milestones.** Each milestone is a demonstrable state of the system, not a period of activity.
"Auth works end to end including password reset" is a milestone. "Auth development" is a calendar
entry. Give each a target date and the `FR-###` set it closes. Sequence so that every milestone
leaves the system in a state that could ship if the money ran out that day.

**Ownership boundaries.** This is what prevents Workers colliding. For each area of the system,
name the single owner and the interface others must go through:

| Area | Owner | Others may | Others must not |
|---|---|---|---|
| Data schema | `TASK-002` | Read migration files | Add or alter migrations |
| Auth middleware | `TASK-004` | Import and call it | Reimplement checks inline |
| Design tokens | `TASK-003` | Reference token names | Hardcode colours or spacing |

The rule underneath the table: **one writer per file, always.** If two tasks need the same file,
they are one task or they are wrongly cut. Concurrency bugs between agents look exactly like
concurrency bugs between threads, and they are debugged the same painful way.

---

## 0.5 Definition of Done and acceptance checklist → `dod.md`

This is the contract the Judge enforces. `loop.py init` seeds this file in `/loop-project/0-plan/`.

Two parts:

**Project-level DoD** — conditions that must hold for the whole build. Typical set, adjust to the
project rather than copying blindly:

- All Must-have `FR-###` implemented and verified by a named test
- Test suite green; no tests skipped, disabled, or weakened during the build
- Every blocking item in the security contract satisfied
- No Sev-1 or Sev-2 defect open
- Runs from a clean clone with documented commands
- Secrets in environment configuration, none in the repository or its history
- For UI: design contract satisfied at the stated accessibility bar
- README covers install, run, test, and deploy

**Acceptance checklist** — one row per Must-have requirement, in this exact shape:

| ID | Requirement | How it is proven | Evidence artifact |
|---|---|---|---|
| AC-001 | FR-003: When a user submits an expired token, the API shall return 401 with no body | Integration test `auth.expired.spec.ts` | Test output in REPORT |
| AC-002 | FR-011: Table renders 10,000 rows without dropping below 30fps on scroll | Manual measurement, documented method | QA report with numbers |

"How it is proven" must be something someone else could re-run. If the only proof available is
"the agent looked at it and it seemed right," the criterion is not yet written properly — either
find a mechanical check or state the manual procedure precisely enough to repeat.

---

## Gate G0 — human approval

The only gate that requires a human by default. Present a compact summary — not the documents,
a summary — and ask for approval. Check before presenting:

- [ ] `research.md` records constraints and decisions with rationale
- [ ] Every `BR-###` has a measurable success condition
- [ ] Every Must-have `FR-###` is in valid EARS form and traces to a `BR-###`
- [ ] Unwanted-behaviour requirements exist for the obvious failure modes
- [ ] Non-goals are written down
- [ ] Milestones have dates and each leaves the system shippable
- [ ] Ownership boundaries assign exactly one writer per area
- [ ] Every Must-have has an acceptance row with a re-runnable proof
- [ ] Open questions are listed, and none of them block G1

- [ ] The role set has been chosen deliberately and confirmed, not left at the default

On approval: `python3 scripts/loop.py gate g0 --pass`, which freezes `dod.md` by recording its
hash in `loop.json`. Any later change to the file is detected and reported as scope drift.

If the human wants changes, take them and re-present. Do not proceed on a maybe — an unapproved
DoD produces a Judge with nothing to judge against, and the loop degenerates into the pipeline it
was built to replace.
