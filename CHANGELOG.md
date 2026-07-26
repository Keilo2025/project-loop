# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- npm distribution: `npm install -g project-loop`, exposing `project-loop` and the `ploop` alias
- Interactive installer. Running `project-loop` bare asks which agents and how widely, then writes
  only what was agreed. Arrow-key navigation on a TTY, numbered fallback when piped
- Scope selection: `user` (every project on the machine) or `project` (one repository)
- Target selection across Claude Code, OpenAI Codex, Cursor, and a `generic` target that takes a
  custom skills directory for any other Agent Skills reader
- Saved defaults in `~/.project-loop/config.json`, so upgrades are `project-loop install --yes`.
  Preferences only — loop state stays in each project's `loop-project/`, never centralised
- `project-loop status` — every install location plus the current directory's loop state
- `project-loop doctor` — python3, git, payload integrity, install paths, git work tree
- `project-loop config [--reset]` — view or clear saved defaults
- `project-loop init [--brownfield]` — delegates to `loop.py init` at whichever path is installed
- `--dry-run` on install and uninstall, printing every path that would be touched
- 23 installer tests running against throwaway `HOME` and project directories, covering scope
  isolation, adapter non-clobbering, `loop-project/` preservation on uninstall, and config recovery
- `scripts/flatten-repo.sh` — one-time cleanup of the nested duplicate working tree

### Changed
- Repository URLs resolved from `CHANGEME` and `<owner>` placeholders to the real slug
- `.gitignore` covers npm build output; `package-lock.json` is not committed, since a
  zero-dependency package has nothing for a lockfile to pin

### Notes
- Zero runtime dependencies, by design — an installer that runs before you have vetted anything is
  a poor place to introduce a supply chain. Node 18 or later
- `scripts/install.sh` is unchanged and still supported. It needs no Node, which matters when
  installing onto a machine that does not have it
- Uninstall never removes adapter files (`AGENTS.md`, Cursor rules) or `loop-project/` directories

## [1.0.0] — 2026-07-26

First release.

### Added
- Four-phase loop: Plan, Spec, Build, Verify, with gates G0 through G3
- Five roles with declared read-sets and prohibitions: Planner, Architect, Worker, Tester, Judge
- Judge-held exit gate — only a `PASS` verdict closes the loop
- REPORT evidence schema, enforced mechanically; a missing report is automatic rework
- Test-tampering detection: added skip markers, deleted test files, removed assertions (Sev-1)
- Definition of Done frozen and SHA-256 hashed at G0, with drift reported on every status check
- Write-set enforcement against `git status`
- Secret scanning with placeholder suppression
- Bounded rework: 3 cycles per recurring finding, 5 per task, then `BLOCKED`
- Cause classification (`code` / `spec` / `scope` / `plan`) routing rework to the right role
- Security contract derived from OWASP LLM and Agentic Applications risk lists, every rule with a
  stated check
- Design contract: tokens, required states, WCAG 2.2 AA bar, anti-generic rules, performance budget
- EARS notation for functional requirements
- Token budget discipline: binding read-sets, artifact handoff, deterministic checks in code,
  delta-only judging, progressive disclosure
- Craft contract: consistency, reuse-first, and anti-slop as a third blocking gate
- `conventions.md` memory substrate — conventions, append-only reuse registry, bound decisions
- `loop.py reuse` — searches registry and working tree before anything new is built
- Near-duplicate detection by normalised filename and normalised file body
- Reuse-registry enforcement: new components, hooks, utils, services must be registered on creation
- Mechanical slop detection: empty catch, `any` escape hatches, suppressed checks, leftover debug
  output, TODOs introduced by the task, comments restating the line below, placeholder-grade and
  versioned names
- REPORT gains a required `Reuse` section
- Judge rubric gains check 4 (craft) and a `craft` cause classification
- `loop.py` state machine: `init`, `status`, `task`, `reuse`, `verify`, `cycle`, `gate`, `block`
- Placeholder detection so unfilled templates cannot pass a gate
- Five Claude Code subagents with per-role model, effort and tool restrictions
- Cross-agent installer for Claude Code, Codex and Cursor, with `--dry-run` and `--uninstall`
- Adapters for Cursor `.mdc` rules and `AGENTS.md`
- `--brownfield` mode for existing codebases
