# Project Loop

This repository uses Project Loop (any Agent Skills compatible tool): a closed-loop build method where a separate Judge role holds
the exit gate. The method is a skill at `<skill-install-path>/SKILL.md` — read it rather
than working from this file, which is a pointer, not a copy.

## Before anything else

```bash
python3 <skill-install-path>/scripts/loop.py status
```

`no loop found` means start at Phase 0. Any other output means resume at the reported cursor.
State lives in `/loop-project/loop.json`, not in the conversation.

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
  human decision recorded in `/loop-project/ledger.md`.

## Roles

Eighteen roles across four authority classes — PLAN, CODE, TEST, JUDGE — of which five are enabled by
default: Planner, Architect, Worker, Tester, Judge. Choose the set at loop start with
`loop.py roles --recommend`; G0 will not pass until it is confirmed.

The optional roles are Analyst, Domain Analyst, UX Researcher, Designer, Content Strategist, SEO
Specialist, LLM Specialist, Security Architect (PLAN); Integrator, Scribe (CODE); Adversary, UI
Critic (TEST); Product Owner (JUDGE). The Domain Analyst takes a vertical:
`loop.py roles --enable domain-analyst --vertical fintech`. The SEO and LLM Specialists are
unabsorbed — no other role covers their rules, so disabling them removes the work rather than moving
it.

Run the enabled roles sequentially, announcing each switch, and honour each role's read-set. No
role ever holds two authority classes. Briefs are in the skill's `references/roles.md`.
