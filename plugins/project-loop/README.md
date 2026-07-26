# project-loop (plugin)

The plugin package. Full documentation is in the [repository root](../../README.md).

```
plugins/project-loop/
├── .claude-plugin/plugin.json
├── agents/                     18 roles as Claude Code subagents, 5 enabled by default
└── skills/project-loop/
    ├── SKILL.md                router, state machine, gates
    ├── references/             phases, roles, rubrics, contracts
    ├── templates/              per-task artifacts
    └── scripts/loop.py         state machine and deterministic checks
```

Install: `/plugin marketplace add Keilo2025/project-loop` then
`/plugin install project-loop@project-loop`.
