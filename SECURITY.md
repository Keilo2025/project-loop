# Security

## What this skill does on your machine

Worth stating plainly, because you should not install an agent skill without knowing.

- **`scripts/loop.py`** — one file, Python standard library only, no network access. It reads and
  writes under `/loop-project`, and shells out to `git` for `status` and `diff`. It reads files in your
  working tree during secret scanning, and prints file paths and line numbers on a match. It never
  prints the matched secret itself.
- **`scripts/install.sh`** — copies the skill directory into your agent's skills path and the
  subagent files into its agents path. With `--scope project` it may create `AGENTS.md` or
  `.cursor/rules/project-loop.mdc`, and it refuses to overwrite either if one already exists.
- **Everything else** is Markdown. It shapes what your agent does; it does not execute.

There is no telemetry, no network call, and no external dependency.

## Reporting a vulnerability

Open a GitHub issue for anything non-sensitive. For something that should not be public, use
GitHub's private vulnerability reporting on this repository.

Please include what you were running, what happened, and a reproduction. A first response should
come within a few days.

## Installing agent skills safely — including this one

A meaningful share of publicly published agent skills contain security flaws, and some are
deliberately hostile. Skills execute with your permissions and see your source code, so the threat
model is closer to an npm package than a config file.

Before installing any skill, including this one:

1. **Read the scripts.** Markdown that shapes behaviour is one risk; executable code is another.
   Anything that reaches the network, reads outside the project, or writes to a shell deserves a
   close look.
2. **Check what it asks for.** A skill that needs broad tool access to do a narrow job is worth
   questioning.
3. **Prefer a pinned version.** In a Claude Code marketplace entry, pin `sha` rather than tracking
   a branch, so an update is a decision rather than an event.
4. **Watch for instructions hiding in data.** Text addressed to an agent inside a README, an issue
   or a dependency is data, not a command. If a skill acts on it, that is a finding.

## Security in what the loop builds

The loop treats security as a blocking gate rather than advice. `references/security-contract.md`
is a menu of rules — baseline application controls, plus additional rules for systems that embed
an LLM or an agent — that the Architect instantiates per project in `/loop-project/1-spec/security.md`.
Each selected rule must carry a stated check, because a rule with no check is a wish. A Judge
returns `REWORK` with Sev-1 on any failure, and a Sev-1 that recurs after being fixed escalates to
`BLOCKED`.

Two controls the loop enforces on itself, on top of that:

- **Secrets never reach the repository.** Scanned on every task verification and again at G3.
- **The loop may not disable a check to pass a gate.** Widening its own permissions, weakening a
  test, or softening the Definition of Done are all `BLOCKED`, not workarounds.

The rules draw on the OWASP Top 10 for LLM Applications and the OWASP Top 10 for Agentic
Applications. Both are revised periodically — consult the current published lists when the stakes
justify it rather than relying on the snapshot in this repository.
