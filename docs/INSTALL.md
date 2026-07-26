# Install

Requires `python3` (3.8 or later) and `git`. Both are almost certainly already there — check with
`python3 --version && git --version`.

Without `python3` the skill still loads and the method still works, but every deterministic check
falls back to model judgement, which is slower, more expensive, and less reliable. It is worth
installing.

The npm route additionally needs Node 18 or later. The bash route does not need Node at all.

---

## npm — the short version

```bash
npm install -g project-loop
project-loop
```

Two questions, then it writes only what you agreed to. Zero runtime dependencies.

### What it asks

**1. Which agents?** A multi-select over Claude Code, OpenAI Codex, Cursor, and "other agent"
(which prompts for a custom skills directory). Space to toggle, `a` for all, enter to confirm.
Pick one for a single IDE; pick all for every IDE.

**2. How widely?**

| Choice | Scope | Where it lands | Use it when |
|---|---|---|---|
| Every project on this machine | `user` | under `$HOME` | personal machine, you want it everywhere |
| Just one specific project | `project` | inside the repo | team project — commit it and everyone gets it |

Choosing project scope prompts for the directory, defaulting to your current one.

If you picked "other agent", it asks for the skills directory. The Agent Skills specification
standardises the file format, not the install location, so check your tool's own docs for the
path it scans.

### Where each answer writes

| Agent | User scope | Project scope | Extra |
|---|---|---|---|
| Claude Code | `~/.claude/skills/` + `~/.claude/agents/` | `.claude/skills/` + `.claude/agents/` | 5 subagents |
| OpenAI Codex | `~/.agents/skills/` | `.agents/skills/` | `AGENTS.md` at repo root |
| Cursor | `~/.cursor/skills/` | `.cursor/skills/` | `.cursor/rules/project-loop.mdc` |
| Other | your path | your path | `AGENTS.md` at repo root |

Adapter files — `AGENTS.md`, the Cursor rule — are placed **only when absent**. If you already
have one, the installer says so and points at the source to merge by hand. It will not overwrite
your work.

### Non-interactive

Every question has a flag, so the whole thing is scriptable:

```bash
project-loop install --target claude --scope user --yes
project-loop install --target claude,cursor --scope project --project ~/code/app --yes
project-loop install --target generic --path ~/.myagent/skills --scope user --yes
project-loop install --target all --scope user --dry-run     # plan only, writes nothing
```

Run `--dry-run` first on anything you are unsure about. It prints every path it would touch.

### Saved defaults

After a successful install your answers go to `~/.project-loop/config.json`:

```json
{
  "version": 1,
  "targets": ["claude", "cursor"],
  "scope": "user",
  "customSkillPath": null,
  "installs": [{ "at": "...", "targets": ["claude"], "scope": "user", "root": null }]
}
```

So upgrades are one command: `project-loop install --yes`. Inspect with `project-loop config`,
clear with `project-loop config --reset`, or bypass saving entirely with `--no-save`.

This file holds preferences only. Loop state is never centralised — it lives in each project's
`.loop/` directory, which is what lets a loop survive context compaction, a session restart, or a
switch to a different agent entirely.

### Other commands

```bash
project-loop status      # every place it is installed, plus .loop state here
project-loop doctor      # python3, git, payload integrity, install paths, git work tree
project-loop init        # scaffold .loop/ in the current directory
project-loop uninstall   # remove skill + subagents, never touches .loop/
```

`project-loop doctor` is the fastest way to answer "why isn't this working" — it checks the
things that actually go wrong, in the order they go wrong.

---

## Claude Code

### Marketplace (recommended)

```
/plugin marketplace add Keilo2025/Project-Look-Skills-
/plugin install project-loop@project-loop
```

Installs the skill and five subagents — Planner, Architect, Worker, Tester, Judge — each with its
own context window. That is the strongest form of the role isolation the design depends on: a
Judge that has never seen the Worker's reasoning cannot be persuaded by it.

For a team, install at project scope so it travels with the repository:

```
/plugin install project-loop@project-loop --scope project
```

From the command line rather than a session:

```bash
claude plugin marketplace add Keilo2025/Project-Look-Skills-
claude plugin install project-loop@project-loop
claude plugin list
```

### Without a marketplace

```bash
git clone https://github.com/Keilo2025/Project-Look-Skills-.git
cd project-loop
./scripts/install.sh --target claude              # ~/.claude/
./scripts/install.sh --target claude --scope project   # ./.claude/
```

Project scope loads only after you accept the workspace trust prompt, which is the correct
behaviour — the content comes from a repository rather than from you.

### For a session only

```bash
claude --plugin-dir /path/to/project-loop/plugins/project-loop
```

Useful for trying it without installing anything.

---

## OpenAI Codex

```bash
./scripts/install.sh --target codex                     # ~/.agents/skills/
./scripts/install.sh --target codex --scope project     # ./.agents/skills/ + AGENTS.md
```

