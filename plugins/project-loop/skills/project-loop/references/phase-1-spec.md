# Phase 1 — Spec

Role: **Architect**. Output: `loop-project/1-spec/`. Exit: gate **G1**.

Phase 1 turns *what the system does* into *how it is put together and how we will know it works*.
The test of a good Phase 1 is simple: a Worker with no memory of this conversation should be able
to pick up a task card, read `interfaces.md`, and produce code that fits — without asking a
question and without reading anything else.

Read-set for this phase: `0-plan/prd.md`, `0-plan/dod.md`, `0-plan/research.md`. Not the BRD —
business rationale does not change component boundaries, and it costs tokens.

---

## 1.1 Architecture → `architecture.md`

`loop.py init` seeds this file in `loop-project/1-spec/`.

**Components.** Name each one, state its single responsibility in one sentence, and list what it
owns. If a component's responsibility needs "and" to describe, split it.

**Data flow.** Trace the two or three journeys that matter, end to end, naming every hop:
entry point → validation → authorisation → business logic → persistence → response. Mark the
**trust boundaries** — every point where data crosses from a less-trusted zone to a more-trusted
one. Those marks are what the security contract attaches to, and what the Judge looks for.

**Data model.** Entities, relationships, ownership, and the multi-tenancy strategy if there is
one. State the isolation mechanism explicitly rather than assuming it: row-level security,
separate schemas, separate databases, or application-layer filtering. Application-layer filtering
is the one that fails silently, so if it is chosen, say why and say what enforces it.

**Foundation ordering.** List, in build order, what must exist before feature work begins. Usually:
project scaffold and toolchain → configuration and secrets loading → data layer and migrations →
auth and session → error handling and logging → the shared UI shell and design tokens. Feature
work that starts before the foundation is stable produces rework that looks like feature bugs, and
that is expensive to diagnose.

**ADRs.** For every decision that would be costly to reverse, one short record: context, options
considered, decision, consequences. Three to six is normal. Anything reversible in an afternoon
does not need one.

---

## 1.2 Interfaces → `interfaces.md`

This is the single most valuable artifact in the loop, because it is the only spec file most
Workers read. It must be complete enough to build against and short enough to load cheaply.

Contents:

- **Module boundaries** — what each module exports, and what it may import. Explicitly state the
  imports that are forbidden, because "don't reach into the data layer from the UI" is invisible
  unless written.
- **API contracts** — for each endpoint: method, path, auth requirement, request shape, response
  shape, and the full set of error responses with status codes. Error responses are not optional;
  under-specified errors are the top source of integration rework.
- **Shared types** — the canonical definitions. Workers import these; they do not redefine them.
- **Events and messages** — name, payload, producer, consumers, delivery guarantee.
- **Naming and file conventions** — where things go, what they are called. Mechanical, but it is
  what stops five Workers producing five layouts.

If a Worker has to guess a shape, `interfaces.md` has failed and the resulting defect is an
Architect defect, not a Worker defect. Judges must classify it that way — the `3 → 1` back-edge
exists precisely for this.

---

## 1.3 Security contract → `security.md`

Read `references/security-contract.md` and instantiate it for this project. Do not copy the
generic list wholesale; it is a menu, and an unfiltered menu is noise that Workers learn to skim.

The output is a set of **blocking rules** — conditions that make the Judge return REWORK with
Sev-1 regardless of anything else. Each rule states the rule, where it applies, and how it is
checked. A rule with no check is a wish.

Minimum coverage for any project that touches a network or a user:

- Authentication and session handling, including expiry and revocation
- Authorisation on every non-public route, checked server-side, per-resource not just per-role
- Input validation at every trust boundary, allow-list rather than deny-list
- Output encoding appropriate to the sink
- Secrets handling: environment configuration only, never committed, never logged
- Transport security and the headers that go with it
- Dependency provenance and a pinned lockfile
- Logging that is useful for incidents and free of credentials and personal data
- Rate limiting on anything unauthenticated or expensive

