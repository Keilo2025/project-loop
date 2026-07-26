# Portability

Project Loop is written against the Agent Skills open standard, so the same `SKILL.md` and
`references/` load in any tool that implements it. What differs between tools is discovery paths,
whether real subagents exist, and how the human confirms a gate.

The loop's state lives entirely in `loop-project/`, which means a build can be started in one agent and
finished in another. That is worth knowing before you commit to a tool for a long project.

---

## Discovery paths

The specification standardises the file format, not the install location. Current locations:

| Agent | Project scope | User scope |
|---|---|---|
| Claude Code | `.claude/skills/project-loop/` | `~/.claude/skills/project-loop/` |
| OpenAI Codex | `.agents/skills/project-loop/` | `~/.agents/skills/project-loop/` |
| Cursor | `.cursor/skills/` plus a rule in `.cursor/rules/` | Cursor settings |
| Others | usually one of the above, or `AGENTS.md` | varies |

`scripts/install.sh` writes to whichever targets you name. Paths move as tools evolve — if a skill
is not being discovered, check the tool's current documentation before assuming the skill is
broken.

---

## Subagents, and running without them

Claude Code ships the five roles as bundled subagents, each with its own context window. That is
the strongest form of the isolation the design depends on: a Judge that has never seen the
Worker's reasoning cannot be persuaded by it.

Where subagents are unavailable, run the roles sequentially in one session. The isolation is
weaker and you should say so rather than pretend otherwise. Compensate by:

1. **Announcing the switch explicitly.** "Switching to Judge for TASK-007. I will not edit source
   files in this pass." Stating the constraint measurably improves adherence to it.
2. **Reloading from artifacts.** Read the REPORT and QA report from disk. Do not rely on
   remembering what you did — the memory is exactly the contamination you are trying to avoid.
3. **Honouring the read-set anyway.** Do not open files the role is not entitled to.
4. **Leaning on the script.** `loop.py verify` does not care which role is running. When
   isolation is weak, deterministic checks carry more of the load.

Sequential mode works. It catches most of what isolated mode catches, because the majority of
rework causes are mechanical — a missing report, an out-of-scope edit, an unproven acceptance
criterion — and those are found by the script, not by the model's independence.

---

## Human gates

By default only G0 requires a human. Configure this in `loop-project/loop.json`:

```json
{ "human_gates": ["g0"] }
```

Add `"g3"` when the work is going to production, and add `"g1"` on a first run with an unfamiliar
team or codebase — the cost of an unnoticed architectural mistake is much higher than the cost of
a five-minute review.

Interactive CLI agents can simply ask. In a non-interactive or CI context, a gate requiring a
human writes the request into `ledger.md`, sets `status: BLOCKED`, and exits non-zero. Wire that
exit code into whatever notifies a person.

---

## Adapter files

`adapters/` in the repository contains:

- `codex/AGENTS.md` — a compact preamble for Codex and any AGENTS.md-reading tool, pointing at the
  skill rather than duplicating it
- `cursor/project-loop.mdc` — a Cursor rule with `alwaysApply: false` and a description that lets
  the agent pull it in when relevant. Kept deliberately short: always-on rules are charged on every
  request
- `generic/AGENTS.md` — the minimal version for anything else

All three point at the skill instead of restating it. Duplicating the loop's rules into a rules
file guarantees the two copies diverge, and the divergence surfaces as contradictory instructions
at the worst moment.

---

## Model choice by role

Where a runtime lets you set a model per role, the economics are lopsided:

| Role | Suggested | Why |
|---|---|---|
| Planner | strongest available | Ambiguity here is paid for repeatedly |
| Architect | strongest available | Interface defects route back through every task |
| Worker | mid-tier | Bounded scope and an explicit contract, which is what mid-tier models do well |
| Tester | mid-tier | Executing and reproducing, not reasoning about design |
| Judge | strongest available | It holds the exit gate; a lenient Judge voids the whole design |

Saving money on the Planner and the Judge is a false economy. Saving it on Workers is usually
real, and Workers do most of the turns.

---

## Moving a loop between agents

`loop-project/` is plain Markdown and one JSON file. To hand a build over:

1. Commit `loop-project/` along with the code
2. Install the skill in the new agent
3. Run `loop.py status` and continue from the reported cursor

No conversation history is needed, which is the point. If a handover requires explaining what was
happening, the loop was being run out of the chat rather than out of the artifacts, and that
should be corrected before continuing.