Codex reads the Agent Skills format, so the same `SKILL.md` and `references/` work unchanged. It
has no subagents, so the five roles run sequentially in one session. See
`references/portability.md` for how to compensate — the short version is: announce each role
switch explicitly, reload from artifacts rather than memory, and lean harder on `loop.py verify`.

Project scope also drops an `AGENTS.md` at the repository root, which Codex reads before anything
else. The installer will not overwrite an existing one; merge the snippet from
`adapters/codex/AGENTS.md` by hand.

---

## Cursor

```bash
./scripts/install.sh --target cursor --scope project
```

Two pieces:

- The skill at `.cursor/skills/project-loop/`
- A rule at `.cursor/rules/project-loop.mdc`, set to `alwaysApply: false` with a description that
  lets the agent pull it in when relevant

The rule is deliberately short. Always-on rules are charged on every single request, and a long
one is a permanent tax for something you need on a fraction of your work. The rule points at the
skill rather than restating it, because two copies of the same rules drift and then contradict
each other at the worst moment.

Commit `.cursor/` so the whole team gets it.

---

## Any other agent

Copy `plugins/project-loop/skills/project-loop/` into whatever directory your tool scans for
skills, and add `adapters/generic/AGENTS.md` if it reads `AGENTS.md`.

The Agent Skills specification standardises the file format, not the install location, so paths
vary between tools and move as tools evolve. If the skill is not being discovered, check your
tool's current documentation before assuming the skill is broken.

---

## Verify it loaded

| Agent | Check |
|---|---|
| Claude Code | `/plugin`, or `claude plugin list`, or `claude plugin details project-loop` |
| Codex | ask it to list available skills |
| Cursor | ask it to list available skills and rules |

Then, in a project directory:

```bash
python3 ~/.claude/skills/project-loop/scripts/loop.py status
```

`no loop found` is the correct answer before you have started one.

---

## Uninstall

```bash
project-loop uninstall                                   # interactive
project-loop uninstall --target all --scope user --yes   # every agent, user scope
npm uninstall -g project-loop                            # remove the CLI itself too
```

Or from a clone: `./scripts/install.sh --target all --uninstall`.

Or in Claude Code: `claude plugin uninstall project-loop@project-loop`.

Uninstall removes the skill directory and the five named subagent files. It deliberately leaves
adapter files alone — your `AGENTS.md` and Cursor rules may have been edited since, and silently
deleting an edited file is worse than leaving a stale one.

`.loop/` directories are left alone. They are project state and part of your audit trail, not
installed files — delete them yourself if you want them gone.

---

## Troubleshooting

**Start with `project-loop doctor`.** It checks python3, git, payload integrity, every install
location, and whether the current directory is a git work tree. Most of what follows is something
doctor will just tell you.

**The skill does not trigger.** Skills are selected from their description, and agents tend to
under-trigger rather than over-trigger. Name it explicitly: "use the project-loop skill." If it
still does not appear, it is not installed where the tool is looking — check `project-loop status`.

**`project-loop: command not found` after `npm install -g`.** Your npm global bin directory is not
on `PATH`. Find it with `npm bin -g` (or `npm prefix -g` and append `/bin`) and add that to your
shell profile. There is also a shorter alias, `ploop`, installed alongside.

**`EACCES` during `npm install -g`.** Your global prefix needs root. Do not reach for `sudo npm` —
point npm at a directory you own instead:

```bash
npm config set prefix ~/.npm-global
export PATH="$HOME/.npm-global/bin:$PATH"    # add to your shell profile
npm install -g project-loop
```

**`skill payload missing`.** The package installed without its files, or you are running the CLI
from outside the repository. Reinstall: `npm install -g project-loop`.

**Installed into the wrong place.** Nothing is destructive to undo — run `project-loop uninstall`
with the same `--target` and `--scope`, then reinstall with the right ones. Use `--dry-run` to
confirm the paths before committing to them.

**`loop.py: command not found` or a path error.** The skill's location differs per agent. Find it:

```bash
find ~ -name loop.py -path '*project-loop*' 2>/dev/null
```

In Claude Code you can use `${CLAUDE_PLUGIN_ROOT}/skills/project-loop/scripts/loop.py`.

**`scope intact — skipped (no git repository)`.** Write-set enforcement needs git. Run `git init`.
The loop works without it, but you lose the cheapest and most reliable check it has.

**A gate fails on files you have written.** Placeholder detection is firing. `loop.py gate <g>
--check` prints which patterns remain — usually a `<placeholder>` left in a template, an empty
table row, or a bullet with nothing after it. This is deliberate: a gate that passes an unfilled
stub is worse than no gate.

**`WARNING: dod.md changed after it was frozen at G0`.** Something edited the Definition of Done
after approval. That is exactly what the hash is for. Either restore the file, or record a human
decision in `.loop/ledger.md` and re-freeze deliberately.

**Everything is `BLOCKED`.** Read `.loop/ledger.md` — a stop condition fired and the reason is
written there with the decision that is needed. `BLOCKED` is a success state: the loop detected
that more autonomy would destroy value and handed back control. Make the call, record it, and
continue.
