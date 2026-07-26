# Project Loop

This repository uses Project Loop: a closed-loop build method where a separate Judge role holds
the exit gate. The method is a skill at `.agents/skills/project-loop/SKILL.md` — read it rather
than working from this file, which is a pointer, not a copy.

## Before anything else

```bash
python3 .agents/skills/project-loop/scripts/loop.py status
```

`no loop found` means start at Phase 0. Any other output means resume at the reported cursor.
State lives in `loop-project/loop.json`, not in the conversation.

## Non-negotiable

- Only a Judge verdict of `PASS` closes the loop. You may not declare the work complete.
- Phases are gated: Plan → Spec → Build → Verify. Building before gate G1 passes produces rework
  that looks like feature bugs.
- Every task delivers a REPORT with exact commands and their output. No report means automatic
  rework, and the Judge will not open the diff to compensate.
- Never modify, weaken, skip, or delete a test to make the suite pass. Detected automatically,
  treated as Sev-1.
- Never edit files outside a task's declared write-set. Request a scope amendment.
- The Definition of Done is frozen at G0. Changing it afterwards is scope drift and requires a
  human decision recorded in `loop-project/ledger.md`.

## Roles

Planner, Architect, Worker, Tester, Judge. Run them sequentially, announcing each switch, and
honour each role's read-set. Role briefs are in the skill's `references/roles.md`.
