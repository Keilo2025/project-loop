# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [1.0.0] — 2026-07-26

First release.

### Added

**The loop.** Four-phase build system — Plan, Spec, Build, Verify — gated G0 through G3, with a
back-edge from Verify to Build for code defects and a separate back-edge to Spec for defects in the
specification itself. Only a Judge verdict of `PASS` closes the loop; nothing else may declare the
work complete.

**Twelve roles, four authority classes.** Authority attaches to a class — PLAN, CODE, TEST, JUDGE —
rather than to a persona, and every role belongs to exactly one. Five are enabled by default:
Planner, Architect, Worker, Tester, Judge. The other seven are opt-in: Analyst, Designer, Security
Architect, Integrator, Scribe, Adversary, Product Owner. `loop.py roles --recommend` proposes a set
from the shape of the project; presets are `core` (5), `standard` (8), `full` (12). G0 will not pass
until the set is confirmed, and every optional role's artifact gates something real — a design
contract at G1, a security pass or business acceptance at G3. All twelve ship as bundled Claude Code
subagents with per-role model, effort and tool restrictions.

**Evidence, not claims.** REPORT schema enforced mechanically; a missing report is automatic
rework, and the Judge does not open the diff to compensate for it. Test-tampering detection —
added skip markers, deleted test files, removed assertions — treated as Sev-1. Write-set
enforcement against `git status`. Secret scanning with placeholder suppression. Cause
classification (`code` / `spec` / `scope` / `plan`) routes rework to the role that owns the fix.
Bounded rework: 3 cycles per recurring finding, 5 per task, then `BLOCKED` with the decision handed
to a human.

**Definition of Done.** Frozen and SHA-256 hashed at G0; drift reported on every status check.
Functional requirements in EARS notation, each traced to a business requirement.

**Contracts.** Security contract derived from OWASP LLM and Agentic Applications risk lists, every
rule with a stated check. Design contract: tokens, required component states, a WCAG 2.2 AA bar,
anti-generic bans, a performance budget. Craft contract: consistency, reuse-first, and anti-slop as
a third blocking gate.

**Memory and reuse.** `conventions.md` as the loop's memory substrate — conventions, an append-only
reuse registry, bound decisions. `loop.py reuse` searches the registry and the working tree before
anything new is built. Near-duplicate detection by normalised filename and normalised file body.
Reuse-registry enforcement: new components, hooks, utils and services must be registered on
creation. Mechanical slop detection: empty catch blocks, `any` escape hatches, suppressed checks,
leftover debug output, TODOs introduced by the task, comments that restate the line below them,
placeholder-grade and versioned names.

**`loop.py` state machine.** `init [--brownfield]`, `status`, `roles`, `task`, `reuse`, `verify`,
`cycle`, `gate`, `block`. Placeholder detection so an unfilled template cannot pass a gate.

**Distribution.** `npm install -g project-loop`, exposing `project-loop` and the `ploop` alias.
Interactive installer — running `project-loop` bare asks which agents and how widely, then writes
only what was agreed; arrow-key navigation on a TTY, numbered fallback when piped. Scope selection
(`user` or `project`) and target selection across Claude Code, OpenAI Codex, Cursor, and a `generic`
target for any other Agent Skills reader. Saved defaults in `~/.project-loop/config.json`, so
upgrades are `project-loop install --yes` — preferences only, loop state stays in each project's
`/loop-project`, never centralised. `project-loop status` reports every install location plus the
current directory's loop state; `project-loop doctor` checks python3, git, payload integrity and
install paths; `project-loop config [--reset]` views or clears saved defaults. `--dry-run` on
install and uninstall prints every path that would be touched without touching it. The original
`scripts/install.sh` still works and needs no Node, for machines that do not have it. Adapters for
Cursor `.mdc` rules and `AGENTS.md`. 31 tests covering installer scope isolation, adapter
non-clobbering, `/loop-project` preservation on uninstall, and config recovery.

### Notes

- Zero runtime dependencies, by design — an installer that runs before you have vetted anything is
  a poor place to introduce a supply chain. Node 18 or later
- Uninstall never removes adapter files (`AGENTS.md`, Cursor rules) or `/loop-project` directories;
  those are project state and an audit trail, not installed files
- A loop begun before role selection existed defaults to the core five and behaves exactly as
  before — an upgrade never changes the shape of work already in progress
