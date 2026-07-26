# Templates

Phase 0 and Phase 1 artifacts — including `conventions.md`, the loop's memory file — are
scaffolded directly into `/loop-project` by `loop.py init`, so they are
not duplicated here — two copies of the same template drift, and the divergence surfaces as
contradictory guidance at the worst moment.

What lives here are the artifacts that repeat once per task or per cycle:

| File | Written by | Goes to |
|---|---|---|
| `task.md` | Architect | `/loop-project/2-build/tasks/TASK-###.md` |
| `report.md` | Worker, Integrator, Scribe | `/loop-project/2-build/reports/TASK-###.report.md` |
| `qa-report.md` | Tester | `/loop-project/3-verify/qa/QA-###.md` |
| `ui-report.md` | UI Critic | `/loop-project/3-verify/qa/UI-###.md` |
| `verdict.md` | Judge | `/loop-project/3-verify/verdicts/V-###.md` |
| `rework.md` | Judge | `/loop-project/3-verify/rework/R-###.md` |

The Adversary uses `qa-report.md` and files to `SEC-###.md`; the Product Owner uses `verdict.md` and
files to `PO-###.md`. Neither needs a template of its own — the shape is the same and a near-duplicate
template is a thing that drifts.

The per-role contracts in `1-spec/` are seeded by `loop.py roles --enable`, not from this directory,
for the same reason Phase 0 and Phase 1 artifacts are not duplicated here.

Copy the shape rather than inventing structure. `loop.py verify` parses these headings by name,
so a renamed section reads as a missing one.
