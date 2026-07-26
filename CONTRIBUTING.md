# Contributing

Contributions are welcome. The bar is simple: does the change make a verdict more trustworthy, or
make the loop cheaper without making it more lenient?

## What is most useful

**Deterministic checks.** Anything currently done by model judgement that could be done by
`loop.py` is a direct win — cheaper and more reliable. Test-tampering detection across more
languages and test frameworks is the obvious open area; the current patterns cover the common
JavaScript, Python, Java, Rust and Go idioms and miss plenty.

**Adapters.** New agents adopt the Agent Skills format regularly. An adapter is a short pointer
file plus a case in `install.sh`.

**Sharper rubrics.** If a Judge check has a blind spot you have hit in practice, that is worth
more than a new feature.

**Honest corrections to `docs/COMPARISON.md`.** If something there is wrong or stale, say so. I
would rather it be accurate than flattering.

## What will be declined

- Anything that lets the builder close its own loop.
- Additional roles whose output does not gate anything. If a role's document never changes a
  verdict, it is a cost centre.
- Always-on context that is not needed on every request. The token budget is a feature.
- Prescriptive implementation guidance in Judge orders. Judges state outcomes; designing is not
  their job.

## Working on it

```bash
git clone https://github.com/Keilo2025/project-loop.git
cd project-loop
./scripts/install.sh --target claude --scope project --dry-run
python3 -m py_compile plugins/project-loop/skills/project-loop/scripts/loop.py
bash -n scripts/install.sh
```

Test `loop.py` against a scratch git repository rather than a real project — `verify` and `gate`
read `git status`, and it is easier to reason about when the tree is yours.

## Style

- `loop.py` stays standard-library-only, single file, no network.
- Reference documents explain why a rule exists, not only what it is. A rule whose purpose is
  invisible gets skimmed within two tasks.
- Keep `SKILL.md` under 500 lines. It is a router; detail belongs in `references/`.
- No emoji in skill content.

## Pull requests

One concern per PR. Say what problem it solves and how you tested it. If it changes a gate or a
rubric, say what it would now catch that it previously missed — and what it might now reject that
it should not.
