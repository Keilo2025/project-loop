# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [2.0.0] — 2026-07-28

### Added

- A black-box lifecycle suite covering gate order, approvals, Git baselines, verdict evidence,
  rework, blocking, recovery, secret scanning, security/UI/business evidence, tamper detection,
  hostile Git filenames, path-confinement attacks, parallel state updates, and safe reset behaviour.
  It now runs under
  `npm test`, with Node 18/20/22 and Python 3.8/3.11/3.13 covered in CI.
- Typed `approve`, `verdict pass|rework|blocked`, and `unblock` transitions. PASS requires valid
  Worker, Tester, and Judge artifacts; REWORK requires schema-valid numbered orders; BLOCKED can
  only be resumed by an attributed human decision.
- An audited `migrate --by ... --reason ...` transition for legacy loops without frozen role
  rosters or immutable task baselines.

### Changed

- Gates can only pass in order, tasks can only be created after G1, and G3 refuses an empty task
  set.
- Task verification compares the complete result against the Git SHA captured when the task was
  created, parses filenames with NUL delimiters, fails closed without Git, and rejects edits to
  pre-existing tests.
- G3 scans the current project tree for credential assignments and reachable Git history for
  strong token and private-key signatures, including secrets deleted by a later commit.
- Task cards, Worker REPORTs, and Tester QA must carry exactly the same acceptance IDs. G3
  independently revalidates their hashes, the stored mechanical receipt, frozen DoD coverage,
  enabled Adversary/UI Critic/Product Owner evidence, and a SHA-256 snapshot of each task's exact
  delivered paths instead of recomputing a moving task-to-current-tree delta.
- The approved role roster is frozen at G0. State transitions are serialized with a project lock,
  preventing optional-role bypasses and lost updates from parallel agents.
- The evidence-free `cycle` transition is retired. Typed REWORK now enforces every cited order
  artifact. Required `Finding-ID`, `Domain`, `DoD-impact`, and severity fields drive hard stops for
  DoD changes, recurring findings, recurring Sev-1 security failures, and excessive task cycles;
  changing a label cannot reset an already bound order or finding signature.
- `init --force` archives the complete previous `loop-project` directory before creating a fresh
  loop. The root and every owned evidence directory are realpath-confined, preventing stale
  artifacts, root symlinks, nested evidence escapes, and changed source symlinks from crossing the
  project boundary.

## [1.1.0] — 2026-07-26

### Added

**Six specialist roles, taking the roster from twelve to eighteen.** The authority model is unchanged
— every new role belongs to exactly one existing class and inherits its prohibitions whole, which is
the property that let the roster grow without the permission model growing with it.

| Role | Class | Owns | Phase |
|---|---|---|---|
| Domain Analyst | PLAN | `0-plan/domain.md` | 0 |
| UX Researcher | PLAN | `1-spec/ux-contract.md` | 1 |
| Content Strategist | PLAN | `1-spec/content-contract.md` | 1 |
| SEO Specialist | PLAN | `1-spec/seo-contract.md` | 1 |
| LLM Specialist | PLAN | `1-spec/ai-readiness.md` | 1 |
| UI Critic | TEST | `3-verify/qa/UI-###.md` | 3 |

**The Domain Analyst is configured, not just enabled.** `loop.py roles --enable domain-analyst
--vertical proptech` sets its specialisation; `--vertical list` shows the twenty verticals that have a
section in the new `references/verticals.md` — fintech, healthtech, proptech, agritech, regtech,
insurtech, legaltech, edtech, climatetech, martech, hrtech, logistics, govtech, defencetech, commerce,
wealthtech, cybersecurity, biotech, traveltech, foodtech, plus `other`. G0 fails without a vertical,
because a Domain Analyst without a domain is a second Analyst at the same cost.

**Two roles are marked `unabsorbed`.** Every other optional role hands its artifact to the core role
in its class when disabled. The SEO Specialist and LLM Specialist do not — no existing role's remit
covers crawlability, indexation control, crawler access grants or agent-usability. Disabling them
removes the work rather than moving it, and `loop.py roles --list` now says so rather than letting the
"nothing is skipped" claim stand where it is false.

**Two new presets.** `product` (12) adds the experience roles for real-user product work; `growth`
(15) adds the discoverability and content roles for a public platform. `core` (5), `standard` (8) and
`full` (18) are unchanged in intent.

**Four new reference contracts.** `verticals.md`, `ux-contract.md`, `content-contract.md`, and
`discoverability-contract.md` — the last split into Part A for search and Part B for AI readiness.
Part B leads with what is actually known rather than the usual advice: `llms.txt` is a community
convention that most AI crawlers do not fetch and no major provider has committed to reading, no file
or markup buys citation, and the interventions with published effect sizes are attributable quotations
and verifiable figures. Verified July 2026 and dated in the file, because this is the fastest-moving
area in the framework.

**New gate checks, all mechanical.** G0 requires a vertical and a dated domain brief when the Domain
Analyst is on. G1 requires each enabled optional PLAN role's contract, a stated check against every
selected SEO and AI-readiness rule, a filled crawler-access grant, numeric completion bars in the UX
contract, and a non-empty string table in the content contract. G3 requires a UI report when the
Critic is on. Enabling a role that changed no gate would be ceremony.

**Judge rubric check 8b.** Grades the UX, content, SEO and AI-readiness contracts against the check
each rule declares — never against the Judge's own taste. Three findings are Sev-1 wherever they
appear, because each is a misrepresentation rather than a defect: content served differently to
crawlers than to users, markup describing text a user cannot see, and a fabricated statistic,
quotation or source. The last is called out explicitly because "add figures and quotations" is the
highest-leverage content technique and inventing them is the cheapest way to satisfy it.

### Changed

- `loop.py roles --recommend` detects seven more signals: a named audience, a public surface, AI or
  agent language, content and messaging work, and regulated-vertical vocabulary.
- Enabling an optional PLAN role seeds its contract template. It never overwrites a file that already
  has content.
- Anti-collusion rules gain three entries: the unabsorbed exception stated plainly, "every contract's
  rules carry a stated check" generalised beyond `security.md`, and a prohibition on one PLAN role
  writing another's artifact.
- The Tester's order of attack now ends at the other enabled contracts, and the Tester/UI Critic split
  is stated explicitly — the Tester verifies stated rules, the Critic judges what a rule cannot capture.
- Phase 1 gains section 1.7 with the intra-phase ordering rule: UX contract before design contract,
  content contract before the SEO and AI-readiness contracts.
- `templates/ui-report.md` added for the UI Critic. The Adversary and Product Owner deliberately reuse
  the QA and verdict templates rather than getting near-duplicates that drift.
- `templates/task.md` carries a commented-out contract list so the Architect picks the ones a task
  needs. Six contracts in every read-set is a tax on every task, and a Worker facing all six reads
  none of them.
- `token-budget.md` documents the three places a larger roster could have multiplied read cost, and
  the rule that prevents each: one vertical section not twenty, a split discoverability reference, and
  per-task contract selection.

### Fixed

- The CLI reported "5 subagents" in its install plan, its target hints and its uninstall summary,
  while the installer had always copied every file in the agents directory. The count is now read from
  disk via `agentCount()` rather than written as a literal, so it cannot drift again.
- `docs/INSTALL.md` claimed five subagents were installed and that uninstall removed five files. Both
  were wrong before this release too. It now distinguishes *installed* (all of them) from *enabled by
  default* (five), which is the distinction that actually matters to a reader.
- `docs/HOW-IT-WORKS.md` described "the four contracts" and listed four; there are now eight, and the
  table marks which are always present and which belong to an optional role.

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
