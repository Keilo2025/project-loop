# Project Loop

**A closed-loop build system for AI coding agents. The thing that writes the code doesn't get to
decide the code is done.**

Works in Claude Code, OpenAI Codex, Cursor, and anything else that reads the
[Agent Skills](https://agentskills.io) format. MIT licensed.

---

## The problem

Spec-driven development fixed the first half of vibe coding. Write the spec first, and the agent
stops improvising an architecture halfway through. That was a real advance, and frameworks like
Spec Kit, BMAD, OpenSpec and Kiro all deliver it.

They share one gap. They are **pipelines**: plan → spec → tasks → build → done. And "done" is
decided by the same agent that did the building.

So you get a build that ends when the model runs out of ideas, reports success it never observed,
quietly weakens a failing test, edits three files nobody asked it to touch, and hands you
something that "should work." Every one of those is a rational move for a system whose only exit
condition is its own satisfaction.

## What this does differently

Project Loop is a **control system**. Work flows forward through four phases, but a separate
**Judge** role holds the exit gate. The Judge never writes code, so it has nothing to protect. It
grades evidence, issues numbered rework orders, and the loop closes when the Judge says `PASS` —
at no other moment.

```
                     ┌──────────── REWORK ────────────┐
                     ▼                                │
    [0 Plan] ──G0──> [1 Spec] ──G1──> [2 Build] ──> [3 Verify] ──G3(PASS)──> done
                         ▲                                │
                         └──────── spec defect ───────────┘
```

Five things that, as far as I can tell, nothing else combines:

**1. The Judge grades evidence, not claims.**
Every task returns a REPORT in a fixed schema: files touched, exact commands, exact output,
acceptance criteria mapped to proof, assumptions, risks, blockers. No REPORT means automatic
rework — and the Judge does not open the diff to compensate, because reconstructing the report on
the Worker's behalf teaches the loop that reports are optional.

**2. Test tampering is detected and blocking.**
The fastest way to make a suite green is to weaken it. `loop.py` diffs test paths separately and
flags added skip markers, deleted test files, and removed assertions. That is a Sev-1, not a style
note. It is the one failure mode that makes every other check unreliable, so it gets its own gate.

**3. The Definition of Done is frozen and hashed at G0.**
An agent that can edit the finish line always reaches it. The DoD's SHA-256 is recorded when the
human approves it; any later change is reported as scope drift rather than absorbed silently.

**4. The loop has a memory, so the codebase has an author.**
Multi-agent builds drift: task 3 handles errors one way, task 7 another, task 9 rebuilds the date
formatter task 4 already wrote. Every task passes its own criteria and the result is still a mess,
because nothing in a per-task contract can see across tasks. `conventions.md` is in every Worker's
read-set and carries the conventions, an append-only reuse registry, and the decisions that bind
later tasks. Workers must run `loop.py reuse "<thing>"` before creating anything, and the verifier
flags near-duplicate files, unregistered components, and the mechanical slop patterns — empty catch
blocks, `any` escape hatches, leftover debug output, comments that restate the line below them.

**5. Security and frontend quality are blocking gates, not advice.**
A security contract instantiated per project from OWASP's LLM and Agentic Applications risk lists,
where every rule carries a stated check — because a rule with no check is a wish. Plus a design
contract covering tokens, required states, and a measured WCAG 2.2 AA bar. The Judge enforces
both.

And it is built to be cheap. Read-sets are binding, handoff is by artifact rather than
conversation, deterministic checks run in a script instead of costing model tokens, and the Judge
reads diffs rather than trees. Details in
[`references/token-budget.md`](plugins/project-loop/skills/project-loop/references/token-budget.md).

---

## Install

### npm (recommended)

```bash
npm install -g project-loop
project-loop
```

Running it bare starts an interactive installer that asks two questions — which agents, and how
widely — then writes only what you agreed to. Zero dependencies, so the install is a single
download and there is no supply chain to audit.

```
? Install into which agents?
  [x] Claude Code      - skill + 5 subagents (strongest role isolation)
  [ ] OpenAI Codex     - skill only — no subagents, roles run sequentially
  [ ] Cursor           - skill + a short project rule that pulls it in on demand
  [ ] Other agent      - any tool that reads the Agent Skills format

? How widely should it apply?
  > Every project on this machine   - user scope, installs under your home directory
    Just one specific project       - project scope, commit it so your team gets it too
```

Your answers are remembered in `~/.project-loop/config.json`, so the next machine or the next
upgrade is just `project-loop install --yes`.

Skip the prompts entirely when you already know what you want:

```bash
project-loop install --target claude --scope user            # one IDE, every project
project-loop install --target all --scope user --yes         # every IDE, every project
project-loop install --target cursor --scope project \
                     --project ~/code/app                    # one specific repo
project-loop install --target all --scope user --dry-run     # show the plan, write nothing
```

| Command | What it does |
|---|---|
| `project-loop` | interactive install |
| `project-loop install` | install, promptless when fully flagged |
| `project-loop uninstall` | remove the skill and subagents, never touches `.loop/` |
| `project-loop status` | every place it is installed, plus loop state here |
| `project-loop config` | view, change or `--reset` saved defaults |
| `project-loop doctor` | checks `python3`, `git`, payload integrity, install paths |
| `project-loop init` | scaffold `.loop/` in the current directory |

| Flag | Values | Default |
|---|---|---|
| `--target`, `-t` | `claude`, `codex`, `cursor`, `generic`, `all` (comma-separated) | ask, or last used |
| `--scope`, `-s` | `user` (every project), `project` (one repo) | ask, or last used |
| `--project`, `-p` | project root for `--scope project` | current directory |
| `--path` | skills directory for the `generic` target | ask |
| `--yes`, `-y` | accept defaults, ask nothing | off |
| `--dry-run`, `-n` | print the plan, write nothing | off |
| `--no-save` | do not remember these answers | off |

**Choosing a scope.** User scope installs under your home directory and applies to every project
you open — right for a personal machine. Project scope installs into the repository itself, so
committing `.claude/` or `.cursor/` hands the method to everyone who clones it — right for a team.
The two are independent; installing both is fine, and a project-scoped copy wins where it exists.

### Claude Code plugin marketplace

```bash
/plugin marketplace add Keilo2025/project-loop
/plugin install project-loop@project-loop
```

This brings the skill and five bundled subagents — Planner, Architect, Worker, Tester, Judge —
each with its own context window, which is the strongest form of the isolation the design needs.

### From a clone, via the shell installer

The original bash installer still works and behaves identically. It has no Node requirement, which
matters if you are installing onto a machine that does not have it.

```bash
git clone https://github.com/Keilo2025/project-loop.git
cd project-loop
./scripts/install.sh --target claude          # or codex, cursor, all
./scripts/install.sh --target all --scope project
./scripts/install.sh --target all --uninstall
```

### Manual

The skill is one directory. Copy `plugins/project-loop/skills/project-loop/` to wherever your
agent looks:

| Agent | Path |
|---|---|
| Claude Code | `~/.claude/skills/` or `.claude/skills/` |
| OpenAI Codex | `~/.agents/skills/` or `.agents/skills/` |
| Cursor | `.cursor/skills/` plus a rule from `adapters/cursor/` |

Requires `python3` for the state machine. Full details in [docs/INSTALL.md](docs/INSTALL.md).

---

## Use

In your project directory, tell the agent what you want:

> Run the project loop. Build me a expenses API with receipt upload, approval workflow, and CSV
> export for the finance team.

It will start at Phase 0, research, write the requirements, and come back for your approval at
gate G0. After that it runs until the Judge says `PASS` or hands you a specific decision.

To drive it manually:

```bash
python3 <skill>/scripts/loop.py status              # always run this first
python3 <skill>/scripts/loop.py init                # or --brownfield
python3 <skill>/scripts/loop.py gate g0 --check
python3 <skill>/scripts/loop.py task new "Receipt upload"
python3 <skill>/scripts/loop.py reuse "currency format"   # search before building
python3 <skill>/scripts/loop.py verify TASK-001
python3 <skill>/scripts/loop.py cycle TASK-001 --finding missing-authz
```

Everything the loop knows lives in `.loop/` as Markdown plus one JSON file. Commit it. A build can
be started in Claude Code and finished in Codex, or picked up by a colleague three weeks later,
with no conversation history at all — which is the point.

---

## What it produces

```
.loop/
├── loop.json              phase, cursor, cycle counts, frozen DoD hash
├── ledger.md              append-only: decisions, deviations, escalations
├── 0-plan/                research, BRD, EARS product spec, milestones, frozen DoD
├── 1-spec/                architecture, interfaces, security + craft + design contracts, conventions, QA strategy
├── 2-build/               task cards and Worker REPORTs
└── 3-verify/              QA reports, Judge verdicts, numbered rework orders
```

That is also your audit trail. Every decision traces to a document, every acceptance criterion
traces to evidence, and every deviation is in the ledger — which matters if anyone ever has to
explain how a system got built.

---

## When not to use this

Honest answer, because a framework that claims to fit everything fits nothing:

- **A single-file change or a quick script.** The gates cost more than the work.
- **Exploration and prototyping.** The loop is built to converge on a frozen definition of done.
  If you do not yet know what done means, go and find out first, then run the loop.
- **You want speed over correctness on something disposable.** The loop trades turnaround for a
  verdict you can trust. Sometimes that is the wrong trade.

It earns its overhead when correctness matters, when the work spans more than a session, when
someone else will have to trust the result, or when you are handing a build to an agent and
walking away.

See [docs/COMPARISON.md](docs/COMPARISON.md) for how it sits against Spec Kit, BMAD, OpenSpec and
Kiro, including where those are the better choice.

---

## Documentation

| Doc | Contents |
|---|---|
| [docs/INSTALL.md](docs/INSTALL.md) | Per-agent install, troubleshooting, uninstall |
| [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md) | The state machine, gates, roles, worked example |
| [docs/COMPARISON.md](docs/COMPARISON.md) | Against other spec-driven frameworks |
| [SECURITY.md](SECURITY.md) | Reporting issues, and what this skill does on your machine |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to propose changes |

The method itself is in
[`SKILL.md`](plugins/project-loop/skills/project-loop/SKILL.md) and its `references/`. It is
written to be read by a human as well as an agent.

---

## A note on trust

This is a skill that runs a Python script and reads your repository. A meaningful share of
published agent skills contain security flaws, and some are deliberately hostile. Do not take my
word for it that this one is fine — `loop.py` is a single stdlib-only file with no network access,
and the rest is Markdown. Read it before you install it.

That advice applies to every skill you install, including the popular ones.

---

MIT licensed. Issues and pull requests welcome.
