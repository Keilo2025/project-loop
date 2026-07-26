# Craft contract

The third blocking contract, alongside security and design. It exists because multi-agent builds
fail in a characteristic way that no functional test catches: every task passes, and the codebase
is still a mess.

Three failure modes, all of which look fine one task at a time:

- **Slop.** Code that works and reads as machine-produced — redundant comments restating the line
  below, empty catch blocks, `any` escape hatches, leftover debug output, defensive nesting around
  things that cannot be null.
- **Drift.** Task 3 handles errors one way, task 7 another, task 11 a third. Each is defensible
  alone. Together they are a codebase with no author.
- **Duplication.** Task 9 builds a date formatter that task 4 already built, under a different
  name, in a different directory. Nobody notices until the two disagree.

None of these are caught by acceptance criteria, because each task genuinely satisfied its own.
They are caught by memory — a written record of what already exists and what was already decided,
which every Worker reads before writing anything.

---

## The memory substrate: `conventions.md`

One file, `loop-project/1-spec/conventions.md`, in every Worker's read-set. The Architect writes sections
1 and 3 in Phase 1; Workers append to section 2 as they build. It is the loop's memory, and it is
what makes task 20 look like it was written by whoever wrote task 1.

Keep it compact. It is loaded on every task, so a bloated conventions file is a tax paid dozens of
times. Tables, not prose.

### Section 1 — Conventions

Only the decisions that would otherwise get made differently by different Workers:

| Concern | Decision |
|---|---|
| File and directory layout | `src/<domain>/{model,service,routes}.ts` |
| Naming | Components PascalCase, hooks `useThing`, files kebab-case |
| Validation | Zod at every boundary, schemas colocated with the route |
| Errors | Throw `AppError`; one handler at the edge; never catch to log and rethrow |
| Async | `async/await`, never mixed with `.then` |
| Dates | ISO 8601 strings at boundaries, `Date` only inside a module |
| State | Server state via the query client, UI state local; no global store |
| Tests | One `describe` per exported function, arrange-act-assert, no shared mutable fixtures |
| Imports | Absolute from `src/`, no deep relative paths beyond one level |

For brownfield, derive these from the existing code rather than inventing them. A convention that
contradicts the surrounding codebase is worse than no convention, because now there are two.

### Section 2 — Reuse registry

Append-only. Every reusable unit a Worker creates goes here immediately, in one line.

| Name | Path | Purpose | Created by | Used by |
|---|---|---|---|---|
| `formatCurrency` | `src/lib/format.ts` | AED/USD display with locale | TASK-004 | TASK-007, TASK-011 |
| `useDebounced` | `src/hooks/use-debounced.ts` | Debounce a changing value | TASK-006 | TASK-009 |
| `<DataTable>` | `src/ui/data-table.tsx` | Sortable table, virtualised over 200 rows | TASK-003 | TASK-008 |
| `requireOwner` | `src/auth/guards.ts` | Per-resource ownership guard | TASK-002 | all routes |

This table is the single highest-value artifact for preventing duplication, and it only works if
it is written at the moment of creation. A registry updated at the end of the project is an
inventory, not a memory.

### Section 3 — Bound decisions

Decisions taken during the build that constrain later tasks. Distinct from `ledger.md`, which
records deviations and escalations; this records constraints.

| ID | Decision | Binds | Taken in |
|---|---|---|---|
| BD-001 | Money is stored in minor units as integers, never floats | all financial code | TASK-004 |
| BD-002 | Soft delete via `deleted_at`; no hard deletes outside admin tooling | all data access | TASK-002 |

A Worker that needs to break a bound decision stops and requests an amendment. It does not decide
locally that this case is different — that is precisely how a codebase acquires two conventions.

---

## Reuse first

Before creating any new component, hook, utility, service, type, or endpoint, the Worker searches.
Not optionally, and not "if it seems likely."

```bash
python3 scripts/loop.py reuse "currency format"
```

That searches the registry and the working tree, and prints candidates. Then one of three outcomes:

1. **Something fits.** Import it. Add this task to its `Used by` column.
2. **Something nearly fits.** Extend it, if extending does not make it do two unrelated things.
   Update its `Purpose`.
3. **Nothing fits.** Build it, register it immediately, and record in the REPORT what you searched
   for and why what you found did not fit.

The third outcome is fine and common. What is not fine is the fourth, unstated one: building
without looking. That is the origin of every near-duplicate in every codebase, and an agent with
no memory of the last twenty tasks does it constantly.

**Extraction threshold.** The second time a pattern appears, extract it. Not the first — premature
abstraction is its own slop, and an abstraction with one caller is a guess about the future. Not
the third either, by which point three call sites have diverged and the extraction is a refactor
rather than a move.

---

## Anti-slop rules

Slop is code that works and reads as unconsidered. Some of it is mechanically detectable, which is
where `loop.py verify` earns its keep; the rest is judgement, which is check 4 in the rubric.

**Detected mechanically:**

| Pattern | Why it is slop |
|---|---|
| Comment restating the line below it | Costs a line, carries nothing, goes stale silently |
| Empty catch, or catch that only logs and continues | Converts a failure into a silent wrong answer |
| `any`, `as any`, `# type: ignore`, `@ts-ignore` | Deletes the guarantee the type system was there to give |
| `console.log`, `print`, `dbg!` left in source | Debug residue; noise in production logs |
| `TODO`, `FIXME`, `XXX` introduced by this task | Work declared and abandoned in the same commit |
| Names like `utils2`, `helper`, `dataManager`, `NewThing`, `handleThingFinal` | The name is a shrug; it tells a reader nothing |
| A new file near-identical to an existing one | Duplication, usually from not searching first |

**Judgement, checked by the Judge:**

- **Defensive noise.** Null checks on values that cannot be null, try/catch around code that does
  not throw, validation repeated at three layers. Each looks careful; together they hide where the
  real boundary is.
- **Comment density inverted.** Obvious lines commented, subtle ones bare. Comments explain *why*;
  the code already says *what*. If a comment is needed to say what, rename something instead.
- **Inconsistent shapes.** Three ways to return an error, two ways to name a boolean, both
  `getUser` and `fetchUser` for the same operation.
- **Abstraction with one caller.** A base class, a generic helper, or a config object introduced
  for a single use.
- **Copy-paste with variation.** Two blocks that differ in one identifier. Extract or accept the
  duplication deliberately — but not accidentally.
- **Dead scaffolding.** Exports nobody imports, parameters nobody passes, branches nobody reaches.

For interfaces, the visual equivalents live in `design-contract.md`. Same principle: models
converge on a small set of defaults, and the defaults now read as machine-made.

---

## What this is not

It is not a licence to refactor. A Worker still touches only its write-set, and still does not
improve code no acceptance criterion depends on. The craft contract governs **what this task
produces**, not what it finds nearby.

Existing slop outside the write-set gets logged in the REPORT under `Risks` and, if it matters,
becomes its own task. It does not get fixed in passing — an unreviewable diff is worse than an
inconsistent one, because nobody can see what changed.

---

## Instantiating it

The Architect writes `conventions.md` sections 1 and 3 during Phase 1 and states in
`loop-project/1-spec/qa-strategy.md` which craft rules are blocking for this project. Sensible default:
all mechanical rules blocking at Sev-3, duplication of a registered component at Sev-2, and the
judgement rules advisory unless the codebase is one people will maintain for years — in which case
make them blocking too, because the cost curve on drift is steep and entirely back-loaded.