If the system embeds an LLM or an agent, add the agentic-risk rules from
`references/security-contract.md` — prompt injection through retrieved content, tool
over-permission, unbounded loop cost, and the fact that model output reaching a shell, a query, or
a browser is an untrusted input at that point regardless of where it came from.

---

## 1.4 QA strategy → `qa-strategy.md`

`loop.py init` seeds this file in `loop-project/1-spec/`. This defines what counts as proof, before anyone has an
incentive to lower the bar.

- **Layers and their jobs.** Unit for logic and edge cases; integration for contracts between
  components and for the database; end-to-end for the journeys named in the PRD; manual only where
  automation genuinely cannot reach, with the procedure written out.
- **Coverage expectations by area,** not a single global number. Payment logic and authorisation
  deserve near-total coverage; a settings page does not. A global percentage target mostly
  incentivises tests of trivial code.
- **The mapping.** Every `AC-###` from the DoD gets a named test or a named manual procedure. Any
  acceptance criterion without one is a gap that must close before G1.
- **Test data and fixtures.** Where they come from, and how tests stay independent of each other.
- **The commands.** Exact invocations for full suite, single file, and single test. Workers and
  Testers both need these verbatim; guessing them wastes turns.
- **What "reproducible" means here** — the standard the Tester must meet in Phase 3.

---

## 1.5 Conventions and memory → `conventions.md`

Read `references/craft-contract.md`. This file is the loop's memory and it is in every Worker's
read-set, so keep it compact — tables, not prose.

Write section 1 (**conventions**) and section 3 (**bound decisions**) now. Section 2 (the **reuse
registry**) starts empty and Workers append to it as they build.

Section 1 covers only the decisions different Workers would otherwise make differently: file
layout, naming, validation approach, error handling, async style, date representation, state
management, test structure, import style. Anything a reasonable engineer could do two ways, and
where two ways in one codebase is worse than either way consistently.

For brownfield, derive these from the existing code rather than inventing them. A convention that
contradicts the surrounding codebase is worse than no convention, because now there are two.

Then state in `qa-strategy.md` which craft rules are blocking for this project. Sensible default:
mechanical rules blocking at Sev-3, duplication of a registered component at Sev-2, judgement
rules advisory — unless people will maintain this for years, in which case make them blocking too.
The cost curve on drift is steep and entirely back-loaded.

## 1.6 Design contract → `design-contract.md`

Only if the project has a user interface. Read `references/design-contract.md` and instantiate it:
tokens, type scale, spacing scale, component inventory, required states, accessibility bar,
motion policy, responsive breakpoints.

This is a blocking contract, not a style suggestion. UI built without it is the single most
common source of "technically passes, obviously unshippable" — and that outcome is far more
expensive to fix at the end than to prevent at the start.

---

## Gate G1

No human required by default, but the checklist is not optional. `loop.py gate g1 --check` runs
the mechanical parts; the rest is judgement.

- [ ] Every Must-have `FR-###` maps to at least one named component
- [ ] Every `AC-###` maps to a named test or a written manual procedure
- [ ] `interfaces.md` is complete enough to build against without asking a question
- [ ] Every API contract lists its error responses, not just the success case
- [ ] Trust boundaries are marked on the data flow
- [ ] Every security rule has a stated check
- [ ] Foundation build order is explicit
- [ ] `conventions.md` sections 1 and 3 are written and specific
- [ ] Design contract exists if there is a UI
- [ ] Test commands are written verbatim
- [ ] No component is responsible for two unrelated things

Two failure modes to actively check for. **Over-specification**: if the spec dictates the body of
a function, it has stopped being a spec — cut it back to contracts and let the Worker work.
**Convenient omission**: if a hard part of the PRD has quietly not made it into any component, it
will resurface at G3 as a missing acceptance criterion. Search the PRD for the requirement you
least want to build and confirm it is specified.

On pass: `python3 scripts/loop.py gate g1 --pass`. The loop advances to Phase 2.
