# UI-### — TASK-###
UI Critic pass. Date: <date>

Contracts in scope: design-contract.md<, ux-contract.md, content-contract.md>
Surfaces examined: <routes, screens or components actually opened>
How: <running app at <url> / storybook / built preview — not the source>

## Anti-generic bans
| Ban (quote the contract line) | Present? | Where |
|---|---|---|
| <e.g. "no gradient hero with a centred headline"> | no | — |

Unlisted clichés found: <or "none">

## Token discipline
Computed values checked against the token set, not the source comments.

| Property | Literal found | Should be | File / element |
|---|---|---|---|

## Data stress
| Case | Result |
|---|---|
| zero rows | |
| one row | |
| ~1000 rows | |
| 40-char unbroken name | |
| null where a value was assumed | |
| 8-line description | |
| RTL text / emoji in a name field | |

## Required states
| Component | default | hover | focus | active | disabled | loading | empty | error |
|---|---|---|---|---|---|---|---|---|

Unreachable states (a state you could not trigger is a finding, not a blank cell):
- 

## The one deliberate decision
Anchor the contract named: <typeface pairing / density / accent / illustrative style>

| Surface | Held? | Note |
|---|---|---|
| <surface 1> | | |
| <surface 2> | | |
| <surface 3> | | |

Do these three look like one product? <yes / no, and why>

## UX bars
| Journey | Bar | Measured | Pass? |
|---|---|---|---|
| <journey> | <max steps / fields from ux-contract.md> | | |

## Copy
Banned register terms found: <or "none">
Placeholder text still shipped: <or "none" — any hit is Sev-2>
Strings over their character ceiling: <or "none">

## Findings

### UI-###-01 — Sev-<1|2|3|4> — <one-line title>
Contract line: <quote it>
Steps: 
1. 
2. 
Expected: <what the contract requires>
Actual: <what rendered>
Evidence: <screenshot path, computed value, exact string>

## Observations — contract is silent here
Not findings. These are gaps in the design contract, cause `spec`, routed to the Designer. Do not
write them as rework orders against the Worker, and do not invent a rule to make one fit.

- 

## Coverage
What was examined and found clean, so the Judge can see the scope of a quiet report:
- 
