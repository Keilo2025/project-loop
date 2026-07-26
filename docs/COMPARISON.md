# How Project Loop compares

Spec-driven development is a crowded category, and most comparison tables are marketing. This one
tries to be useful, including about where the alternatives are the better choice.

The landscape as of mid-2026: GitHub Spec Kit, BMAD-METHOD, OpenSpec, GSD, Agent OS, and AWS Kiro
are the names that come up in real engineering conversations, alongside a long tail of Claude Code
methodologies. Check current figures before quoting any of them — this category moves fast.

---

## The structural difference

Almost every framework in the category converges on the same four-phase shape: specify, plan,
break into tasks, implement. That convergence is a good sign — it means the shape is right.

The difference is what happens at the end.

**Pipelines** terminate when the implementing agent declares completion. Verification, where it
exists, is a step the same agent performs on its own work. That works when the agent is honest and
thorough, which is most of the time, and fails invisibly when it is not.

**Project Loop** terminates when a separate Judge grades evidence against a Definition of Done
that was frozen and hashed before building started. The Judge cannot write code. The loop has a
back-edge from verification to build, and a second one from verification to spec for the case
where the code is right and the spec was wrong.

That is the whole claim. Everything else in this repository is machinery to make that claim
enforceable rather than aspirational.

---

## Feature comparison

| | Spec Kit | BMAD | OpenSpec | Kiro | GSD | **Project Loop** |
|---|---|---|---|---|---|---|
| Spec is source of truth | yes | yes | yes | yes | partial | yes |
| Multiple specialised roles | no | 12+ | no | no | no | 12 |
| **Roster chosen per project, not fixed** | no | no | no | no | no | **yes** |
| **Authority classes, so roles can be added without new permissions** | no | no | no | no | no | **yes** |
| **Every optional role gates something** | n/a | no | n/a | n/a | n/a | **yes** |
| **Separate verifier that cannot write code** | no | partial | no | no | no | **yes** |
| **Structured evidence contract per task** | no | no | no | no | no | **yes** |
| **Test-tampering detection** | no | no | no | no | no | **yes** |
| **Definition of Done frozen and hashed** | no | no | no | no | no | **yes** |
| **Bounded rework with stop conditions** | no | no | no | no | no | **yes** |
| **Reuse registry the agent must search first** | no | no | no | no | no | **yes** |
| **Cross-task convention memory** | partial | partial | partial | partial | yes | **yes** |
| **Mechanical anti-slop detection** | no | no | no | no | no | **yes** |
| Security contract as a blocking gate | no | partial | no | partial | no | **yes** |
| Design contract as a blocking gate | no | partial | no | no | no | **yes** |
| Deterministic checks in code, not prompts | no | no | no | partial | no | **yes** |
| Declared per-role read-sets | no | no | no | no | partial | **yes** |
| Cross-agent portable | yes | yes | yes | no | partial | yes |
| Relative token cost | low | high | low | medium | low | **low to high — you choose** |

Rows are drawn from public documentation and community write-ups. If something here is wrong or
out of date, open an issue — I would rather this table be accurate than flattering.

---

## Honest positioning

**Against BMAD.** BMAD is the most architecturally ambitious framework in the category, simulating
a full agile team across 12+ named agent personas, and it produces genuinely thorough
documentation. It is also widely reported as the most expensive to run and takes weeks to learn.

Project Loop also has a large roster — eighteen roles — and the difference is what they are for and
when you pay for them. Three things separate the two:

*Every optional role gates something.* Enable the Designer and G1 will not pass without a design
contract. Enable the UX Researcher and G1 requires numeric completion bars rather than the word
"intuitive". Enable the SEO or LLM Specialist and G1 requires a stated check against every rule they
selected. Enable the Adversary or UI Critic and G3 requires their report. Enable the Product Owner and
G3 requires business acceptance against the BRD. A role that changed no gate would be ceremony, and
the rule for admitting one to the roster is that its output must be able to change a verdict.

