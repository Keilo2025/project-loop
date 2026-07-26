# Templates

Phase 0 and Phase 1 artifacts — including `conventions.md`, the loop's memory file — are
scaffolded directly into `/loop-project` by `loop.py init`, so they are
not duplicated here — two copies of the same template drift, and the divergence surfaces as
contradictory guidance at the worst moment.

What lives here are the artifacts that repeat once per task or per cycle:

| File | Written by | Goes to |
|---|---|---|
| `task.md` | Architect | `/loop-project/2-build/tasks/TASK-###.md` |
| `report.md` | Worker | `/loop-project/2-build/reports/TASK-###.report.md` |
| `qa-report.md` | Tester | `/loop-project/3-verify/qa/QA-###.md` |
| `verdict.md` | Judge | `/loop-project/3-verify/verdicts/V-###.md` |
| `rework.md` | Judge | `/loop-project/3-verify/rework/R-###.md` |

Copy the shape rather than inventing structure. `loop.py verify` parses these headings by name,
so a renamed section reads as a missing one.