*Authority is a class, not a persona.* Four classes — PLAN, CODE, TEST, JUDGE — carry every
read-set and prohibition, and each role belongs to exactly one. Going from five roles to eighteen
added thirteen briefs and zero permission rules, which is why the roster can keep growing without the
model of who-may-do-what getting harder to reason about. The specialist roles added most recently — a
vertical Domain Analyst, UX Researcher, Content Strategist, SEO Specialist, LLM Specialist, UI
Critic — cost six new briefs and changed nothing structural.

*You pay for the roster you chose.* Five roles are on by default; the loop asks at the start which of
the other thirteen this project needs and recommends a set from the shape of the code and the plan. A
CLI tool runs with five. A public platform that has to be found and cited runs with fifteen. A
regulated payments build runs with eighteen. Turning a role off usually does not skip its work — the
core role in the same class absorbs it, with less specialisation and a wider context — so the choice is
about how carefully something is done, not whether it happens.

*And where that last claim is false, the framework says so.* Two roles are marked `unabsorbed`: the
SEO and LLM Specialists own rules no other role has any claim to, so disabling them removes the work
rather than moving it. `loop.py roles --list` prints that warning rather than letting a convenient
generalisation stand.

Where BMAD still wins: large regulated greenfield programmes with many humans who need the
ceremony, and rich documentation as a deliverable in its own right rather than as a by-product.

**Against Spec Kit.** Spec Kit is the sensible default and the most portable option — a
constitution file plus a clean four-phase workflow, and it does not fight your IDE. Project Loop
is Spec Kit plus a verification stage with teeth. If your agents are already producing code you
trust, Spec Kit's lower ceremony is the better trade. If you have been burned by a build that
reported success it never observed, that is exactly the gap this fills.

**Against OpenSpec.** OpenSpec is strong on brownfield and cheap to run. Project Loop handles
brownfield through `--brownfield` seeding and a longer Phase 1, but OpenSpec is more specialised
at incremental change against existing specs. For a steady stream of small changes to a mature
codebase, OpenSpec is likely the better fit.

**Against Kiro.** Kiro is an IDE, not a methodology, with AWS-native structured requirements and
first-class EARS support. If you are inside the AWS ecosystem and happy to adopt the IDE, it gives
you more out of the box. Project Loop borrows EARS from the same tradition and stays
tool-agnostic.

**Against Agent OS.** Agent OS is standards-first rather than spec-first: it reverse-engineers a
codebase's conventions and injects the relevant ones into the agent's context, which is the closest
thing in the category to Project Loop's `conventions.md`. It is genuinely strong at the consistency
problem. Its v3 dropped durable spec-writing, so it no longer holds a spec as source of truth —
which means it solves drift without solving verification. The two are complementary; if you already
run Agent OS, its standards can seed `conventions.md` section 1 directly.

**Against GSD and the lightweight Claude Code methodologies.** These are deliberately low-ceremony
and very cheap, and for a solo developer moving fast on their own code that is often exactly
right. Project Loop costs more per feature. It buys a verdict someone else can trust.

---

## What Project Loop does not do

- It is not an IDE and it does not manage your context window.
- It does not orchestrate parallel agents. Tasks are sequential by design, because overlapping
  write-sets between agents produce concurrency bugs debugged the same painful way as concurrency
  bugs between threads.
- It does not generate documentation as a deliverable. It produces artifacts that gate work; that
  they read as documentation is a side effect.
- It does not prevent a determined human from overriding it. Every stop condition can be
  overridden — the ledger just makes the override a recorded decision rather than a silent one.

---

## Can you combine them?

Yes, and it is often sensible. Two patterns that work:

**Spec Kit or Kiro for Phases 0–1, Project Loop for Phases 2–3.** Keep the specification workflow
you already like, and adopt the verification stage. Point `/loop-project/1-spec/interfaces.md` at their
output, or symlink it.

**Project Loop as the verification layer over any pipeline.** Even without the planning phases,
the REPORT schema, the Judge rubric, and `loop.py verify` work against any build. The value
concentrates in Phase 3, and Phase 3 does not care much where the code came from.

The category does not need every team standardised on one framework. It needs teams to stop
letting the builder mark its own homework.
